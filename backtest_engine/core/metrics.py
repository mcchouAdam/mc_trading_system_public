import pandas as pd
import numpy as np
from core.dtos import PortfolioMetricsDTO

def calculate_advanced_metrics(portfolio, consolidated_trades, initial_cash):
    """
    Calculate advanced performance metrics from portfolio and consolidated trades.
    """
    all_pnl = portfolio.trades.records['pnl']
    total_trades = len(all_pnl)
    
    # 1. Main Stats
    total_profit = float(all_pnl.sum())
    total_return_pct = (total_profit / initial_cash) * 100
    winning_trades = int((all_pnl > 0).sum())
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    gross_profit = float(all_pnl[all_pnl > 0].sum())
    gross_loss = float(abs(all_pnl[all_pnl < 0].sum()))
    pf = (gross_profit / gross_loss) if gross_loss != 0 else np.inf

    # 2. Equity and MDD
    n_cols = len(portfolio.wrapper.columns)
    portfolio_value = portfolio.value().sum(axis=1) - (n_cols - 1) * initial_cash
    combined_returns = portfolio_value.pct_change().fillna(0)
    mdd = abs((portfolio_value / portfolio_value.cummax() - 1).min() * 100)
    
    # 3. Sharpe
    ann_factor = 252  # daily bars
    sharpe = (combined_returns.mean() / combined_returns.std() * np.sqrt(ann_factor)) if combined_returns.std() != 0 else 0

    # 4. Win/Loss metrics
    all_rets = consolidated_trades['return'] if not consolidated_trades.empty else pd.Series()
    avg_win = float(all_pnl[all_pnl > 0].mean()) if any(all_pnl > 0) else 0
    avg_loss = float(all_pnl[all_pnl < 0].mean()) if any(all_pnl < 0) else 0
    avg_win_pct = float(all_rets[all_rets > 0].mean()) * 100 if any(all_rets > 0) else 0
    avg_loss_pct = float(all_rets[all_rets < 0].mean()) * 100 if any(all_rets < 0) else 0
    best_trade = float(all_pnl.max()) if total_trades > 0 else 0
    worst_trade = float(all_pnl.min()) if total_trades > 0 else 0
    
    # Expectancy = (WinRate * AvgWin) + (LossRate * AvgLoss)
    expectancy = (win_rate/100 * avg_win) + ((1 - win_rate/100) * avg_loss)
    
    avg_dur = consolidated_trades['duration'].mean() if not consolidated_trades.empty else pd.Timedelta(0)
    avg_dur_str = str(avg_dur).split('.')[0]

    return PortfolioMetricsDTO(
        total_profit=total_profit,
        total_return_pct=total_return_pct,
        win_rate=win_rate,
        profit_factor=pf,
        mdd=mdd,
        sharpe=sharpe,
        total_trades=total_trades,
        avg_win=avg_win,
        avg_loss=avg_loss,
        avg_win_pct=avg_win_pct,
        avg_loss_pct=avg_loss_pct,
        best_trade=best_trade,
        worst_trade=worst_trade,
        expectancy=expectancy,
        avg_duration_str=avg_dur_str,
        portfolio_value=portfolio_value
    )
