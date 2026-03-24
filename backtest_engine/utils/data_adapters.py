import math
import decimal
import pandas as pd
import numpy as np
from datetime import datetime
from core.dtos import ChartOutputDataDTO

def clean_json_data(obj):
    """Recursively replace NaN/Inf/Decimal/Timestamp for JSON compatibility."""
    if isinstance(obj, dict):
        return {k: clean_json_data(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_json_data(x) for x in obj]
    elif isinstance(obj, (pd.Timestamp, datetime)):
        return int(obj.timestamp())
    elif isinstance(obj, decimal.Decimal):
        return float(obj)
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
    return obj

def prepare_chart_data(df, trades_df, stop_lines, portfolio_values=None) -> ChartOutputDataDTO:
    """
    Transforms Pandas DataFrames into simple Python dicts/lists suitable for JSON serialization
    and Lightweight Charts rendering.
    """
    # Ensure index is localized (if naive, assume it's UTC)
    if not hasattr(df.index, 'tz') or df.index.tz is None:
        df.index = df.index.tz_localize('UTC')
    
    ohlc_data = [{'time': int(row.Index.timestamp()), 'open': row.open, 'high': row.high, 'low': row.low, 'close': row.close} for row in df.itertuples()]
    
    benchmark_data = []
    if not df.empty and 'close' in df.columns:
        valid_closes = df['close'].dropna()
        if not valid_closes.empty:
            initial_close = float(valid_closes.iloc[0])
            benchmark_data = [{'time': int(row.Index.timestamp()), 'value': round(((float(row.close) - initial_close) / initial_close) * 100, 2) if not math.isnan(float(row.close)) else 0.0} for row in df.itertuples()]

    returns_data = []
    if portfolio_values is not None and not portfolio_values.empty and not trades_df.empty:
        initial_value = float(portfolio_values.dropna().iloc[0])
        raw_rets = {int(trades_df.iloc[0]['entry_time'].timestamp()): 0.0}
        for _, row in trades_df.iterrows():
            exit_ts = int(row['exit_time'].timestamp())
            val_at_exit = float(portfolio_values.get(row['exit_time'], row['exit_price']))
            raw_rets[exit_ts] = round(((val_at_exit - initial_value) / initial_value) * 100, 2) if not math.isnan(val_at_exit) else 0.0
        returns_data = [{'time': t, 'value': raw_rets[t]} for t in sorted(raw_rets.keys())]

    stop_segments = []
    current_segment = []
    for i, val in enumerate(stop_lines):
        if not np.isnan(val):
            current_segment.append({'time': int(df.index[i].timestamp()), 'value': float(val)})
        elif current_segment:
            stop_segments.append(current_segment)
            current_segment = []
    if current_segment: stop_segments.append(current_segment)
            
    markers, trade_lines, trades_json = [], [], []
    if not trades_df.empty:
        for _, row in trades_df.iterrows():
            ets, xts = int(row['entry_time'].timestamp()), int(row['exit_time'].timestamp())
            markers.append({'time': ets, 'position': 'belowBar', 'color': '#2962FF', 'shape': 'arrowUp', 'text': f"Long @ {row['entry_price']:.1f}"})
            markers.append({'time': xts, 'position': 'aboveBar', 'color': '#E91E63', 'shape': 'arrowDown', 'text': f"Exit @ {row['exit_price']:.1f}\nPnL: {row['pnl']:.1f}"})
            trade_lines.append([{'time': ets, 'value': float(row['entry_price'])}, {'time': xts, 'value': float(row['exit_price'])}])
            trades_json.append({
                'strategy': str(row.get('strategy', '')).split('_')[0],
                'entry_time': str(row['entry_time'])[:16], 'exit_time': str(row['exit_time'])[:16],
                'entry_price': round(float(row['entry_price']), 2), 'exit_price': round(float(row['exit_price']), 2),
                'pnl': round(float(row['pnl']), 2), 'return_pct': round(float(row['return']) * 100, 2),
                'entry_ts': ets, 'exit_ts': xts, 'is_win': row['pnl'] > 0
            })
    markers.sort(key=lambda x: x['time'])

    return ChartOutputDataDTO(
        ohlc_data=clean_json_data(ohlc_data),
        benchmark_data=clean_json_data(benchmark_data),
        returns_data=clean_json_data(returns_data),
        stop_segments=clean_json_data(stop_segments),
        markers=clean_json_data(markers),
        trade_lines=clean_json_data(trade_lines),
        trades_json=clean_json_data(trades_json)
    )
