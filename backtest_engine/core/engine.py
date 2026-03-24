import pandas as pd
import numpy as np
import os
import itertools
import vectorbt as vbt
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from tqdm import tqdm
from .dtos import BacktestConfigDTO

# Suppress FutureWarning for silently downcasting object dtype arrays
pd.set_option('future.no_silent_downcasting', True)

class BacktestEngine:
    def __init__(self, strategies, initial_cash=10000, fee=0.001):
        """
        strategies: a list of strategy instances (C++ classes).
        """
        self.strategies = strategies if isinstance(strategies, list) else [strategies]
        self.initial_cash = initial_cash
        self.fee = fee
        
        load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"))
        user = os.getenv("POSTGRES_USER")
        pw = os.getenv("POSTGRES_PASSWORD")
        db = os.getenv("POSTGRES_DB", "trading_db")
        host = "localhost" # Connect to localhost for local testing
        
        db_url = os.getenv("DATABASE_URL", f"postgresql://{user}:{pw}@{host}:5432/{db}")
        # If DATABASE_URL starts with Host= (old format), override it
        if db_url.startswith("Host="):
            db_url = f"postgresql://{user}:{pw}@{host}:5432/{db}"
        self.db_engine = create_engine(db_url)

    def load_data(self, epic, resolution, start=None, end=None, tz='Asia/Taipei'):
        try:
            sql = "SELECT time, open_price as open, high_price as high, low_price as low, close_price as close, volume FROM market_candles WHERE epic = :epic AND resolution = :resolution"
            params = {"epic": epic, "resolution": resolution}
            
            if start:
                sql += " AND time >= :start"
                params["start"] = start
            if end:
                sql += " AND time <= :end"
                params["end"] = end
            
            sql += " ORDER BY time ASC"
            
            df = pd.read_sql(text(sql), self.db_engine, params=params)
            if df.empty:
                return None
                
            df.set_index("time", inplace=True)
            df.index = pd.to_datetime(df.index)
            
            # Localize to UTC then convert to target timezone
            if df.index.tz is None:
                df.index = df.index.tz_localize('UTC')
            if tz:
                df.index = df.index.tz_convert(tz)
                
            cols = ['open', 'high', 'low', 'close', 'volume']
            df[cols] = df[cols].apply(pd.to_numeric, errors='coerce')
            return df
        except Exception as e:
            print(f"[ERROR] DB Load failure for {epic} {resolution}: {e}")
            return None

    def run_backtest(self, config: BacktestConfigDTO):
        all_entries, all_exits, all_exec_prices = [], [], []
        all_short_entries, all_short_exits = [], []
        all_close, all_stop_lines = {}, {}
        all_sizes = []

        epics = [config.epics] if isinstance(config.epics, str) else config.epics
        resolutions = [config.resolutions] if isinstance(config.resolutions, str) else config.resolutions

        for strategy in self.strategies:
            for epic in epics:
                for res in resolutions:
                    df = self.load_data(epic, res, start=config.start, end=config.end, tz=config.tz)
                    if df is None: continue

                    s_name = strategy.name() if callable(strategy.name) else strategy.name
                    label = f"{s_name}_{epic}_{res}"
                    
                    # C++ Batch Execution
                    batch_res = strategy.run_batch(
                        df['open'].to_list(), df['high'].to_list(),
                        df['low'].to_list(), df['close'].to_list(),
                        df['volume'].to_list()
                    )
                    
                    entries = pd.Series(batch_res.entries, index=df.index).shift(1).fillna(False)
                    
                    if config.use_ml:
                        from .ml_handler import MLInferenceHandler
                        handler = MLInferenceHandler()
                        # Convert strategy name to key (e.g., 'YuBrokenBottom' -> 'yu_broken_bottom')
                        s_key = s_name.lower().replace('strategy', '').strip()
                        # Handle camelCase to snake_case if needed, but here we just do simple lower
                        # Or better: use a reliable mapping
                        if 'broken' in s_key: s_key = 'yu_broken_bottom'
                        
                        entries = handler.apply_ml_filter(s_key, df, entries)

                    res_exits = pd.Series(batch_res.exits, index=df.index)
                    res_exit_prices = pd.Series(batch_res.exit_prices, index=df.index)
                    
                    res_short_entries = pd.Series(getattr(batch_res, 'short_entries', [False]*len(df)), index=df.index).shift(1).fillna(False)
                    res_short_exits = pd.Series(getattr(batch_res, 'short_exits', [False]*len(df)), index=df.index)

                    exec_price = df['open'].copy()
                    exec_price.loc[res_exits] = res_exit_prices[res_exits]
                    exec_price.loc[res_short_exits] = res_exit_prices[res_short_exits]
                    
                    # Position Sizing Logic
                    sl_series = pd.Series(getattr(batch_res, 'stop_lines', [np.nan]*len(df)), index=df.index)
                    if config.sizing_type == 'RISK' and not sl_series.isna().all():
                        risk_pct = config.position_size / 100.0
                        entry_price = df['open']
                        dist_pct = (entry_price - sl_series).abs() / entry_price
                        dist_pct = dist_pct.replace(0, np.nan)
                        # Size expressed as % of equity/cash (leverage-aware)
                        size_vals = risk_pct / dist_pct
                        size_vals = size_vals.fillna(0.0) # No risk if no SL
                        size_type = 'percent'
                    elif config.sizing_type == 'FIXED':
                        # Fixed units
                        size_vals = pd.Series(config.position_size, index=df.index)
                        size_type = 'amount'
                    else:
                        # Default All-in (100% of cash)
                        size_vals = pd.Series(1.0, index=df.index)
                        size_type = 'percent'

                    all_entries.append(entries.rename(label))
                    all_exits.append(res_exits.rename(label))
                    all_short_entries.append(res_short_entries.rename(label))
                    all_short_exits.append(res_short_exits.rename(label))
                    all_exec_prices.append(exec_price.rename(label))
                    all_close[label] = df['close']
                    all_stop_lines[label] = sl_series.rename(label)
                    all_sizes.append(size_vals.rename(label))

        if not all_entries: return None, None

        # Infer frequency from index
        freq = df.index.inferred_freq if 'df' in locals() else None

        portfolio = vbt.Portfolio.from_signals(
            close=pd.concat(all_close.values(), axis=1, keys=all_close.keys()).astype(np.float64),
            entries=pd.concat(all_entries, axis=1).astype(bool),
            exits=pd.concat(all_exits, axis=1).astype(bool),
            short_entries=pd.concat(all_short_entries, axis=1).astype(bool) if all_short_entries else None,
            short_exits=pd.concat(all_short_exits, axis=1).astype(bool) if all_short_exits else None,
            size=pd.concat(all_sizes, axis=1).astype(np.float64) if all_sizes else None,
            size_type=size_type if all_sizes else None,
            price=pd.concat(all_exec_prices, axis=1).astype(np.float64),
            init_cash=self.initial_cash,
            fees=self.fee,
            cash_sharing=len(all_entries) > 1,
            group_by=False,
            call_seq='auto',
            freq=freq
        )
        return portfolio, all_stop_lines

    def optimize(self, epic, resolution, param_grid, start=None, end=None, df=None, tz='Asia/Taipei'):
        strategy = self.strategies[0]
        if df is None:
            df = self.load_data(epic, resolution, start=start, end=end, tz=tz)
            
        if df is None or len(df) == 0: return None
        
        print(f"[INFO] Processing {len(df)} bars from {df.index[0].date()} to {df.index[-1].date()}")

        keys = list(param_grid.keys())
        combinations = list(itertools.product(*param_grid.values()))
        entries_dict, exits_dict, exec_prices_dict = {}, {}, {}

        algo_class = type(strategy)
        for combo in tqdm(combinations, desc="Optimizing Rows"):
            params = dict(zip(keys, combo))
            s_inst = algo_class(params)
            
            batch_res = s_inst.run_batch(
                df['open'].to_list(), df['high'].to_list(),
                df['low'].to_list(), df['close'].to_list(),
                df['volume'].to_list()
            )
            
            key = tuple(combo)
            entries_dict[key] = pd.Series(batch_res.entries, index=df.index).shift(1).fillna(False)
            exits = pd.Series(batch_res.exits, index=df.index)
            exit_prices = pd.Series(batch_res.exit_prices, index=df.index)
            exits_dict[key] = exits
            
            exec_price = df['open'].copy()
            exec_price.loc[exits] = exit_prices[exits]
            exec_prices_dict[key] = exec_price

        if not entries_dict: return None

        multi_idx = pd.MultiIndex.from_tuples(entries_dict.keys(), names=keys)
        
        freq = df.index.inferred_freq

        portfolio = vbt.Portfolio.from_signals(
            close=df['close'].astype(np.float64),
            entries=pd.DataFrame(entries_dict, columns=multi_idx).astype(bool),
            exits=pd.DataFrame(exits_dict, columns=multi_idx).astype(bool),
            price=pd.DataFrame(exec_prices_dict, columns=multi_idx).astype(np.float64),
            init_cash=self.initial_cash, fees=self.fee,
            freq=freq
        )
        return portfolio
