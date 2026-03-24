from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional

@dataclass
class BacktestConfigDTO:
    """Data Transfer Object for Backtest Engine configuration."""
    epics: List[str]
    resolutions: List[str]
    params: Dict[str, Any]
    use_ml: bool = False
    start: Optional[str] = None
    end: Optional[str] = None
    sizing_type: str = 'FIXED'
    position_size: float = 1.0
    tz: str = 'Asia/Taipei'


@dataclass
class MonteCarloResultDTO:
    """Data Transfer Object for Monte Carlo Simulation results."""
    n_simulations: int
    n_trades: int
    ruin_threshold_pct: float
    ruin_probability: float
    
    return_p5: float
    return_p25: float
    return_p50: float
    return_p75: float
    return_p95: float
    return_mean: float
    
    mdd_p5: float
    mdd_p25: float
    mdd_p50: float
    mdd_p75: float
    mdd_p95: float
    mdd_mean: float
    
    final_returns: List[float]
    max_drawdowns: List[float]

    # Added by calling actions later
    actual_return_pct: Optional[float] = None
    actual_mdd_pct: Optional[float] = None

    def to_dict(self):
        return asdict(self)


@dataclass
class PortfolioMetricsDTO:
    """Data Transfer Object for Portfolio Metrics."""
    total_profit: float
    total_return_pct: float
    win_rate: float
    profit_factor: float
    mdd: float
    sharpe: float
    total_trades: int
    avg_win: float
    avg_loss: float
    avg_win_pct: float
    avg_loss_pct: float
    best_trade: float
    worst_trade: float
    expectancy: float
    avg_duration_str: str
    portfolio_value: Any  # Usually a pd.Series

    def to_dict(self):
        return asdict(self)


@dataclass
class ReportDataDTO:
    """Data Transfer Object for Standard Backtest HTML Report."""
    df: Any
    trades_df: Any
    stop_lines: Any
    report_file: str
    strategy_name: str
    target_tz: str = 'Asia/Taipei'
    portfolio_values: Optional[Any] = None
    stats: Optional[Dict[str, Any]] = None
    multi_stats: Optional[List[Dict[str, Any]]] = None
    multi_returns: Optional[List[Dict[str, Any]]] = None
    mc_results: Optional[MonteCarloResultDTO] = None
    indicators: Optional[List[Dict[str, Any]]] = None

    def to_dict(self):
        return asdict(self)


@dataclass
class AuditReportDataDTO:
    """Data Transfer Object for Audit HTML Report."""
    df: Any
    live_trades_df: Any
    bt_trades_df: Any
    live_equity: Any
    bt_equity: Any
    comparison_stats: Dict[str, Any]
    report_file: str
    strategy_name: str
    target_tz: str = 'UTC'

    def to_dict(self):
        return asdict(self)


@dataclass
class WfoConfigDTO:
    """Data Transfer Object for Walk-Forward Optimization configuration."""
    epic: str
    resolution: str
    param_grid: Dict[str, List[Any]]
    n_splits: int = 5
    train_ratio: float = 0.7
    start: Optional[str] = None
    end: Optional[str] = None
    tz: str = 'Asia/Taipei'


@dataclass
class WfoWindowResultDTO:
    """Data Transfer Object for a single WFO window result."""
    split: int
    train_start: Any
    train_end: Any
    test_start: Any
    test_end: Any
    best_params: Dict[str, Any]
    train_return_pct: float
    test_return_pct: float
    test_mdd_pct: float
    test_trades: int


@dataclass
class WfoResultDTO:
    """Data Transfer Object for full Walk-Forward Optimization results."""
    strategy: str
    epic: str
    resolution: str
    n_splits: int
    train_ratio: float
    windows: List[WfoWindowResultDTO]
    combined_test_return: float
    avg_train_return: float
    worst_test_mdd: float
    profitable_splits: int
    efficiency_ratio: float

    def to_dict(self):
        return asdict(self)


@dataclass
class ChartOutputDataDTO:
    """Data Transfer Object for processed chart data (ready for JSON)."""
    ohlc_data: List[Dict[str, Any]]
    benchmark_data: List[Dict[str, Any]]
    returns_data: List[Dict[str, Any]]
    stop_segments: List[List[Dict[str, Any]]]
    markers: List[Dict[str, Any]]
    trade_lines: List[List[Dict[str, Any]]]
    trades_json: List[Dict[str, Any]]

    def to_dict(self):
        return asdict(self)
