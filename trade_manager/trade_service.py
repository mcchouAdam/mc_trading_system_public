import time
import json
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, Any, Tuple

from trade_manager.models import TradeSignal, TradeRecord, Actions, SizingTypes, PositionDTO, TradingSettingsDTO
from trade_manager.capital_client import CapitalClient
from trade_manager.trade_repository import TradeRepository

REDIS_KEY_SETTINGS = "TRADING_SETTINGS"
REDIS_KEY_RISK_STATE = "RISK_STATE"
REDIS_KEY_CACHED_POSITIONS = "CACHED_OPEN_TRADES"
REDIS_CH_POSITIONS_UPDATED = "CHANNEL_POSITIONS_UPDATED"

MIN_POSITION_SIZE = 0.01
SETTINGS_TTL = 10 # Seconds

FLD_ENGINE_HALT = "engine_halt_status"
FLD_MANUAL_HALT = "manual_halt_status"
FLD_RESUME_OVERRIDE = "resume_override"
FLD_HALT_REASON = "engine_halt_reason"

SET_DEFAULT_SIZE = "default_size"
SET_RISK_PCT = "risk_pct_per_trade"
SET_DYNAMIC_SIZING = "use_dynamic_sizing"
SET_LEVERAGE_FACTOR = "fixed_leverage_factor"

