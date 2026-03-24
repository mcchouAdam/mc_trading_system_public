import React, { useEffect, useRef, useState } from 'react';
import { createChart, LineStyle } from 'lightweight-charts';
import type { Time, ISeriesApi, IChartApi, IPriceLine } from 'lightweight-charts';
import { ChartHeader } from './ChartHeader';
import { TradeActionPanel } from './TradeActionPanel';
import { CHART_OPTIONS, CHART_COLORS } from './chartConstants';
import { calculatePnL, formatPnLTitle, getBinSize, formatDisplayTime, formatFullDisplayTime, formatTimeToBin } from './chartUtils';
import { useChartData, type Kline } from './useChartData';
import { parseToUnix } from '../../utils/dateUtils';
import { apiClient } from '../../api/apiClient';
import './TradingChart.css';

interface TradingChartProps {
    epic: string;
    resolution: string;
    onResolutionChange: (res: string) => void;
    openTrades?: any[];
    selectedDealId?: string | null;
    selectedHistoryTrade?: any | null;
    onRefresh?: () => void;
    onNotify?: (title: string, message: string, type: 'info' | 'error' | 'confirm', onConfirm?: () => void) => void;
}

export const TradingChart: React.FC<TradingChartProps> = ({
    epic, resolution, onResolutionChange,
    openTrades = [], selectedDealId = null, selectedHistoryTrade = null,
    onRefresh, onNotify
}) => {
    const chartContainerRef = useRef<HTMLDivElement>(null);
    const chartRef = useRef<IChartApi | null>(null);
    const [series, setSeries] = useState<ISeriesApi<"Candlestick"> | null>(null);

    const [isPlacingOrder, setIsPlacingOrder] = useState<boolean>(false);
    const { isChartLoading, isHistoryLoading, fullData, handleLazyLoad } = useChartData(epic, resolution, series, chartRef.current);

    const lazyLoadRef = useRef(handleLazyLoad);
    useEffect(() => { lazyLoadRef.current = handleLazyLoad; }, [handleLazyLoad]);

    const linesRef = useRef<Map<string, { entry: IPriceLine, tp?: IPriceLine, sl?: IPriceLine }>>(new Map());
    const openTradesRef = useRef<any[]>(openTrades);

    useEffect(() => { openTradesRef.current = openTrades; }, [openTrades]);

    const handlePlaceOrder = async (direction: 'BUY' | 'SELL', size: number) => {
        if (!onNotify) return;
        onNotify("Confirm Order", `Are you sure you want to ${direction} ${size} of ${epic}?`, 'confirm', async () => {
            setIsPlacingOrder(true);
            try {
                await apiClient.api.tradeOrderCreate({ epic, direction, size });
                onNotify("Order Submitted", `Trade signal published to queue for ${epic}`, 'info');
                if (onRefresh) onRefresh();
            } catch (e: any) {
                const message = e?.response?.data?.detail || e.message || 'Order failed';
                onNotify("Order Failed", message, 'error');
            } finally {
                setIsPlacingOrder(false);
            }
        });
    };

    // 1. Initialize Chart Object
    useEffect(() => {
        if (!chartContainerRef.current) return;
        const chart = createChart(chartContainerRef.current, {
            ...CHART_OPTIONS,
            timeScale: { ...CHART_OPTIONS.timeScale, tickMarkFormatter: formatDisplayTime },
            localization: { ...CHART_OPTIONS.localization, timeFormatter: formatFullDisplayTime }
        } as any);
        chartRef.current = chart;

        const candleSeries = chart.addCandlestickSeries({
            upColor: CHART_COLORS.up, downColor: CHART_COLORS.down,
            borderVisible: false, wickUpColor: CHART_COLORS.up, wickDownColor: CHART_COLORS.down
        });
        setSeries(candleSeries);

        chart.timeScale().subscribeVisibleLogicalRangeChange(async (range) => {
            await lazyLoadRef.current(range, chart);
        });

        const handleResize = () => chart.applyOptions({ width: chartContainerRef.current?.clientWidth });
        window.addEventListener('resize', handleResize);
        return () => {
            window.removeEventListener('resize', handleResize);
            chart.remove();
            setSeries(null);
        };
    }, []);

    // 2. Update Price Lines (Entry/SL/TP)
    useEffect(() => {
        if (!series) return;
        const map = linesRef.current;

        let currentTrades = openTradesRef.current.filter((t: any) => t.epic === epic);
        currentTrades = selectedDealId ? currentTrades.filter((t: any) => t.deal_id === selectedDealId) : [];

        const activeIds = new Set(currentTrades.map((t: any) => t.deal_id));
        for (const [id, lines] of map.entries()) {
            if (!activeIds.has(id)) {
                series.removePriceLine(lines.entry);
                if (lines.tp) series.removePriceLine(lines.tp);
                if (lines.sl) series.removePriceLine(lines.sl);
                map.delete(id);
            }
        }

        currentTrades.forEach(trade => {
            let lines = map.get(trade.deal_id);
            if (!lines) {
                lines = {
                    entry: series.createPriceLine({
                        price: trade.entry_price,
                        color: trade.direction === 'BUY' ? CHART_COLORS.up : CHART_COLORS.down,
                        lineWidth: 1, lineStyle: LineStyle.Solid, axisLabelVisible: true,
                        title: `${trade.direction} ${(trade.size || 1)}`,
                    })
                };
                map.set(trade.deal_id, lines);
            } else {
                lines.entry.applyOptions({ price: trade.entry_price });
            }

            if (trade.stop_level) {
                const sl = calculatePnL(trade, trade.stop_level);
                const title = formatPnLTitle('SL', sl.pnl, sl.pct);
                if (!lines.sl) {
                    lines.sl = series.createPriceLine({
                        price: trade.stop_level, color: CHART_COLORS.orange,
                        lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: true, title
                    });
                } else lines.sl.applyOptions({ price: trade.stop_level, title });
            }

            const tpLevel = trade.limit_level || trade.profit_level;
            if (tpLevel) {
                const tp = calculatePnL(trade, tpLevel);
                const title = formatPnLTitle('TP', tp.pnl, tp.pct);
                if (!lines.tp) {
                    lines.tp = series.createPriceLine({
                        price: tpLevel, color: CHART_COLORS.up,
                        lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: true, title
                    });
                } else lines.tp.applyOptions({ price: tpLevel, title });
            }
        });
    }, [openTrades, epic, selectedDealId]);

    // 3. Handle Historical Markers
    useEffect(() => {
        if (isChartLoading || !series || !chartRef.current) return;
        const chart = chartRef.current;

        if (!selectedHistoryTrade || selectedHistoryTrade.epic !== epic) {
            series.setMarkers([]); return;
        }

        const t = selectedHistoryTrade;
        const binSize = getBinSize(resolution);
        const rawEntryTs = parseToUnix(t.entry_time);
        const rawExitTs = parseToUnix(t.exit_time);
        const entryTs = formatTimeToBin(rawEntryTs, binSize);
        const exitTs = formatTimeToBin(rawExitTs, binSize);

        const data = fullData.current;
        const isOutsideRange = !data.length || (rawEntryTs < (data[0].time as number)) || (rawExitTs > (data[data.length - 1].time as number) + binSize * 10);

        const applyMarkers = () => {
            const isBuy = t.direction === 'BUY';
            const directionColor = isBuy ? CHART_COLORS.up : CHART_COLORS.down;
            const exitColor = t.pnl >= 0 ? CHART_COLORS.up : CHART_COLORS.down;

            series.setMarkers([
                { time: entryTs, position: isBuy ? 'belowBar' : 'aboveBar', color: directionColor, shape: isBuy ? 'arrowUp' : 'arrowDown', text: 'Entry' },
                { time: exitTs, position: isBuy ? 'aboveBar' : 'belowBar', color: exitColor, shape: isBuy ? 'arrowDown' : 'arrowUp', text: `Exit PnL: ${t.pnl.toFixed(2)}` }
            ]);
            chart.timeScale().setVisibleRange({ from: ((entryTs as number) - binSize * 20) as Time, to: ((exitTs as number) + binSize * 20) as Time });
        };

        if (isOutsideRange) {
            apiClient.api.marketKlinesList({ epic, resolution, max_bars: 500, to: rawExitTs + binSize * 100 })
                .then(res => res.data as unknown as Kline[])
                .then(fetched => {
                    if (fetched.length) {
                        fullData.current = fetched;
                        series.setData(fetched);
                        applyMarkers();
                    }
                }).catch(console.error);
        } else applyMarkers();
    }, [selectedHistoryTrade, epic, isChartLoading, resolution, fullData]);

    return (
        <div className="chart-content">
            <div className={`chart-wrapper ${isChartLoading ? 'chart-wrapper--loading' : ''}`}>
                {isHistoryLoading && <div className="chart-history-loading">Loading History...</div>}
                <ChartHeader epic={epic} resolution={resolution} onResolutionChange={onResolutionChange} />
                <TradeActionPanel isPlacingOrder={isPlacingOrder} onPlaceOrder={handlePlaceOrder} />
                <div ref={chartContainerRef} className="chart-canvas" />
            </div>
        </div>
    );
};
