from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, Dict, Any

class Actions:
    BUY = "BUY"
    SELL = "SELL"
    CLOSE = "CLOSE"
    UPDATE_SL = "UPDATE_SL"

class SizingTypes:
    FIXED = "FIXED"
    RISK = "RISK"

@dataclass
class TradeSignal:
    epic: str
    action: str  # Actions.BUY, Actions.SELL, etc.
    strategy: str
    price: float = 0.0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    resolution: str = "MINUTE"
    deal_id: Optional[str] = None
    source: str = "AUTO"
    use_ml: bool = False
    position_size: Optional[float] = None
    sizing_type: str = SizingTypes.FIXED

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TradeSignal':
        return cls(
            epic=data.get("epic", ""),
            action=data.get("action", ""),
            strategy=data.get("strategy", "Unknown"),
            price=float(data.get("price", 0)),
            stop_loss=data.get("stop_loss"),
            take_profit=data.get("take_profit"),
            resolution=data.get("resolution", "MINUTE"),
            deal_id=data.get("deal_id"),
            source=data.get("source", "AUTO"),
            use_ml=data.get("use_ml", False),
            position_size=data.get("position_size"),
            sizing_type=data.get("sizing_type", SizingTypes.FIXED)
        )

@dataclass
class TradeRecord:
    deal_id: str
    deal_reference: str
    epic: str
    direction: str
    size: float
    entry_price: float
    entry_time: datetime
    resolution: Optional[str] = None
    strategy: Optional[str] = None
    source: str = "AUTO"
    leverage: Optional[int] = None
    currency: str = "USD"
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    realized_pnl: Optional[float] = None
    exit_type: Optional[str] = None

@dataclass
class PositionDTO:
    """Contract DTO for active positions shared with C++ Engine."""
    deal_id: str
    epic: str
    direction: str
    entry_price: float
    entry_time: str
    size: float
    resolution: Optional[str]
    strategy: Optional[str]
    stop_level: float = 0.0
    profit_level: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "deal_id": self.deal_id,
            "epic": self.epic,
            "direction": self.direction,
            "entry_price": self.entry_price,
            "entry_time": self.entry_time,
            "size": self.size,
            "resolution": self.resolution,
            "strategy": self.strategy,
            "stop_level": self.stop_level,
            "profit_level": self.profit_level
        }

@dataclass
class TradingSettingsDTO:
    """System-wide trading configurations."""
    default_size: float = 0.01
    risk_pct_per_trade: float = 0.01
    use_dynamic_sizing: bool = True
    max_open_positions: int = 10
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TradingSettingsDTO':
        return cls(
            default_size=float(data.get("default_size", 0.01)),
            risk_pct_per_trade=float(data.get("risk_pct_per_trade", 0.01)),
            use_dynamic_sizing=str(data.get("use_dynamic_sizing", "true")).lower() == "true",
            max_open_positions=int(data.get("max_open_positions", 10))
        )

@dataclass
class HistoryBarDTO:
    """Historical bar data format sent to C++ Engine."""
    time: str
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "time": self.time,
            "open_price": self.open_price,
            "high_price": self.high_price,
            "low_price": self.low_price,
            "close_price": self.close_price,
            "volume": self.volume
        }

@dataclass
class TradeCostDTO:
    """Represents a transaction cost (SWAP or COMMISSION)."""
    deal_id: str
    date: date
    type: str # SWAP, COMMISSION
    amount: float
    currency: str
    epic: str
    raw_reference: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "deal_id": self.deal_id,
            "date": self.date,
            "type": self.type,
            "amount": self.amount,
            "currency": self.currency,
            "epic": self.epic,
            "raw_reference": self.raw_reference
        }
