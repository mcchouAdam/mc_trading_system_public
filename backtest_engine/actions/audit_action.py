import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from actions.base import BaseAction
from trade_manager.trade_repository import TradeRepository
from trade_manager.capital_client import CapitalClient
from utils.tv_chart import generate_audit_report
from core.dtos import BacktestConfigDTO, AuditReportDataDTO

class AuditAction(BaseAction):
    def execute(self, args, engine):
        print(f"\n[INFO] Starting Live vs Backtest Audit")
        print(f"Strategy: {args.strategy} | Ticker: {args.epics}")
        
        from_dt = datetime.strptime(args.from_date, "%Y-%m-%d") if args.from_date else None
        to_dt = datetime.strptime(args.to_date, "%Y-%m-%d") if args.to_date else None
        
        # If to_dt is just a date, set it to end of day (23:59:59)
        if to_dt:
            to_dt = to_dt.replace(hour=23, minute=59, second=59)
        
        # 1. Fetch Live Trades from DB
        repo = TradeRepository()
        live_trades = repo.get_trades(
            strategy=args.strategy,
            epic=args.epics,
            from_date=from_dt,
            to_date=to_dt,
            include_open=False
        )
        
        if not live_trades:
            print(f"[WARN] No live trades found for {args.strategy} on {args.epics} in the selected range.")
            return

        print(f"[INFO] Found {len(live_trades)} live trades.")

        # 2. Fetch/Cache Costs (SWAP / Commission)
        if getattr(args, 'skip_sync', False):
            print("[INFO] Skipping cost sync as requested.")
        else:
            self._sync_costs(from_dt, to_dt)

        # 3. Run Matching Backtest
        res = args.resolutions.split(',')[0] if args.resolutions else (live_trades[0]['resolution'] or 'MINUTE_5')
        print(f"[INFO] Running comparison backtest with resolution: {res}")
        
        params = engine.parse_params(args.params)
        
        config = BacktestConfigDTO(
            epics=[args.epics], 
            resolutions=[res], 
            params=params,
            use_ml=getattr(args, 'use_ml', False),
            start=args.from_date,
            end=args.to_date,
            sizing_type=args.sizing_type,
            position_size=args.position_size,
            tz=args.timezone
        )
        portfolio, stop_lines = engine.run_backtest(config)

        if not portfolio:
            print("[ERROR] Could not run matching backtest. Data missing?")
            return

        # 4. Compare and Analyze
        comparison_results = self._compare_trades(live_trades, portfolio, args.timezone)
        
        # 5. Generate Report
        self._generate_audit_report(args, engine, live_trades, portfolio, comparison_results, res)

    def _sync_costs(self, from_dt, to_dt):
        """On-demand sync of SWAP and Commission from Capital.com."""
        if not from_dt or not to_dt: return
        
        start_date = from_dt.date()
        end_date = to_dt.date()
        
        repo = TradeRepository()
        covered = repo.get_covered_cost_dates(start_date, end_date)
        
        # if any date is missing, we re-fetch the whole range to be safe (Capital API is 1-day chunks anyway)
        delta = (end_date - start_date).days
        all_dates = {start_date + timedelta(days=i) for i in range(delta + 1)}
        missing = all_dates - covered
        
        if missing:
            print(f"[INFO] Fetching missing cost records for {len(missing)} days...")
            for d in sorted(list(missing)):
                try:
                    client = CapitalClient()
                    new_costs = client.fetch_costs_for_range(d, d)
                    if new_costs:
                        repo.upsert_trade_costs(new_costs)
                except Exception as e:
                    print(f"[WARN] Cost sync failed for {d}: {e}")
            print("[INFO] Cost sync complete.")

    def _compare_trades(self, live_trades: list, portfolio, target_tz='UTC'):
        """Match live trades to backtest trades and calculate slippage."""
        # Get backtest trades as DataFrame
        bt_label = portfolio.wrapper.columns[0]
        bt_recs = portfolio[bt_label].trades.records
        
        if len(bt_recs) == 0:
            return [{'deal_id': lt['deal_id'], 'matched': False, 'note': 'Backtest has no trades'} for lt in live_trades]
            
        bt_trades_df = pd.DataFrame(bt_recs)
        time_index = portfolio[bt_label].wrapper.index
        bt_trades_df['entry_time'] = time_index[bt_trades_df['entry_idx']]
        
        # Backtest time normalization (assuming DB candles are UTC)
        if not hasattr(bt_trades_df['entry_time'].dt, 'tz') or bt_trades_df['entry_time'].dt.tz is None:
            bt_trades_df['entry_time'] = bt_trades_df['entry_time'].dt.tz_localize('UTC')
        
        bt_trades_df['entry_time_tz'] = bt_trades_df['entry_time'].dt.tz_convert(target_tz)

        results = []
        for lt in live_trades:
            # lt['entry_time'] usually UTC from DB
            lt_time = pd.Timestamp(lt['entry_time'])
            if lt_time.tzinfo is None:
                lt_time = lt_time.tz_localize('UTC')
            
            diffs = (bt_trades_df['entry_time'].dt.tz_convert('UTC') - lt_time.tz_convert('UTC')).abs()
            idx = diffs.idxmin()
            
            if diffs[idx] < pd.Timedelta(hours=4):
                bt_t = bt_trades_df.loc[idx]
                slippage = float(lt['entry_price']) - float(bt_t['entry_price'])
                if lt['direction'] == 'SELL': slippage = -slippage
                
                results.append({
                    'deal_id': lt['deal_id'],
                    'matched': True,
                    'live_entry': lt['entry_price'],
                    'bt_entry': bt_t['entry_price'],
                    'slippage_points': slippage,
                    'live_pnl': lt['realized_pnl'],
                    'bt_pnl': bt_t['pnl'],
                    'timing_diff': diffs[idx].total_seconds() / 60
                })
            else:
                results.append({
                    'deal_id': lt['deal_id'],
                    'matched': False,
                    'note': f"No matching bt trade within 4h (Smallest diff: {diffs[idx].total_seconds()/60:.1f}m)"
                })
        
        return results

    def _generate_audit_report(self, args, engine, live_trades, portfolio, comparison_results, resolution):
        print(f"\n[REPORT] Audit Statistics:")
        matched = [r for r in comparison_results if r['matched']]
        
        # 1. Calc Live Stats
        live_trades_df = pd.DataFrame(live_trades)
        total_live_pnl = live_trades_df['realized_pnl'].sum() if not live_trades_df.empty else 0
        live_win_rate = (live_trades_df['realized_pnl'] > 0).mean() * 100 if not live_trades_df.empty else 0
        live_avg_pnl = live_trades_df['realized_pnl'].mean() if not live_trades_df.empty else 0
        # live_comm = float(live_trades_df['total_commission'].sum()) if 'total_commission' in live_trades_df else 0.0
        # live_swap = float(live_trades_df['total_swap'].sum()) if 'total_swap' in live_trades_df else 0.0
        
        initial_cash = getattr(args, 'cash', 10000)
        live_avg_pnl_pct = (live_avg_pnl / initial_cash) * 100 if initial_cash > 0 else 0
        
        # 2. Calc Backtest Stats
        bt_label = portfolio.wrapper.columns[0]
        bt_trades_df = pd.DataFrame(portfolio[bt_label].trades.records)
        time_index = portfolio[bt_label].wrapper.index
        bt_trades_df['entry_time'] = time_index[bt_trades_df['entry_idx']]
        bt_trades_df['exit_time'] = time_index[bt_trades_df['exit_idx']]
        
        bt_win_rate = (bt_trades_df['pnl'] > 0).mean() * 100 if not bt_trades_df.empty else 0
        bt_avg_pnl = bt_trades_df['pnl'].mean() if not bt_trades_df.empty else 0
        bt_total_pnl = bt_trades_df['pnl'].sum()
        bt_avg_pnl_pct = (bt_avg_pnl / initial_cash) * 100 if initial_cash > 0 else 0
        
        # 3. Prepare Equity Curves
        initial_cash = getattr(args, 'cash', 10000)
        equity_steps = [(pd.Timestamp(portfolio[bt_label].wrapper.index[0]).tz_localize(None), initial_cash)]
        
        if not live_trades_df.empty:
            live_trades_df = live_trades_df.sort_values('exit_time')
            live_trades_df['cum_net_pnl'] = live_trades_df['net_pnl'].cumsum() if 'net_pnl' in live_trades_df else live_trades_df['realized_pnl'].cumsum()
            for _, row in live_trades_df.iterrows():
                t = pd.Timestamp(row['exit_time']).tz_localize(None)
                equity_steps.append((t, initial_cash + row['cum_net_pnl']))
        
        equity_steps.sort(key=lambda x: x[0])
        times, values = zip(*equity_steps)
        live_equity = pd.Series(values, index=times).astype(float)
        
        # Ensure bt equity index is localized for report
        bt_equity = portfolio[bt_label].value()
        if not hasattr(bt_equity.index, 'tz') or bt_equity.index.tz is None:
            bt_equity.index = bt_equity.index.tz_localize('UTC')
        bt_equity.index = bt_equity.index.tz_convert(args.timezone)

        # Calculate MDD
        live_mdd = abs((live_equity / live_equity.cummax() - 1).min() * 100) if not live_equity.empty else 0.0
        bt_mdd = abs((bt_equity / bt_equity.cummax() - 1).min() * 100) if not bt_equity.empty else 0.0

        # 4. Comparative Stats
        matched = [r for r in comparison_results if r['matched']]
        avg_slip = np.mean([r['slippage_points'] for r in matched]) if matched else 0
        
        total_live_pnl_pct = (total_live_pnl / initial_cash) * 100 if initial_cash > 0 else 0
        bt_total_pnl_pct = (bt_total_pnl / initial_cash) * 100 if initial_cash > 0 else 0

        comparison_stats = {
            "Total PnL (%)": {"live": total_live_pnl_pct, "bt": bt_total_pnl_pct},
            "Max Drawdown (%)": {"live": live_mdd, "bt": bt_mdd},
            "Win Rate (%)": {"live": live_win_rate, "bt": bt_win_rate},
            "Avg PnL/Trade (%)": {"live": live_avg_pnl_pct, "bt": bt_avg_pnl_pct},
            # "Avg Slippage": {"live": avg_slip, "bt": 0.0},
            # "Commission": {"live": live_comm, "bt": 0.0},
            # "Swap (RollOver)": {"live": live_swap, "bt": 0.0},
            "Resolution": {"live": resolution, "bt": resolution},
            "Timezone": {"live": args.timezone, "bt": args.timezone},
        }

        # 5. Load Market Data for Chart
        parts = bt_label.split('_')
        epic = parts[1] if len(parts) > 1 else args.epics
        res  = parts[2] if len(parts) > 2 else 'DAY'
        df_main = engine.load_data(epic, res, start=args.from_date, end=args.to_date, tz=args.timezone)

        # 6. Generate Report
        print(f"[INFO] Generating dual-pane audit report...")
        reports_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reports")
        os.makedirs(reports_dir, exist_ok=True)
        
        from_str = args.from_date.replace("-", "") if args.from_date else "Start"
        to_str = args.to_date.replace("-", "") if args.to_date else "End"
        
        report_path = os.path.join(reports_dir, f"Audit_{args.strategy}_{args.epics}_{from_str}_{to_str}.html")
        
        report_data = AuditReportDataDTO(
            df=df_main,
            live_trades_df=live_trades_df,
            bt_trades_df=bt_trades_df,
            live_equity=live_equity,
            bt_equity=bt_equity,
            comparison_stats=comparison_stats,
            report_file=report_path,
            strategy_name=f"Audit: {args.strategy} on {args.epics} ({resolution})",
            target_tz=args.timezone
        )
        generate_audit_report(report_data)
        print(f"[SUCCESS] Audit report saved to {report_path}")