class TradeService:
    def __init__(self, 
                 api_client: CapitalClient, 
                 repository: TradeRepository, 
                 redis_client,
                 ml_handler = None):
        self.api = api_client
        self.repo = repository
        self.redis = redis_client
        self.ml = ml_handler
        self.open_positions: Dict[str, str] = {} # epic -> deal_id

    def process_signal(self, signal: TradeSignal):
        """Main entry point for processing a trade signal using Strategy Map."""
        print(f"[SERVICE] Processing {signal.action} {signal.epic} (Strategy: {signal.strategy})")

        strategy_map = {
            Actions.BUY:       self._handle_open,
            Actions.SELL:      self._handle_open,
            Actions.CLOSE:     self._handle_close,
            Actions.UPDATE_SL: self._handle_update_sl,
        }

        handler = strategy_map.get(signal.action)
        if handler:
            handler(signal)
        else:
            print(f"[WARN] Unknown action: {signal.action}")

    def _handle_open(self, signal: TradeSignal):
        # 1. Risk Check
        is_halted, reason = self.is_system_halted()
        if is_halted:
            print(f"[REJECTED] System HALTED: {reason}")
            return

        # 2. ML Filter
        if signal.use_ml and self.ml:
            if not self._check_ml_filter(signal):
                return

        # 3. Calculate Sizing
        size = self._get_final_size(signal)
        if size <= 0:
            print(f"[ERROR] Invalid size: {size}")
            return

        # 4. Execute on API
        deal_ref = self.api.open_position(
            epic=signal.epic,
            direction=signal.action,
            size=size,
            stop_level=signal.stop_loss,
            profit_level=signal.take_profit
        )
        if not deal_ref:
            return

        # 5. Confirm & Record
        time.sleep(0.5)
        confirm = self.api.get_position_confirm(deal_ref)
        if not confirm:
            print(f"[ERROR] Could not confirm deal_ref: {deal_ref}")
            return

        deal_id = confirm.get("dealId", deal_ref)
        affected = confirm.get("affectedDeals", [])
        if affected:
            deal_id = affected[0].get("dealId", deal_id)

        trade_record = TradeRecord(
            deal_id=deal_id,
            deal_reference=deal_ref,
            epic=signal.epic,
            direction=signal.action,
            size=size,
            entry_price=float(confirm.get("level", 0)),
            entry_time=datetime.now(timezone.utc),
            resolution=signal.resolution,
            strategy=signal.strategy,
            source=signal.source,
            leverage=confirm.get("leverage"),
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit
        )
        
        self.repo.insert_trade_open(trade_record)
        self.open_positions[signal.epic] = deal_id
        self.sync_positions_to_redis()

    def _handle_close(self, signal: TradeSignal):
        deal_id = signal.deal_id or self.open_positions.get(signal.epic)
        if not deal_id:
            print(f"[WARN] No deal_id to close for {signal.epic}")
            return

        deal_ref = self.api.close_position(deal_id)
        if not deal_ref:
            return

        time.sleep(0.5)
        confirm = self.api.get_position_confirm(deal_ref)
        if not confirm:
            return

        self.repo.update_trade_close(
            deal_id=deal_id,
            exit_price=float(confirm.get("level", 0)),
            exit_time=datetime.now(timezone.utc),
            realized_pnl=float(confirm.get("profit", 0)),
            exit_type="AUTO"
        )
        
        self.open_positions.pop(signal.epic, None)
        self.sync_positions_to_redis()

    def _handle_update_sl(self, signal: TradeSignal):
        if not signal.deal_id or signal.stop_loss is None:
            return
        if self.api.update_position(signal.deal_id, stop_level=signal.stop_loss):
            print(f"[OK] Updated SL for {signal.deal_id}")
            self.repo.update_trade_sl(signal.deal_id, signal.stop_loss)
            self.sync_positions_to_redis()

    # --- Helper Methods ---

    def _check_ml_filter(self, signal: TradeSignal) -> bool:
        """Consults the ML Inference Handler to approve or reject the signal."""
        if not self.ml:
            print("[ML Warn] ML Handler not initialized. Passing by default.")
            return True

        try:
            df = self.repo.get_latest_candles(signal.epic, signal.resolution, count=200)
            if df.empty or len(df) < 50:
                print(f"[ML Warn] Insufficient market data. Proceeding.")
                return True

            s_key = signal.strategy.lower().replace('strategy', '').strip()
            if 'broken' in s_key: s_key = 'yu_broken_bottom'
            
            dummy_entries = pd.Series(False, index=df.index)
            dummy_entries.iloc[-1] = True
            
            filtered_entries = self.ml.apply_ml_filter(s_key, df, dummy_entries)
            if not filtered_entries.iloc[-1]:
                print(f"[ML REJECTED] ❌ AI rejected signal for {signal.epic}.")
                return False
                
            print(f"[ML PASSED] ✅ AI approved signal for {signal.epic}.")
            return True
        except Exception as e:
            print(f"[ML Error] Filter execution failed: {e}. Defaulting to PASS.")
            return True

    def _get_final_size(self, signal: TradeSignal) -> float:
        """Determines position size based on signal, settings, and equity risk."""
        if signal.position_size and signal.sizing_type == SizingTypes.FIXED:
            return float(signal.position_size)

        settings = self._get_trading_settings()
        equity = self._get_current_equity()
        
        if equity <= 0:
            return signal.position_size or settings.default_size

        # Dynamic Sizing Logic (Risk based)
        if signal.sizing_type == SizingTypes.RISK and signal.position_size:
            risk_pct = signal.position_size / 100.0
            if signal.stop_loss and signal.price:
                dist = abs(signal.price - signal.stop_loss)
                if dist > 0:
                    size = (equity * risk_pct) / dist
                    return round(max(size, MIN_POSITION_SIZE), 2)

        return settings.default_size

    def _get_trading_settings(self) -> TradingSettingsDTO:
        """Fetch settings from Redis with a local cache mechanism."""
        if hasattr(self, '_settings_cache') and (time.time() - self._settings_cache_time < SETTINGS_TTL):
            return self._settings_cache

        try:
            raw = self.redis.get(REDIS_KEY_SETTINGS)
            data = json.loads(raw) if raw else {}
            self._settings_cache = TradingSettingsDTO.from_dict(data)
        except Exception:
            self._settings_cache = TradingSettingsDTO()
        
        self._settings_cache_time = time.time()
        return self._settings_cache

    def _get_current_equity(self) -> float:
        """Fetch total equity from Capital.com."""
        data = self.api.get_accounts()
        if not data or "accounts" not in data: return 0.0
        acc = next((a for a in data["accounts"] if a.get("preferred")), data["accounts"][0])
        return float(acc["balance"]["balance"]) + float(acc["balance"]["profitLoss"])

    def is_system_halted(self) -> Tuple[bool, str]:
        risk_state = self.redis.hgetall(REDIS_KEY_RISK_STATE)
        if not risk_state: return False, ""
        
        halted = risk_state.get(FLD_ENGINE_HALT, "false").lower() == "true" or \
                 risk_state.get(FLD_MANUAL_HALT, "false").lower() == "true"
        
        if halted and risk_state.get(FLD_RESUME_OVERRIDE, "false").lower() == "true":
            return False, ""
        return halted, risk_state.get(FLD_HALT_REASON, "Risk/Manual Halt")

    def sync_positions_to_redis(self):
        """Updates Redis cache for the C++ engine to see, using the formal PositionDTO."""
        all_trades = self.repo.get_trades(include_open=True)
        active = []
        for t in all_trades:
            if t.get('exit_time') is not None: continue
            
            dto = PositionDTO(
                deal_id=t['deal_id'],
                epic=t['epic'],
                direction=t['direction'],
                entry_price=float(t['entry_price']),
                entry_time=str(t['entry_time']),
                size=float(t['size']),
                resolution=t.get('resolution'),
                strategy=t.get('strategy'),
                stop_level=float(t.get('stop_loss') or 0.0),
                profit_level=float(t.get('take_profit') or 0.0) if t.get('take_profit') else None
            )
            active.append(dto.to_dict())
            
        self.redis.set(REDIS_KEY_CACHED_POSITIONS, json.dumps(active))
        self.redis.publish(REDIS_CH_POSITIONS_UPDATED, "CHANGED")
        print(f"[SYNC] {len(active)} active positions synced.")
