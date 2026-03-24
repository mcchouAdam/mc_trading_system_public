from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Optional
from datetime import datetime

@dataclass
class MLSampleDTO:
    """A single labelled training sample for the ML model."""
    trade_id: str
    timestamp: str
    epic: str
    resolution: str
    features: Dict[str, Any]
    outcome: int
    pnl_ratio: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class YuBrokenBottomFeaturesDTO:
    """Features specific to the YuBrokenBottom strategy."""
    rsi: float
    volatility: float
    dist_ema20: float
    vol_ratio: float
    atr_norm: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CollectionConfigDTO:
    """Configuration for data collection (feature extraction)."""
    strategy: str
    epics: Optional[str] = None
    resolutions: Optional[str] = None
    overwrite: bool = False

@dataclass
class TrainingConfigDTO:
    """Configuration for model training."""
    strategy: str
    notes: str = ""

@dataclass
class ModelVersionDTO:
    """Details for a specific version of a model."""
    version: str
    path: str
    trained_date: str
    status: str  # 'candidate', 'production', 'archived'
    notes: str = ""
    dataset: Optional[str] = None
    promoted_date: Optional[str] = None
    demoted_date: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class StrategyRegistryDTO:
    """Full registry entry for a strategy."""
    strategy_name: str
    versions: List[ModelVersionDTO] = field(default_factory=list)
    production: Optional[str] = None  # Current production model path
    enabled: bool = True
    threshold: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "threshold": self.threshold,
            "production": self.production,
            "versions": [v.to_dict() for v in self.versions]
        }
