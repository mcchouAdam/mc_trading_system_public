import os
import plotly.graph_objects as go
from datetime import datetime
import numpy as np
from actions.base import BaseAction

class OptimizeAction(BaseAction):
    def execute(self, args, engine):
        strategy_names = [s.strip() for s in args.strategy.split(',')]
        epics = [e.strip() for e in args.epics.split(',')]
        resolutions = [r.strip() for r in args.resolutions.split(',')]
        
        s_name = strategy_names[0]
        epic, res = epics[0], resolutions[0]
        
        print(f"\nOptimizing {s_name} on {epic} {res}...")
            
        grid = self._parse_opt_range(args.opt)
        if not grid:
            print("\n" + "!"*50)
            print("[ERROR] --opt is required for optimization mode.")
            print("Example: --mode optimize --opt \"FAST=10:50:5|SLOW=20:100:10\"")
            print("!"*50 + "\n")
            return

        portfolio = engine.optimize(epic, res, grid, start=args.from_date, end=args.to_date, tz=args.timezone)
        
        if portfolio:
            start_ts = portfolio.wrapper.index[0].strftime('%Y%m%d')
            end_ts = portfolio.wrapper.index[-1].strftime('%Y%m%d')
            date_range_str = f"{start_ts}_{end_ts}"

            returns = portfolio.total_return()
            print("\n" + "="*50)
            print(f"TOP 5 PARAMS ({s_name} on {epic} {res})")
            print("="*50)
            print(returns.sort_values(ascending=False).head(5))
            
            if len(grid) == 2:
                self._generate_heatmap(s_name, epic, res, grid, returns, date_range_str)
            elif len(grid) > 2:
                print(f"\n[INFO] Heatmap currently only supports 2D (found {len(grid)} dims).")

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

    def _generate_heatmap(self, s_name, epic, res, grid, returns, date_range_str):
        keys = list(grid.keys())
        heatmap_data = (returns * 100).unstack(level=1)
        
        fig = go.Figure(data=go.Heatmap(
            z=heatmap_data.values,
            x=heatmap_data.columns.astype(str),
            y=heatmap_data.index.astype(str),
            colorscale='Viridis',
            hovertemplate=f"{keys[1]}: %{{x}}<br>{keys[0]}: %{{y}}<br>Return: %{{z}}%<extra></extra>"
        ))
        
        fig.update_layout(
            title=f'Optimization: {s_name} {epic} {res} ({date_range_str})',
            xaxis_title=keys[1],
            yaxis_title=keys[0],
            template='plotly_dark'
        )
        
        reports_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reports")
        os.makedirs(reports_dir, exist_ok=True)
        report_file = os.path.join(reports_dir, f"Opt_{s_name}_{epic}_{res}_{date_range_str}_heatmap.html")
        fig.write_html(report_file)
        print(f"\n[Heatmap saved to: {report_file}]")
