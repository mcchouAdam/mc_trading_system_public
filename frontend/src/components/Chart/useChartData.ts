import { useState, useEffect, useRef, useCallback } from 'react';
import type { Time, ISeriesApi, IChartApi } from 'lightweight-charts';
import { HubConnectionBuilder, HubConnection, LogLevel } from '@microsoft/signalr';
import { API_BASE_URL } from '../../config';
import { getBinSize, formatTimeToBin } from './chartUtils';
import { HUB_EVENTS } from '../../constants';
import { apiClient } from '../../api/apiClient';

export interface Kline {
    time: Time;
    open: number;
    high: number;
    low: number;
    close: number;
}

interface WsKline {
    epic: string;
    resolution: string;
    time: number;
    open: number;
    high: number;
    low: number;
    close: number;
}

const globalChartCache: Record<string, Kline[]> = {};
const cacheOrder: string[] = [];
const MAX_CACHE_SIZE = 20;

const updateCache = (key: string, data: Kline[]) => {
    if (!globalChartCache[key]) {
        cacheOrder.push(key);
        if (cacheOrder.length > MAX_CACHE_SIZE) {
            const oldestKey = cacheOrder.shift();
            if (oldestKey) delete globalChartCache[oldestKey];
        }
    }
    globalChartCache[key] = data;
};

// ─── Pure Helper: Merge a single WS tick into a Kline array ──────────────────
/**
 * Merges one incoming WebSocket tick into a mutable Kline array.
 * Returns the updated lastBar reference (or null if no merge happened).
 *
 * Rules:
 *  - tick.time > lastBar.time  → append a new bar
 *  - tick.time === lastBar.time → update OHLC of the last bar in-place
 *  - tick.time < lastBar.time  → historical merge into an existing bar (if found)
 */
export const mergeTickIntoData = (
    data: Kline[],
    lastBar: Kline | null,
    tick: WsKline,
    resolution: string
): Kline | null => {
    const binSize = getBinSize(resolution);
    const binnedTime = formatTimeToBin(tick.time, binSize);

    if (!lastBar) {
        const firstBar: Kline = { time: binnedTime, open: tick.open, high: tick.high, low: tick.low, close: tick.close };
        data.push(firstBar);
        return firstBar;
    }

    if (binnedTime > lastBar.time) {
        // New bar started
        const newBar: Kline = { time: binnedTime, open: tick.open, high: tick.high, low: tick.low, close: tick.close };
        data.push(newBar);
        return newBar;
    }

    if (binnedTime === lastBar.time) {
        // Update latest bar in-place
        const updatedBar: Kline = {
            time: lastBar.time,
            open: lastBar.open,
            high: Math.max(lastBar.high, tick.high),
            low: Math.min(lastBar.low, tick.low),
            close: tick.close,
        };
        data[data.length - 1] = updatedBar;
        return updatedBar;
    }

    // Historical tick: merge into existing bar if found
    const existingIdx = data.findIndex(k => k.time === binnedTime);
    if (existingIdx !== -1) {
        const existing = data[existingIdx];
        data[existingIdx] = {
            ...existing,
            high: Math.max(existing.high, tick.high),
            low: Math.min(existing.low, tick.low),
            close: tick.close,
        };
    }
    return null; // lastBar unchanged
};

