import json
import numpy as np
import math
import os
import decimal
import pandas as pd
from .report_components import get_summary_header, get_multi_stats_table, get_monte_carlo_panel, get_trades_table
from .data_adapters import clean_json_data, prepare_chart_data
from core.dtos import ReportDataDTO, AuditReportDataDTO

def _get_template_file(filename):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, 'templates', filename)
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def get_report_css():
    return _get_template_file('report.css')

def get_report_js(target_tz='Asia/Taipei'):
    try:
        offset_sec = int(pd.Timestamp.now(tz='UTC').tz_convert(target_tz).utcoffset().total_seconds())
    except Exception:
        offset_sec = 28800
    js_content = _get_template_file('report.js')
    return f"const TZ_OFFSET = {offset_sec};\n{js_content}"

def generate_tv_chart(report_data: ReportDataDTO):
    if report_data.stats is None: report_data.stats = {}
    if report_data.multi_stats is None: report_data.multi_stats = []
    if report_data.multi_returns is None: report_data.multi_returns = []
    if report_data.indicators is None: report_data.indicators = []
    
    os.makedirs(os.path.dirname(report_data.report_file), exist_ok=True)
    
    # 1. Data Preparation
    chart_data = prepare_chart_data(report_data.df, report_data.trades_df, report_data.stop_lines, report_data.portfolio_values)

    # 2. UI Helper Formatting
    total_pnl_val = float(report_data.stats.get('Total Return [%]', 0))
    pnl_class = 'win' if total_pnl_val > 0 else ('loss' if total_pnl_val < 0 else '')
    total_pnl_str = f"{'+' if total_pnl_val > 0 else ''}{total_pnl_val:.2f}%"
    mdd_str = f"{float(report_data.stats.get('Max Drawdown [%]', 0)):.2f}%"
    total_trades = int(float(report_data.stats.get('Total Trades', 0)))
    pf_str = f"{float(report_data.stats.get('Profit Factor', 0)):.3f}"
    
    stats_rows = "".join([f"<tr><td>{k}</td><td>{f'{v:.4f}' if isinstance(v, float) else v}</td></tr>" for k, v in report_data.stats.items()])
    start_time, end_time = report_data.df.index[0].strftime('%Y-%m-%d %H:%M:%S'), report_data.df.index[-1].strftime('%Y-%m-%d %H:%M:%S')

    # 3. Assemble HTML Content
    css = get_report_css()
    js_template = get_report_js(target_tz=report_data.target_tz)
    
    # Inject Data into JS
    js_content = js_template.replace("JSON_OHLC_DATA", json.dumps(chart_data.ohlc_data)) \
                           .replace("JSON_STOP_SEGMENTS", json.dumps(chart_data.stop_segments)) \
                           .replace("JSON_TRADE_LINES", json.dumps(chart_data.trade_lines)) \
                           .replace("JSON_MARKERS_DATA", json.dumps(chart_data.markers)) \
                           .replace("JSON_INDICATORS_DATA", json.dumps(clean_json_data(report_data.indicators))) \
                           .replace("JSON_BENCHMARK_DATA", json.dumps(chart_data.benchmark_data)) \
                           .replace("JSON_RETURNS_DATA", json.dumps(chart_data.returns_data)) \
                           .replace("JSON_MULTI_RETURNS", json.dumps(clean_json_data(report_data.multi_returns))) \
                           .replace("JSON_TRADES_JSON", json.dumps(chart_data.trades_json)) \
                           .replace("JSON_MC_DATA", json.dumps(clean_json_data({'final_returns': report_data.mc_results.final_returns, 'max_drawdowns': report_data.mc_results.max_drawdowns, 'actual_return': report_data.mc_results.actual_return_pct, 'actual_mdd': report_data.mc_results.actual_mdd_pct}) if report_data.mc_results else None))

    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1.0"/>
    <title>{report_data.strategy_name} Dashboard</title>
    <script src="https://unpkg.com/lightweight-charts@4.2.3/dist/lightweight-charts.standalone.production.js"></script>
    <style>{css}</style>
