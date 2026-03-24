def get_summary_header(pnl_class, total_pnl_str, mdd_str, total_trades, pf_str, stats, multi_stats, start_time_str, end_time_str):
    if multi_stats:
        # If multi-stats exists, we might show a minimal header or just the period
        return f'''
            <div id="returns-header">
                <div class="summary-period">
                    Backtest Period: {start_time_str} ~ {end_time_str}
                </div>
            </div>
        '''
    
    return f'''
        <div id="returns-header">
            <div class="metric-box"><div class="m-title">Total P&amp;L (%)</div><div class="m-value {pnl_class}">{total_pnl_str}</div></div>
            <div class="metric-box"><div class="m-title">Max Drawdown (%)</div><div class="m-value loss">{mdd_str}</div></div>
            <div class="metric-box"><div class="m-title">Total Trades</div><div class="m-value">{total_trades}</div></div>
            <div class="metric-box"><div class="m-title">Profit Factor</div><div class="m-value">{pf_str}</div></div>
            <div class="metric-box"><div class="m-title">Avg. Win</div><div class="m-value win">{stats.get('Avg Win Trade', 'N/A')}</div></div>
            <div class="metric-box"><div class="m-title">Avg. Loss</div><div class="m-value loss">{stats.get('Avg Loss Trade', 'N/A')}</div></div>
            <div class="metric-box"><div class="m-title">Sharpe Ratio</div><div class="m-value">{stats.get('Sharpe Ratio', 'N/A')}</div></div>
            
            <div class="summary-period">
                Backtest Period: {start_time_str} ~ {end_time_str}
            </div>
        </div>
    '''

def get_multi_stats_table(multi_stats):
    if not multi_stats:
        return ""
    
    rows = []
    for s in multi_stats:
        pnl = float(s.get('Total Return [%]', 0))
        pnl_class = 'win' if pnl > 0 else 'loss'
        rows.append(f"""
            <tr>
                <td class="label-cell">{s['label']}</td>
                <td class="{pnl_class}">{pnl:.2f}%</td>
                <td class="loss">{float(s.get('Max Drawdown [%]', 0)):.2f}%</td>
                <td>{int(float(s.get('Total Trades', 0)))}</td>
                <td>{float(s.get('Profit Factor', 0)):.3f}</td>
                <td>{float(s.get('Win Rate [%]', 0)):.1f}%</td>
                <td class="win">{s.get('Avg Win Trade', 'N/A')}</td>
                <td class="loss">{s.get('Avg Loss Trade', 'N/A')}</td>
                <td class="win">{s.get('Best Trade', 'N/A')}</td>
                <td class="loss">{s.get('Worst Trade', 'N/A')}</td>
                <td>{s.get('Sharpe Ratio', 'N/A')}</td>
            </tr>
        """)
    
    return f'''
        <div id="multi-stats-container">
            <table class="header-table">
                <thead>
                    <tr>
                        <th>Strategy / Portfolio</th>
                        <th>Total Return (%)</th>
                        <th>Max Drawdown (%)</th>
                        <th>Total Trades</th>
                        <th>Profit Factor</th>
                        <th>Win Rate (%)</th>
                        <th>Avg. Win</th>
                        <th>Avg. Loss</th>
                        <th>Best</th>
                        <th>Worst</th>
                        <th>Sharpe Ratio</th>
                    </tr>
                </thead>
                <tbody>
                    {" ".join(rows)}
                </tbody>
            </table>
        </div>
    '''

def get_monte_carlo_panel(mc_results):
    if not mc_results:
        return ""
    
    ruin_class = 'loss' if mc_results.ruin_probability > 10 else ('win' if mc_results.ruin_probability < 2 else '')
    
    return f'''
        <div id="mc-container">
            <div class="mc-section-title">&#9684; Monte Carlo Simulation &nbsp;<span class="mc-subtitle">({mc_results.n_simulations} runs &middot; {mc_results.n_trades} trades shuffled)</span></div>
            <div class="mc-hist-item mc-hist-item-mb10">
                <div class="mc-hist-label">Max Drawdown Distribution — How bad could it get?</div>
                <canvas id="mc-mdd-canvas" width="580" height="110"></canvas>
            </div>
            <table class="mc-pct-table">
                <thead>
                    <tr>
                        <th></th>
                        <th>Best 5%</th>
                        <th>P25</th>
                        <th>Median</th>
                        <th>P75</th>
                        <th>Worst 5%</th>
                        <th>Historical &#9670;</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Max Drawdown</td>
                        <td class="win">{mc_results.mdd_p5:.1f}%</td>
                        <td>{mc_results.mdd_p25:.1f}%</td>
                        <td>{mc_results.mdd_p50:.1f}%</td>
                        <td>{mc_results.mdd_p75:.1f}%</td>
                        <td class="loss">{mc_results.mdd_p95:.1f}%</td>
                        <td class="actual-col">{mc_results.actual_mdd_pct:.1f}%</td>
                    </tr>
                </tbody>
            </table>
            <div class="mc-ruin">
                &#9888;&nbsp;Ruin Probability&nbsp;<span class="mc-ruin-desc">(MDD &gt; {mc_results.ruin_threshold_pct:.0f}%)</span>:&nbsp;
                <span class="mc-ruin-val {ruin_class}">{mc_results.ruin_probability:.1f}%</span>
                &nbsp;<span class="mc-ruin-subtext">({mc_results.ruin_probability/100*mc_results.n_simulations:.0f} of {mc_results.n_simulations} simulations exceeded this threshold)</span>
            </div>
        </div>
    '''

def get_trades_table():
    return '''
        <div id="trades-container">
            <div class="table-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th data-sort="strategy">Strategy<span class="sort-icon"></span></th>
                            <th data-sort="entry_ts">Entry Time<span class="sort-icon"></span></th>
                            <th data-sort="exit_ts">Exit Time<span class="sort-icon"></span></th>
                            <th data-sort="entry_price">Entry<span class="sort-icon"></span></th>
                            <th data-sort="exit_price">Exit<span class="sort-icon"></span></th>
                            <th data-sort="pnl">PnL ($)<span class="sort-icon"></span></th>
                            <th data-sort="return_pct">Ret (%)<span class="sort-icon"></span></th>
                        </tr>
                    </thead>
                    <tbody id="trades-tbody"></tbody>
                </table>
            </div>
        </div>
    '''
