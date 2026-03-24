import numpy as np
from typing import Optional
from core.dtos import MonteCarloResultDTO


def run_monte_carlo(
    trade_pnls,
    initial_cash: float,
    n_simulations: int = 1000,
    ruin_threshold_pct: float = 50.0,
    seed: Optional[int] = None,
) -> Optional[MonteCarloResultDTO]:
    """
    Monte Carlo simulation by randomly shuffling historical trade PnL outcomes.

    The key insight: your strategy will always produce the same N trades with the
    same PnL values.  But the ORDER those trades happen in real life is uncertain.
    This function explores all shuffled orderings to answer:
        "How bad could things get if my luck was worse?"

    Args:
        trade_pnls:           Array-like of individual trade PnL values (in $)
        initial_cash:         Starting portfolio value ($)
        n_simulations:        Number of random orderings to simulate (default 1000)
        ruin_threshold_pct:   % Max Drawdown considered "ruin" (default 50 %)
        seed:                 Optional random seed for reproducibility

    Returns:
        dict with:
            - Percentile breakdowns for Final Return and Max Drawdown
            - Ruin probability
            - Raw arrays (final_returns, max_drawdowns) for histogram charting
    """
    if seed is not None:
        np.random.seed(seed)

    pnls = np.array(trade_pnls, dtype=float)
    n_trades = len(pnls)

    if n_trades == 0:
        return None

    final_returns = np.empty(n_simulations)
    max_drawdowns = np.empty(n_simulations)

    for i in range(n_simulations):
        shuffled = np.random.permutation(pnls)

        # Build equity curve efficiently with cumsum
        equity = np.empty(n_trades + 1)
        equity[0] = initial_cash
        np.cumsum(shuffled, out=equity[1:])
        equity[1:] += initial_cash

        # Final return %
        final_returns[i] = (equity[-1] - initial_cash) / initial_cash * 100.0

        # Max drawdown: largest peak-to-trough decline (stored as positive %)
        peak = np.maximum.accumulate(equity)
        drawdowns = (equity - peak) / peak
        max_drawdowns[i] = abs(drawdowns.min()) * 100.0

    ruin_prob = float(np.sum(max_drawdowns > ruin_threshold_pct)) / n_simulations * 100.0

    return MonteCarloResultDTO(
        n_simulations=n_simulations,
        n_trades=n_trades,
        ruin_threshold_pct=ruin_threshold_pct,
        ruin_probability=round(ruin_prob, 2),

        # Final Return percentiles
        return_p5=round(float(np.percentile(final_returns,  5)), 2),
        return_p25=round(float(np.percentile(final_returns, 25)), 2),
        return_p50=round(float(np.percentile(final_returns, 50)), 2),
        return_p75=round(float(np.percentile(final_returns, 75)), 2),
        return_p95=round(float(np.percentile(final_returns, 95)), 2),
        return_mean=round(float(np.mean(final_returns)), 2),

        # Max Drawdown percentiles (all positive %)
        mdd_p5=round(float(np.percentile(max_drawdowns,  5)), 2),
        mdd_p25=round(float(np.percentile(max_drawdowns, 25)), 2),
        mdd_p50=round(float(np.percentile(max_drawdowns, 50)), 2),
        mdd_p75=round(float(np.percentile(max_drawdowns, 75)), 2),
        mdd_p95=round(float(np.percentile(max_drawdowns, 95)), 2),
        mdd_mean=round(float(np.mean(max_drawdowns)), 2),

        # Raw arrays for histogram rendering in the HTML report
        final_returns=[round(float(v), 2) for v in final_returns],
        max_drawdowns=[round(float(v), 2) for v in max_drawdowns]
    )