</head>
<body>
    <div id="top-pane">
        <div id="chart-main"><div class="overlay-title">{report_data.strategy_name}</div><div class="overlay-subtitle">Red dashed line is the trailing stop limit</div></div>
        <div id="chart-indicators"></div><div id="error-log"></div>
    </div>
    <div id="h-splitter"></div>
    <div id="bottom-pane">
        <div id="returns-container">
            {get_summary_header(pnl_class, total_pnl_str, mdd_str, total_trades, pf_str, report_data.stats, report_data.multi_stats, start_time, end_time)}
            {get_multi_stats_table(report_data.multi_stats)}
            <div id="returns-chart">
                <div class="overlay-title returns-chart-title">
                    Cumulative Returns (%) &nbsp;&nbsp;
                    <span class="color-consolidated">■ Consolidated</span> &nbsp;&nbsp;
                    <span class="color-individual">■ Individual Strategies</span> &nbsp;&nbsp;
                    <span class="color-benchmark">■ Benchmark</span>
                </div>
            </div>
            <div id="returns-stats"><table><tbody>{stats_rows}</tbody></table></div>
            {get_monte_carlo_panel(report_data.mc_results)}
        </div>
        <div id="v-splitter"></div>
        {get_trades_table()}
    </div>
    <script>{js_content}</script>