export const useChartData = (
    epic: string,
    resolution: string,
    series: ISeriesApi<"Candlestick"> | null,
    chart: IChartApi | null
) => {
    const [isChartLoading, setIsChartLoading] = useState(true);
    const [isHistoryLoading, setIsHistoryLoading] = useState(false);

    const isHistoryLoadingRef = useRef(false);
    const isInitialLoadRef = useRef(true);
    const fullDataRef = useRef<Kline[]>([]);
    const lastBarRef = useRef<Kline | null>(null);
    const tickBufferRef = useRef<WsKline[]>([]);

    const connectionRef = useRef<HubConnection | null>(null);
    const previousEpicRef = useRef<string | null>(null);
    const previousResolutionRef = useRef<string | null>(null);
    const currentEpicRef = useRef<string>(epic);
    const currentResolutionRef = useRef<string>(resolution);
    const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(series);
    const refreshDataRef = useRef<() => Promise<void>>(undefined);

    // Keep refs up to date every render
    useEffect(() => {
        currentEpicRef.current = epic;
        currentResolutionRef.current = resolution;
        seriesRef.current = series;
    }, [epic, resolution, series]);

    // ── Tick processor ───────────────────────────────────────────────────────
    const processTick = useCallback((tick: WsKline) => {
        const currentSeries = seriesRef.current;
        if (!currentSeries || tick.epic !== currentEpicRef.current) return;

        // Buffer ticks while initial history is loading
        if (isInitialLoadRef.current) {
            tickBufferRef.current.push(tick);
            return;
        }

        try {
            const updatedBar = mergeTickIntoData(
                fullDataRef.current,
                lastBarRef.current,
                tick,
                currentResolutionRef.current
            );
            if (updatedBar) {
                lastBarRef.current = updatedBar;
                currentSeries.update(updatedBar);
            } else {
                // Historical merge: update the series entry directly
                const binnedTime = formatTimeToBin(tick.time, getBinSize(currentResolutionRef.current));
                const merged = fullDataRef.current.find(k => k.time === binnedTime);
                if (merged) currentSeries.update(merged);
            }
        } catch (e) { console.error("[SignalR] Process Tick Error:", e); }
    }, []);

    // ── 1. Persistent SignalR Connection ─────────────────────────────────────
    useEffect(() => {
        const hubUrl = `${API_BASE_URL}/hub/market`;
        const conn = new HubConnectionBuilder()
            .withUrl(hubUrl)
            .withAutomaticReconnect()
            .configureLogging(LogLevel.Warning)
            .build();

        conn.on(HUB_EVENTS.TICK, processTick);

        conn.onreconnecting(() => {
            console.warn(`[SignalR] Market Hub connection lost. Reconnecting... (Epic: ${currentEpicRef.current})`);
        });

        conn.onreconnected(async () => {
            const epic = currentEpicRef.current;
            if (epic) {
                try {
                    await conn.invoke("Subscribe", epic);
                    if (refreshDataRef.current) refreshDataRef.current();
                } catch (err) { console.error("[SignalR] Re-subscribe Error:", err); }
            }
        });

        const startConn = async () => {
            try {
                await conn.start();
                if (currentEpicRef.current) await conn.invoke("Subscribe", currentEpicRef.current);
            } catch (err) { console.error("[SignalR] Connection Error:", err); }
        };

        connectionRef.current = conn;
        startConn();

        return () => { conn.stop(); };
    }, [processTick]);

    // ── 2. Fetch & Epic Subscription Management ───────────────────────────────
    const loadChartData = useCallback(async () => {
        if (!series || !chart) return;

        const epic = currentEpicRef.current;
        const resolution = currentResolutionRef.current;
        const cacheKey = `${epic}:${resolution}`;

        // Detect instrument/resolution switch using dedicated refs
        const isEpicChanged = previousEpicRef.current !== epic;
        const isResChanged = previousResolutionRef.current !== resolution;
        const isTargetChanged = isEpicChanged || isResChanged;

        if (isTargetChanged) {
            isInitialLoadRef.current = true;
            setIsChartLoading(true);
            fullDataRef.current = [];
            lastBarRef.current = null;
            tickBufferRef.current = [];
        }

        // Show cache immediately on switch for instant visual feedback
        const cached = globalChartCache[cacheKey];
        if (isTargetChanged && cached && cached.length > 0) {
            fullDataRef.current = [...cached];
            series.setData(cached);
            lastBarRef.current = cached[cached.length - 1];
            setIsChartLoading(false);
        }

        try {
            const response = await apiClient.api.marketKlinesList({ epic, resolution, max_bars: 500 });
            const apiData: Kline[] = response.data as unknown as Kline[];

            // Discard stale response if instrument changed during fetch
            if (epic !== currentEpicRef.current || resolution !== currentResolutionRef.current) return;

            if (apiData && apiData.length > 0) {
                fullDataRef.current = apiData;
                lastBarRef.current = apiData[apiData.length - 1];

                // Flush buffered ticks that arrived during the API fetch
                if (tickBufferRef.current.length > 0) {
                    const buffered = tickBufferRef.current.splice(0);
                    for (const tick of buffered) {
                        if (tick.epic !== epic) continue;
                        const updated = mergeTickIntoData(fullDataRef.current, lastBarRef.current, tick, resolution);
                        if (updated) lastBarRef.current = updated;
                    }
                }

                series.setData(fullDataRef.current);
                updateCache(cacheKey, fullDataRef.current);
                isInitialLoadRef.current = false;

                if (chart && isTargetChanged && (!cached || cached.length === 0)) {
                    const count = fullDataRef.current.length;
                    chart.timeScale().setVisibleLogicalRange({ from: Math.max(0, count - 180), to: count + 15 });
                    series.priceScale().applyOptions({ autoScale: true });
                }
            }
        } catch (err) { console.error("Market Data Fetch Error:", err); }

        setIsChartLoading(false);
        previousEpicRef.current = epic;
        previousResolutionRef.current = resolution;
    }, [series, chart, processTick]);

    // Keep refreshDataRef in sync with latest loadChartData
    useEffect(() => {
        refreshDataRef.current = loadChartData;
    }, [loadChartData]);

    // Trigger load and manage SignalR subscriptions on target change
    useEffect(() => {
        if (!series || !chart) return;

        const conn = connectionRef.current;
        if (conn && conn.state === "Connected") {
            if (previousEpicRef.current && previousEpicRef.current !== epic) {
                conn.invoke("Unsubscribe", previousEpicRef.current).catch(() => { });
            }
            conn.invoke("Subscribe", epic).catch(console.error);
        }

        loadChartData();
    }, [epic, resolution, series, chart, loadChartData]);

    // ── 3. Infinite / Lazy History Loading ───────────────────────────────────
    const hasMoreHistoryRef = useRef<Record<string, boolean>>({});

    const handleLazyLoad = useCallback(async (range: any, chart?: IChartApi | null) => {
        if (!series || !range || isHistoryLoadingRef.current || fullDataRef.current.length === 0 || isInitialLoadRef.current) return;

        const cacheKey = `${epic}:${resolution}`;
        if (hasMoreHistoryRef.current[cacheKey] === false) return;

        if (range.from < 10) {
            const firstCandle = fullDataRef.current[0];
            if (!firstCandle) return;

            isHistoryLoadingRef.current = true;
            setIsHistoryLoading(true);

            try {
                const resp = await apiClient.api.marketKlinesList({ epic, resolution, max_bars: 500, to: firstCandle.time as number });
                const oldData: Kline[] = resp.data as unknown as Kline[];

                if (oldData && oldData.length > 0) {
                    const existingData = [...fullDataRef.current];
                    const existingTimes = new Set(existingData.map(d => d.time));
                    const uniqueOldData = oldData.filter(d => !existingTimes.has(d.time));
                    const addedCount = uniqueOldData.length;

                    if (addedCount > 0) {
                        const combined = [...uniqueOldData, ...existingData].sort((a, b) => (a.time as number) - (b.time as number));
                        fullDataRef.current = combined;
                        updateCache(cacheKey, combined);

                        const currentRange = chart?.timeScale().getVisibleLogicalRange();
                        series.setData(combined);

                        if (chart && currentRange) {
                            chart.timeScale().setVisibleLogicalRange({
                                from: currentRange.from + addedCount,
                                to: currentRange.to + addedCount,
                            });
                        }
                    } else {
                        // All returned bars were duplicates → no more history
                        hasMoreHistoryRef.current[cacheKey] = false;
                    }
                } else {
                    hasMoreHistoryRef.current[cacheKey] = false;
                }
            } catch (err) { console.error("Failed to fetch history:", err); }
            finally {
                isHistoryLoadingRef.current = false;
                setIsHistoryLoading(false);
            }
        }
    }, [epic, resolution, series]);

    return { isChartLoading, isHistoryLoading, fullData: fullDataRef, handleLazyLoad };
};
