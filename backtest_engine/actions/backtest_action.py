import os
import pandas as pd
import numpy as np
import vectorbt as vbt
import math
from actions.base import BaseAction
from core.metrics import calculate_advanced_metrics
from utils.tv_chart import generate_tv_chart
from analysis.monte_carlo import run_monte_carlo
from core.dtos import BacktestConfigDTO, ReportDataDTO

class BacktestAction(BaseAction):
    def execute(self, args, engine):
        strategy_names = [s.strip() for s in args.strategy.split(',')]
        epics = [e.strip() for e in args.epics.split(',')]
        resolutions = [r.strip() for r in args.resolutions.split(',')]
        params = engine.parse_params(args.params)

        print(f"\nRunning Multi-Strategy Backtest: {strategy_names}")
        print(f"Assets: {epics}, Resolutions: {resolutions}")
        if args.from_date or args.to_date:
            print(f"Time Range: {args.from_date or 'Start'} to {args.to_date or 'End'}")
        
        config = BacktestConfigDTO(
            epics=epics,
            resolutions=resolutions,
            params=params,
            use_ml=args.use_ml,
            start=args.from_date,
            end=args.to_date,
            sizing_type=args.sizing_type,
            position_size=args.position_size,
            tz=args.timezone
        )
        
        portfolio, stop_lines = engine.run_backtest(config)
        
        if not portfolio:
            print("[ERROR] Portfolio is empty. No trades occurred.")
            return

        # 1. Correlation Analysis
        if len(portfolio.wrapper.columns) > 1:
            print("\n" + "="*50)
            print("STRATEGY CORRELATION (Daily Returns)")
            print("="*50)
            print(portfolio.returns().corr())

        # 2. Consolidate Trades
        all_trades_list = []
        for label in portfolio.wrapper.columns:
            t_recs = portfolio[label].trades.records
            if len(t_recs) > 0:
                t_df = pd.DataFrame(t_recs)
                time_index = portfolio[label].wrapper.index
                t_df['entry_time'] = time_index[t_df['entry_idx']]
                t_df['exit_time'] = time_index[t_df['exit_idx']]
                t_df['duration'] = t_df['exit_time'] - t_df['entry_time']
                t_df['strategy'] = label
                all_trades_list.append(t_df)
        
        consolidated_trades = pd.concat(all_trades_list) if all_trades_list else pd.DataFrame()

        # 3. Calculate Metrics
        m = calculate_advanced_metrics(portfolio, consolidated_trades, args.cash)

        print("\n" + "="*50)
        print("CONSOLIDATED PERFORMANCE SUMMARY (Total Portfolio)")
        print("="*50)
        print(f"Total Return [%]:         {m.total_return_pct:.2f}%")
        print(f"Max Drawdown [%]:         {m.mdd:.2f}%")
        print(f"Sharpe Ratio:             {m.sharpe:.2f}")
        print(f"Total Trades:             {m.total_trades}")
        print(f"Win Rate [%]:             {m.win_rate:.2f}%")
        print(f"Profit Factor:            {m.profit_factor:.3f}")
        print(f"Avg Win Trade:            ${m.avg_win:.2f} ({m.avg_win_pct:.2f}%)")
        print(f"Avg Loss Trade:           ${m.avg_loss:.2f} ({m.avg_loss_pct:.2f}%)")
        print(f"Best Trade:               ${m.best_trade:.2f}")
        print(f"Worst Trade:              ${m.worst_trade:.2f}")
        print(f"Expectancy:               ${m.expectancy:.2f}")

        # 4. Monte Carlo
        mc_results = None
        if args.monte and m.total_trades > 0:
            print("\n" + "="*50)
            print(f"MONTE CARLO SIMULATION ({args.monte_n} runs)")
            print("="*50)
            mc_results = run_monte_carlo(
                trade_pnls=portfolio.trades.records['pnl'],
                initial_cash=args.cash,
                n_simulations=args.monte_n,
                ruin_threshold_pct=args.ruin_pct,
            )
            mc_results.actual_return_pct = round(m.total_return_pct, 2)
            mc_results.actual_mdd_pct    = round(float(m.mdd), 2)
            d = mc_results
            print(f"  Max Drawdown:  P5={d.mdd_p5:.1f}%  P25={d.mdd_p25:.1f}%  "
                  f"Median={d.mdd_p50:.1f}%  P75={d.mdd_p75:.1f}%  P95={d.mdd_p95:.1f}%")
            print(f"  Ruin Prob (MDD>{args.ruin_pct:.0f}%): {mc_results.ruin_probability:.1f}%")

        # 5. Generate Report
        self._generate_report(args, engine, portfolio, consolidated_trades, m, mc_results, params)

    def _generate_report(self, args, engine, portfolio, consolidated_trades, m, mc_results, params):
        reports_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reports")
        os.makedirs(reports_dir, exist_ok=True)
        from_str = args.from_date.replace("-", "") if args.from_date else "Start"
        to_str = args.to_date.replace("-", "") if args.to_date else "End"
        suffix = f"{args.epics.replace(',','-')}_{args.resolutions.replace(',','-')}_{from_str}_{to_str}"
        
        print(f"\n--- Generating Consolidated Report ---")
        first_label = portfolio.wrapper.columns[0]
        # Label format: {strategy}_{epic}_{res}
        parts = first_label.split('_')
        first_epic = parts[1]
        first_res = "_".join(parts[2:]) # Rejoin all remaining parts to get full resolution (e.g. MINUTE_5)
        df_main = engine.load_data(first_epic, first_res, start=args.from_date, end=args.to_date, tz=args.timezone)
        
        if not consolidated_trades.empty:
            consolidated_trades = consolidated_trades.sort_values('entry_time')
            dummy_stops = np.full(len(df_main), np.nan)
            
            html_file = os.path.join(reports_dir, f"Backtest_{args.strategy.replace(',','_')}_{suffix}.html")
            csv_file = os.path.join(reports_dir, f"Trades_{args.strategy.replace(',','_')}_{suffix}.csv")
            
            consolidated_trades[['strategy', 'exit_time', 'entry_time', 'entry_price', 'exit_price', 'pnl', 'return', 'duration']].to_csv(csv_file, index=False)
            
            multi_stats = []
            total_stats = {
                'label': 'Total Portfolio',
                'Total Return [%]': m.total_return_pct,
                'Max Drawdown [%]': m.mdd,
                'Total Trades': m.total_trades,
                'Win Rate [%]': m.win_rate,
                'Profit Factor': m.profit_factor,
                'Sharpe Ratio': f"{m.sharpe:.2f}",
                'Avg Win Trade': f"${m.avg_win:.2f} ({m.avg_win_pct:.2f}%)",
                'Avg Loss Trade': f"${m.avg_loss:.2f} ({m.avg_loss_pct:.2f}%)",
                'Best Trade': f"${m.best_trade:.2f}",
                'Worst Trade': f"${m.worst_trade:.2f}",
                'Expectancy': f"${m.expectancy:.2f}",
                'Avg Duration': m.avg_duration_str,
                'Initial Cash': f"${args.cash:,.0f}"
            }
            multi_stats.append(total_stats)
            
            # Concisely infer frequency (e.g., HOUR_4 -> 4h, MINUTE_15 -> 15min)
            res_up = first_res.upper()
            num = ''.join(filter(str.isdigit, res_up))
            unit = 'D' if 'DAY' in res_up else ('h' if 'HOUR' in res_up or 'H' in res_up else 'min')
            freq = f"{num}{unit}"
            
            indiv_stats_df = portfolio.stats(agg_func=None, settings=dict(freq=freq))
            if isinstance(indiv_stats_df, pd.Series):
                indiv_stats_df = indiv_stats_df.to_frame()
            elif 'Total Return [%]' not in indiv_stats_df.index:
                indiv_stats_df = indiv_stats_df.T

            multi_returns = []
            for col in portfolio.wrapper.columns:
                pnl_recs = portfolio[col].trades.records['pnl']
                s_avg_win = float(pnl_recs[pnl_recs > 0].mean()) if any(pnl_recs > 0) else 0
                s_avg_loss = float(pnl_recs[pnl_recs < 0].mean()) if any(pnl_recs < 0) else 0
                s_best = float(pnl_recs.max()) if len(pnl_recs) > 0 else 0
                s_worst = float(pnl_recs.min()) if len(pnl_recs) > 0 else 0
                
                s_trades = consolidated_trades[consolidated_trades['strategy'] == col]
                s_avg_dur = s_trades['duration'].mean() if not s_trades.empty else pd.Timedelta(0)
                s_avg_dur_str = str(s_avg_dur).split('.')[0]

                s_stats = indiv_stats_df[col].to_dict()
                s_stats['label'] = str(col).split('_')[0]
                s_stats['Avg Win Trade'] = f"${s_avg_win:.2f}"
                s_stats['Avg Loss Trade'] = f"${s_avg_loss:.2f}"
                s_stats['Best Trade'] = f"${s_best:.2f}"
                s_stats['Worst Trade'] = f"${s_worst:.2f}"
                s_stats['Avg Duration'] = s_avg_dur_str
                s_stats['Initial Cash'] = f"${args.cash:,.0f}"
                s_stats['Sharpe Ratio'] = f"{s_stats.get('Sharpe Ratio', 0):.2f}"
                multi_stats.append(s_stats)

                s_vals = portfolio[col].value()
                initial_v = float(s_vals.iloc[0]) if not s_vals.empty else args.cash
                s_data = [{'time': int(t.timestamp()), 'value': round(((float(v) - initial_v) / initial_v) * 100, 2)} for t, v in s_vals.items()]
                multi_returns.append({'label': col.split('_')[0], 'data': s_data})

            extra_indicators = []
            if "MACD" in args.strategy.upper():
                fast, slow, signal = params.get("FAST", 12), params.get("SLOW", 26), params.get("SIGNAL", 9)
                macd = vbt.MACD.run(df_main['close'], fast_window=fast, slow_window=slow, signal_window=signal)
                macd_data, signal_data, hist_data = [], [], []
                m_list, s_list, h_list = macd.macd.to_numpy(), macd.signal.to_numpy(), (macd.macd - macd.signal).to_numpy()
                idx = macd.macd.index
                for i in range(len(idx)):
                    ts = int(idx[i].timestamp())
                    if not math.isnan(m_list[i]): macd_data.append({'time': ts, 'value': float(m_list[i])})
                    if not math.isnan(s_list[i]): signal_data.append({'time': ts, 'value': float(s_list[i])})
                    if not math.isnan(h_list[i]): hist_data.append({'time': ts, 'value': float(h_list[i])})
                extra_indicators.append({
                    'name': 'MACD', 'type': 'oscillator',
                    'lines': [{'name': 'MACD', 'color': '#2962FF', 'data': macd_data}, {'name': 'Signal', 'color': '#FF6D00', 'data': signal_data}],
                    'histogram': {'name': 'Histogram', 'data': hist_data}
                })

            report_data = ReportDataDTO(
                df=df_main,
                trades_df=consolidated_trades,
                stop_lines=dummy_stops,
                report_file=html_file,
                strategy_name=f"Consolidated ({args.strategy}) {suffix}",
                portfolio_values=m.portfolio_value,
                stats={str(k): str(v) for k, v in total_stats.items()},
                multi_stats=multi_stats,
                multi_returns=multi_returns,
                mc_results=mc_results,
                indicators=extra_indicators,
                target_tz=args.timezone
            )
            generate_tv_chart(report_data)
            print(f"DONE: Consolidated Report: {os.path.abspath(html_file)}")
            print(f"DONE: Trades Log: {os.path.abspath(csv_file)}")