</body>
</html>
    """
    
    with open(report_data.report_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    return report_data.report_file

def generate_audit_report(report_data: AuditReportDataDTO):
    """Generates a specialized Audit report with two synchronized charts and a comparison table."""
    os.makedirs(os.path.dirname(report_data.report_file), exist_ok=True)
    
    df = report_data.df
    live_trades_df = report_data.live_trades_df
    bt_trades_df = report_data.bt_trades_df
    live_equity = report_data.live_equity
    bt_equity = report_data.bt_equity
    comparison_stats = report_data.comparison_stats
    target_tz = report_data.target_tz
    strategy_name = report_data.strategy_name
    report_file = report_data.report_file
    
    # 1. Prepare Chart Data (Shared OHLC)
    # Ensure index is localized to target_tz for consistent display
    if not hasattr(df.index, 'tz') or df.index.tz is None:
        df.index = df.index.tz_localize('UTC')
    df.index = df.index.tz_convert(target_tz)
    
    df = df.sort_index()
    bar_times = df.index.values.astype('datetime64[ns]').astype('datetime64[s]').astype(int)
    
    def snap_time(t):
        if not hasattr(t, 'tzinfo') or t.tzinfo is None:
            t = pd.Timestamp(t).tz_localize('UTC')
        t_target = t.tz_convert(target_tz)
        ts = int(t_target.timestamp())
        # Find the bar that started at or before this timestamp
        idx = np.searchsorted(bar_times, ts, side='right') - 1
        if idx < 0: return bar_times[0]
        return int(bar_times[idx])

    ohlc_data = [{'time': int(row.Index.timestamp()), 'open': row.open, 'high': row.high, 'low': row.low, 'close': row.close} for row in df.itertuples()]
    
    # 2. Prepare Live Markers/Equity
    live_markers = []
    live_lines = []
    if not live_trades_df.empty:
        for _, row in live_trades_df.iterrows():
            ets = snap_time(row['entry_time'])
            xts = snap_time(row['exit_time'])
            
            # Use distinct markers for Buy/Sell
            color_buy = '#26a69a'
            color_sell = '#ef5350'
            
            if row['direction'] == 'BUY':
                live_markers.append({'time': ets, 'position': 'belowBar', 'color': color_buy, 'shape': 'arrowUp', 'text': f"Buy @ {row['entry_price']}"})
                live_markers.append({'time': xts, 'position': 'aboveBar', 'color': color_sell, 'shape': 'arrowDown', 'text': f"Exit @ {row['exit_price']}"})
            else:
                live_markers.append({'time': ets, 'position': 'aboveBar', 'color': color_sell, 'shape': 'arrowDown', 'text': f"Sell @ {row['entry_price']}"})
                live_markers.append({'time': xts, 'position': 'belowBar', 'color': color_buy, 'shape': 'arrowUp', 'text': f"Exit @ {row['exit_price']}"})
            
            # Don't draw lines if entry/exit are the same bar (avoids visual jitter)
            if ets != xts:
               live_lines.append([{'time': ets, 'value': float(row['entry_price'])}, {'time': xts, 'value': float(row['exit_price'])}])
    
    live_returns = []
    if not live_equity.empty:
        # Ensure live_equity index is localized to target_tz for comparison
        if not hasattr(live_equity.index, 'tz') or live_equity.index.tz is None:
            live_equity.index = live_equity.index.tz_localize('UTC')
        live_equity.index = live_equity.index.tz_convert(target_tz)
        
        # Reindex to full OHLC range and forward-fill to create a continuous step curve
        full_live = live_equity.reindex(df.index, method='ffill').fillna(live_equity.iloc[0])
        init_v = live_equity.iloc[0]
        live_returns = [{'time': int(t.timestamp()), 'value': round(((v - init_v)/init_v)*100, 4)} for t, v in full_live.items()]

    # 3. Prepare Backtest Markers/Equity
    bt_markers = []
    bt_lines = []
    if not bt_trades_df.empty:
        # VectorBT records usually have 'direction' where 0=Long, 1=Short
        # and 'entry_price', 'exit_price', 'pnl'
        for _, row in bt_trades_df.iterrows():
            ets = snap_time(row['entry_time'])
            xts = snap_time(row['exit_time'])
            
            # Map direction (0=Long/Buy, 1=Short/Sell)
            is_buy = True
            if 'direction' in row:
                is_buy = (row['direction'] == 0)
            elif 'side' in row:
                is_buy = (row['side'] > 0)

            if is_buy:
                bt_markers.append({'time': ets, 'position': 'belowBar', 'color': '#2196F3', 'shape': 'arrowUp', 'text': f"BT Buy"})
                bt_markers.append({'time': xts, 'position': 'aboveBar', 'color': '#9C27B0', 'shape': 'arrowDown', 'text': f"BT Exit"})
            else:
                bt_markers.append({'time': ets, 'position': 'aboveBar', 'color': '#9C27B0', 'shape': 'arrowDown', 'text': f"BT Sell"})
                bt_markers.append({'time': xts, 'position': 'belowBar', 'color': '#2196F3', 'shape': 'arrowUp', 'text': f"BT Exit"})

            if ets != xts:
                bt_lines.append([{'time': ets, 'value': float(row['entry_price'])}, {'time': xts, 'value': float(row['exit_price'])}])
    
    bt_returns = []
    if not bt_equity.empty:
        # Reindex backtest equity to match OHLC bars
        full_bt = bt_equity.reindex(df.index, method='ffill').fillna(bt_equity.iloc[0])
        init_v = bt_equity.iloc[0]
        bt_returns = [{'time': int(t.timestamp()), 'value': round(((v - init_v)/init_v)*100, 4)} for t, v in full_bt.items()]

    # 4. Generate HTML
    css = get_report_css()
    
    # Rows for Comparison Table
    def fmt_val(v, is_pct=False):
        if v is None: return "—"
        if isinstance(v, (int, float, decimal.Decimal)):
            fv = float(v)
            if math.isnan(fv): return "0.00"
            if round(fv, 2) == 0: fv = 0.0
            return f"{fv:,.2f}%" if is_pct else f"${fv:,.2f}"
        return str(v)

    rows = []
    for metric, vals in comparison_stats.items():
        lv, bv = vals['live'], vals['bt']
        delta_str = ""
        warn_icon = ""
        
        # Safe numeric values for calculation
        ln = float(lv) if isinstance(lv, (int, float, decimal.Decimal)) and not math.isnan(float(lv)) else 0
        bn = float(bv) if isinstance(bv, (int, float, decimal.Decimal)) and not math.isnan(float(bv)) else 0
        
        d = ln - bn
        if round(d, 2) == 0: d = 0.0 # Normalize small delta to +0.00
        delta_str = f"{d:+,.2f}%" if "%" in metric or "Rate" in metric else f"{d:+,.2f}"
        
        if metric in ["Resolution", "Timezone"]:
            delta_str = "—"
            c = ""
        else:
            if "Drawdown" in metric or "Slippage" in metric or "Commission" in metric:
                c = 'win' if d <= 0 else 'loss'
            else:
                c = 'win' if d >= 0 else 'loss'
        
        rows.append(f"""
            <tr>
                <td>{metric}</td>
                <td>{fmt_val(lv, "%" in metric or "Rate" in metric)}</td>
                <td>{fmt_val(bv, "%" in metric or "Rate" in metric)}</td>
                <td class="{c}">{delta_str}</td>
            </tr>
        """)

    html = f"""
<!DOCTYPE html>
<html class="audit-html">
<head>
    <meta charset="utf-8"/><title>Audit Report: {strategy_name}</title>
    <script src="https://unpkg.com/lightweight-charts@4.2.3/dist/lightweight-charts.standalone.production.js"></script>
    <style>{css}</style>
