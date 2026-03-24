import type { Time } from 'lightweight-charts';
import { RESOLUTION_MAP } from './chartConstants';

export const calculatePnL = (trade: any, targetStr: string | number) => {
    const p = typeof targetStr === 'string' ? parseFloat(targetStr) : targetStr;
    if (isNaN(p)) return { pnl: null, pct: null };

    const diff = trade.direction === 'BUY' ? (p - trade.entry_price) : (trade.entry_price - p);
    const pnl = diff * (trade.size || 1);
    const pct = (diff / trade.entry_price) * 100;

    return { pnl, pct };
};

export const formatPnLTitle = (prefix: string, pnl: number | null, pct: number | null) => {
    if (pnl === null) return prefix;
    return `${prefix} ${pnl > 0 ? '+' : ''}${pnl.toFixed(2)} (${pct !== null && pct > 0 ? '+' : ''}${pct?.toFixed(2)}%)`;
};

export const getBinSize = (resolution: string) => RESOLUTION_MAP[resolution] || 60;

export const formatTimeToBin = (timestamp: number, binSize: number): Time => {
    // Standardize to seconds if it's in milliseconds
    const ts = timestamp > 4000000000 ? Math.floor(timestamp / 1000) : timestamp;
    return (ts - (ts % binSize)) as Time;
};

export const formatDisplayTime = (time: number) => {
    const date = new Date(time * 1000);
    return date.toLocaleString('zh-TW', { hour: '2-digit', minute: '2-digit', hour12: false });
};

export const formatFullDisplayTime = (ts: number) => {
    const date = new Date(ts * 1000);
    return date.toLocaleString('zh-TW', {
        hour12: false,
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    }).replace(/\//g, '-');
};
