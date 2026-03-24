import numpy as np
import pandas as pd
from typing import Optional
from core.dtos import BacktestConfigDTO, WfoConfigDTO, WfoWindowResultDTO, WfoResultDTO


def run_wfo(
    engine,
    config: WfoConfigDTO
) -> Optional[WfoResultDTO]:
    """
    Walk-Forward Optimization (Rolling Window).

    Splits the full historical data into N sequential windows.
    For each window:
        1. [Train period] Grid-search for best params by Total Return
        2. [Test period]  Backtest using those best params (out-of-sample)
    
    Finally, concatenates all out-of-sample equity curves to produce the
    "true" WFO equity curve, which is free of in-sample bias.

    Args:
        engine:       BacktestEngine instance (single strategy assumed)
        epic:         Asset ticker (e.g. 'BTCUSD')
        resolution:   Bar resolution (e.g. 'DAY')
        param_grid:   Dict of param -> list of values, same format as --opt
        n_splits:     Number of train/test windows (default 5)
        train_ratio:  Fraction of each window used for training (default 0.7)

    Returns:
        dict with per-window results and combined out-of-sample metrics,
        or None if data insufficient.
    """
    strategy = engine.strategies[0]
    s_name = strategy.name() if callable(strategy.name) else strategy.name
    
    full_df = engine.load_data(config.epic, config.resolution, start=config.start, end=config.end, tz=config.tz)
    if full_df is None or len(full_df) == 0:
        print(f"Error: No data for {config.epic} {config.resolution}")
        return None

    n_bars = len(full_df)
    window_size = n_bars // config.n_splits

    if window_size < 30:
        print(f"Error: Not enough data for {config.n_splits} splits "
              f"(only {n_bars} bars → {window_size} bars per window, need ≥30)")
        return None

    train_size = int(window_size * config.train_ratio)
    test_size  = window_size - train_size

    if test_size < 5:
        print(f"Error: Test window too small ({test_size} bars). "
              f"Reduce n_splits or train_ratio.")
        return None

    n_combos = 1
    for v in config.param_grid.values():
        n_combos *= len(v)
    print(f"\nWalk-Forward Optimization: {s_name} on {config.epic} {config.resolution}")
    print(f"  Data: {full_df.index[0].date()} → {full_df.index[-1].date()} "
          f"({n_bars} bars)")
    print(f"  Splits: {config.n_splits}  |  Window: {window_size} bars  "
          f"|  Train: {train_size}  |  Test: {test_size}")
    print(f"  Grid size: {n_combos} combinations")
    print(f"  Selection metric: Total Return [%]")
    print("=" * 60)

    windows = []
    all_test_pnl_series = []   # list of (test_start_idx, equity_series)

    for i in range(config.n_splits):
        split_start = i * window_size
        split_end   = split_start + window_size if i < config.n_splits - 1 else n_bars

        train_start_idx = split_start
        train_end_idx   = split_start + train_size - 1
        test_start_idx  = train_end_idx + 1
        test_end_idx    = split_end - 1

        # Guard against out-of-range
        if test_end_idx >= n_bars:
            test_end_idx = n_bars - 1
        if test_start_idx > test_end_idx:
            print(f"  Split {i+1}: skipped (test window empty)")
            continue

        train_df = full_df.iloc[train_start_idx : train_end_idx + 1]
        test_df  = full_df.iloc[test_start_idx  : test_end_idx  + 1]

        train_start = full_df.index[train_start_idx]
        train_end   = full_df.index[train_end_idx]
        test_start  = full_df.index[test_start_idx]
        test_end    = full_df.index[test_end_idx]

        # ── 1. Optimize on Train period ──────────────────────────────
        train_portfolio = engine.optimize(config.epic, config.resolution, config.param_grid, df=train_df, tz=config.tz)
        if train_portfolio is None:
            print(f"  Split {i+1}: optimization returned no results, skipping.")
            continue

        # Select best params by Total Return
        train_returns = train_portfolio.total_return()
        best_idx      = train_returns.idxmax()
        best_return   = float(train_returns.max()) * 100

        # Reconstruct best_params dict from MultiIndex tuple
        if isinstance(best_idx, tuple):
            best_params = dict(zip(list(config.param_grid.keys()), best_idx))
        else:
            # Single-param grid → best_idx is a scalar
            key = list(config.param_grid.keys())[0]
            best_params = {key: best_idx}

        # ── 2. Backtest on Test period using best params ─────────────
        config_bt = BacktestConfigDTO(
            epics=[config.epic], 
            resolutions=[config.resolution],
            params=best_params, 
            tz=config.tz
        )
        test_portfolio, _ = engine.run_backtest(config_bt)
        # Slice the test portfolio's value to the test window only
        label = f"{s_name}_{config.epic}_{config.resolution}"
        if test_portfolio is None:
            test_return = 0.0
            test_mdd    = 0.0
            test_trades = 0
        else:
            col_values = test_portfolio[label].value()
            # Crop to test period
            col_values = col_values[(col_values.index >= test_start) &
                                    (col_values.index <= test_end)]

            if len(col_values) > 1:
                test_return = (float(col_values.iloc[-1]) - engine.initial_cash) \
                              / engine.initial_cash * 100
                peak    = col_values.cummax()
                test_mdd = abs(((col_values - peak) / peak).min() * 100)
            else:
                test_return = 0.0
                test_mdd    = 0.0

            # Count test-period trades
            all_trade_rec = test_portfolio[label].trades.records
            trade_df = pd.DataFrame(all_trade_rec)
            if len(trade_df) > 0:
                time_idx = test_portfolio[label].wrapper.index
                trade_df['entry_time'] = time_idx[trade_df['entry_idx']]
                in_test = (trade_df['entry_time'] >= test_start) & \
                          (trade_df['entry_time'] <= test_end)
                test_trades = int(in_test.sum())
                all_test_pnl_series.append(col_values)
            else:
                test_trades = 0

        window_result = WfoWindowResultDTO(
            split=i + 1,
            train_start=train_start,
            train_end=train_end,
            test_start=test_start,
            test_end=test_end,
            best_params=best_params,
            train_return_pct=round(best_return, 2),
            test_return_pct=round(test_return, 2),
            test_mdd_pct=round(test_mdd, 2),
            test_trades=test_trades,
        )
        windows.append(window_result)

        # ── Console output ───────────────────────────────────────────
        params_str = ', '.join(f"{k}={v}" for k, v in best_params.items())
        ret_arrow  = '✓' if test_return > 0 else '✗'
        print(f"  Split {i+1} | "
              f"Train: {train_start.date()}→{train_end.date()} "
              f"| Test: {test_start.date()}→{test_end.date()}")
        print(f"         Best params: [{params_str}]  "
              f"Train={best_return:+.1f}%  "
              f"Test={test_return:+.1f}% {ret_arrow}  "
              f"Test MDD={test_mdd:.1f}%  Trades={test_trades}")

    if not windows:
        print("WFO: No valid splits produced.")
        return None

    # ── Combined out-of-sample metrics ──────────────────────────────
    all_test_returns    = [w.test_return_pct  for w in windows]
    all_train_returns   = [w.train_return_pct for w in windows]
    all_test_mdds       = [w.test_mdd_pct     for w in windows]

    combined_test_return  = sum(all_test_returns)
    avg_train_return      = np.mean(all_train_returns) if all_train_returns else 0
    worst_test_mdd        = max(all_test_mdds) if all_test_mdds else 0
    profitable_splits     = sum(1 for w in windows if w.test_return_pct > 0)

    # Efficiency Ratio: avg(OOS return) / avg(IS return)
    efficiency_ratio = (np.mean(all_test_returns) / avg_train_return) \
                       if avg_train_return != 0 else 0.0

    print("=" * 60)
    print(f"  Combined Out-of-Sample Return:  {combined_test_return:+.2f}%")
    print(f"  Worst Test-Window MDD:          {worst_test_mdd:.2f}%")
    print(f"  Profitable Splits:              {profitable_splits}/{len(windows)}")
    print(f"  WFO Efficiency Ratio:           {efficiency_ratio:.2f}  "
          f"({'✓ good' if efficiency_ratio > 0.5 else ('△ ok' if efficiency_ratio > 0 else '✗ overfit')})")

    return WfoResultDTO(
        strategy=s_name,
        epic=config.epic,
        resolution=config.resolution,
        n_splits=config.n_splits,
        train_ratio=config.train_ratio,
        windows=windows,
        combined_test_return=round(combined_test_return, 2),
        avg_train_return=round(float(avg_train_return), 2),
        worst_test_mdd=round(worst_test_mdd, 2),
        profitable_splits=profitable_splits,
        efficiency_ratio=round(efficiency_ratio, 3),
    )