</head>
<body class="audit-body">
    <div class="audit-layout">
        <div class="section-header">
            <span>LIVE TRADING ANALYSIS</span>
            <span class="live-tag">REAL MONEY / DEMO LIVE</span>
        </div>
        <div class="chart-section">
            <div id="chart-live" class="chart-container"></div>
            <div id="equity-live" class="equity-container"></div>
        </div>

        <div class="comparison-section">
            <div class="mc-section-title">Comparative Performance Summary</div>
            <table class="comp-table">
                <thead><tr><th>Metrics</th><th>LIVE</th><th>BACKTEST</th><th>DELTA</th></tr></thead>
                <tbody>{"".join(rows)}</tbody>
            </table>
        </div>

        <div class="section-header">
            <span>BACKTEST ENGINE RESULTS</span>
            <span class="bt-tag">SIMULATION</span>
        </div>
        <div class="chart-section chart-section-no-border">
            <div id="chart-bt" class="chart-container"></div>
            <div id="equity-bt" class="equity-container"></div>
        </div>
    </div>

    <script>
    const ohlc = {json.dumps(clean_json_data(ohlc_data))};
    const chartOpts = {{
        layout: {{ background: {{ type: 'solid', color: '#131722' }}, textColor: '#d1d4dc' }},
        grid: {{ vertLines: {{ color: '#2B2B43', style: 1 }}, horzLines: {{ color: '#2B2B43', style: 1 }} }},
        timeScale: {{ timeVisible: true, borderColor: '#485c7b', secondsVisible: false }},
        rightPriceScale: {{ borderColor: '#485c7b', autoScale: true }},
        crosshair: {{ mode: 0 }}
    }};
    const eqOpts = {{
        layout: {{ background: {{ type: 'solid', color: '#131722' }}, textColor: '#787B86' }},
        grid: {{ vertLines: {{ visible: false }}, horzLines: {{ color: '#2B2B43' }} }},
        timeScale: {{ visible: false }},
        rightPriceScale: {{ 
            borderColor: '#485c7b',
            mode: 0, // Normal
            autoScale: true
        }},
        localization: {{
            priceFormatter: (p) => p.toFixed(2) + '%'
        }}
    }};

    function setupChart(mainId, eqId, markers, lines, returns, color) {{
        const c = LightweightCharts.createChart(document.getElementById(mainId), chartOpts);
        const s = c.addCandlestickSeries({{ upColor: '#26a69a', downColor: '#ef5350', borderVisible: false, wickUpColor: '#26a69a', wickDownColor: '#ef5350' }});
        s.setData(ohlc);
        
        // Group markers by time to avoid overlap jitter
        s.setMarkers(markers);
        
        // Draw trade connection lines
        lines.forEach(l => {{
            const ls = c.addLineSeries({{ 
                color: color + 'CC', 
                lineWidth: 2, 
                lineStyle: 1, // Dotted
                lastValueVisible: false, 
                priceLineVisible: false,
                crosshairMarkerVisible: false
            }});
            ls.setData(l);
        }});

        const ec = LightweightCharts.createChart(document.getElementById(eqId), eqOpts);
        const es = ec.addAreaSeries({{ lineColor: color, topColor: color + '40', bottomColor: color + '05', lineWidth: 2 }});
        es.setData(returns);
        
        return {{ main: c, equity: ec, ohlcSeries: s }};
    }}

    const live = setupChart('chart-live', 'equity-live', {json.dumps(clean_json_data(live_markers))}, {json.dumps(clean_json_data(live_lines))}, {json.dumps(clean_json_data(live_returns))}, '#4CAF50');
    const bt = setupChart('chart-bt', 'equity-bt', {json.dumps(clean_json_data(bt_markers))}, {json.dumps(clean_json_data(bt_lines))}, {json.dumps(clean_json_data(bt_returns))}, '#2196F3');

    // Sync TimeScales
    const charts = [live.main, bt.main];
    const equities = [live.equity, bt.equity];
    
    let isSyncing = false;
    charts.forEach((src, i) => {{
        src.timeScale().subscribeVisibleLogicalRangeChange(range => {{
            if (isSyncing) return;
            isSyncing = true;
            charts.forEach((dst, j) => {{ if(i!==j) dst.timeScale().setVisibleLogicalRange(range); }});
            equities.forEach(e => e.timeScale().setVisibleLogicalRange(range));
            isSyncing = false;
        }});
    }});
    </script>
</body>
</html>
    """
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(html)
    return report_file
