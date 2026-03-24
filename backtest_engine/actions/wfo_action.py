import numpy as np
from actions.base import BaseAction
from analysis.walk_forward import run_wfo
from core.dtos import WfoConfigDTO

class WfoAction(BaseAction):
    def execute(self, args, engine):
        epics = [e.strip() for e in args.epics.split(',')]
        resolutions = [r.strip() for r in args.resolutions.split(',')]
        
        epic, res = epics[0], resolutions[0]
        grid = self._parse_opt_range(args.opt)

        if not grid:
            print("[ERROR] --opt is required for WFO mode.")
            return

        config = WfoConfigDTO(
            epic=epic,
            resolution=res,
            param_grid=grid,
            n_splits=args.wfo_splits,
            train_ratio=args.wfo_train_ratio,
            start=args.from_date,
            end=args.to_date,
            tz=args.timezone
        )
        wfo_result = run_wfo(engine, config)

        if wfo_result:
            self._print_summary(wfo_result)

    def _parse_opt_range(self, opt_str):
        opt_grid = {}
        if not opt_str: return opt_grid
        targets = opt_str.split('|')
        for target in targets:
            if '=' not in target: continue
            key, val_range = target.split('=')
            key = key.strip()
            if ':' in val_range:
                parts = val_range.split(':')
                start, end = float(parts[0]), float(parts[1])
                step = float(parts[2]) if len(parts) > 2 else 1.0
                vals = [round(v, 4) for v in np.arange(start, end + (step/1000.0), step).tolist()]
                opt_grid[key] = vals
            else:
                opt_grid[key] = [float(v) if '.' in v else int(v) for v in val_range.split(',')]
        return opt_grid

    def _print_summary(self, wfo_result):
        print("\n" + "=" * 60)
        print("WALK-FORWARD SUMMARY")
        print("=" * 60)
        print(f"{'Split':<6} {'Train Period':<25} {'Best Params':<30} "
              f"{'Train Ret':>10} {'Test Ret':>10} {'Test MDD':>10} {'Trades':>7}")
        print("-" * 100)
        for w in wfo_result.windows:
            params_str = ', '.join(f"{k}={v}" for k, v in w.best_params.items())
            train_period = f"{w.train_start.date()} → {w.train_end.date()}"
            sign = '+' if w.test_return_pct >= 0 else ''
            print(f"  {w.split:<4} {train_period:<25} {params_str:<30} "
                  f"{w.train_return_pct:>+9.1f}% "
                  f"{sign}{w.test_return_pct:>9.1f}% "
                  f"{w.test_mdd_pct:>9.1f}% "
                  f"{w.test_trades:>7}")
        print("-" * 100)
        er = wfo_result.efficiency_ratio
        er_label = '✓ good' if er > 0.5 else ('△ moderate' if er > 0 else '✗ overfit')
        print(f"\n  Combined OOS Return : {wfo_result.combined_test_return:+.2f}%")
        print(f"  Worst Test MDD      : {wfo_result.worst_test_mdd:.2f}%")
        print(f"  Profitable Splits   : {wfo_result.profitable_splits}/{wfo_result.n_splits}")
        print(f"  Efficiency Ratio    : {er:.2f}  [{er_label}]")
