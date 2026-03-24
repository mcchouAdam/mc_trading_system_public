import { useState, useCallback, useEffect } from 'react';
import { apiClient } from '../api/apiClient';
import { useNotification } from './useNotification';
import { useAccountSocket } from './useAccountSocket';
import { useTradeActions } from './useTradeActions';
import { useSystemConfig } from './useSystemConfig';
import type { RiskStatus, OpenTrade } from '../types';

export function useTradingSystem(fromDate: string, toDate: string) {
    // 1. Core State
    const [riskStatus, setRiskStatus] = useState<RiskStatus | null>(null);
    const [openTrades, setOpenTrades] = useState<OpenTrade[]>([]);
    const [closedTrades, setClosedTrades] = useState<any[]>([]);

    // Pagination / history
    const [isFetchingClosed, setIsFetchingClosed] = useState(false);
    const [closedTotalCount, setClosedTotalCount] = useState(0);
    const [closedTotalPnL, setClosedTotalPnL] = useState(0);
    const [currentPage, setCurrentPage] = useState(1);
    const [selectedHistoryTrade, setSelectedHistoryTrade] = useState<any | null>(null);

    // 2. Sub-Hooks
    const { modal, setModal, notify } = useNotification();

    const fetchStatusAndTrades = useCallback(async () => {
        try {
            const [risk, open] = await Promise.all([
                apiClient.api.riskStatusList(),
                apiClient.api.tradeOpenList(),
            ]);
            setRiskStatus(risk.data);
            setOpenTrades(open.data);
        } catch (err) { console.error(err); }
    }, []);

    const {
        closingIds, pendingSLIds, pendingTPIds,
        closePosition, updateOptimistically, clearFinishedActions
    } = useTradeActions(notify, fetchStatusAndTrades);

    const {
        config, availableStrategies, supportedEpics, fetchAll: fetchConfig,
        addStrategy, deleteStrategy, toggleStrategy, updateParams
    } = useSystemConfig(notify);

    // 3. Socket Integration
    useAccountSocket(useCallback((data: any) => {
        setRiskStatus(data.risk);
        setOpenTrades(data.trades);
        clearFinishedActions(data.trades);
    }, [clearFinishedActions]));

    // 4. Closed Data Fetching
    const fetchClosedData = useCallback(async (f?: string, t?: string, page: number = 1) => {
        setIsFetchingClosed(true);
        setSelectedHistoryTrade(null);
        try {
            const finalFrom = f || fromDate;
            const finalTo = t || toDate;
            // Use local timezone offset instead of hardcoded +08:00
            const tzOffset = -new Date().getTimezoneOffset();
            const sign = tzOffset >= 0 ? '+' : '-';
            const pad = (n: number) => String(Math.floor(Math.abs(n))).padStart(2, '0');
            const tzStr = `${sign}${pad(tzOffset / 60)}:${pad(tzOffset % 60)}`;

            const res = await apiClient.api.tradeClosedList({
                from_date: finalFrom ? `${finalFrom}T00:00:00${tzStr}` : undefined,
                to_date: finalTo ? `${finalTo}T23:59:59${tzStr}` : undefined,
                page, pageSize: 10,
            });
            const d = (res.data as any);
            setClosedTrades(d.items || []);
            setClosedTotalCount(d.totalCount || 0);
            setClosedTotalPnL(d.totalPnL || 0);
            setCurrentPage(page);
        } catch (err) { console.error(err); }
        finally { setIsFetchingClosed(false); }
    }, [fromDate, toDate]);

    // 5. Risk Actions
    const resumeTrade = async () => {
        await apiClient.api.riskResumeCreate();
        fetchStatusAndTrades();
    };

    const saveRiskLimits = async (
        daily: number,
        dailyEnabled: boolean,
        monthly: number,
        monthlyEnabled: boolean
    ) => {
        await apiClient.api.riskLimitsCreate({
            daily_limit_pct: daily, daily_limit_enabled: dailyEnabled,
            monthly_limit_pct: monthly, monthly_limit_enabled: monthlyEnabled,
        });
        fetchStatusAndTrades();
    };

    // Initial load
    useEffect(() => {
        fetchConfig();
        fetchStatusAndTrades();
        fetchClosedData();
    }, [fetchConfig, fetchStatusAndTrades, fetchClosedData]);

    return {
        riskStatus, setRiskStatus,
        openTrades,
        closedTrades,
        systemConfig: config,
        activeEpics: config.marketData,
        closingDealIds: closingIds,
        pendingSLDealIds: pendingSLIds,
        pendingTPDealIds: pendingTPIds,
        isFetchingClosed,
        closedTotalCount,
        closedTotalPnL,
        currentPage,
        selectedHistoryTrade,
        setSelectedHistoryTrade,
        fetchData: fetchStatusAndTrades,
        fetchClosedData,
        resumeTrade,
        saveRiskLimits,
        closePosition,
        updateTradeOptimistically: (id: string, sl: number | null, tp: number | null) =>
            updateOptimistically(id, sl, tp, setOpenTrades),
        modal, setModal, notify,
        availableStrategies,
        supportedEpics,
        addStrategy,
        deleteStrategy,
        toggleStrategyTarget: (id: string) => toggleStrategy(id, 'active'),
        toggleStrategyMl: (id: string) => toggleStrategy(id, 'use_ml'),
        updateStrategyParams: updateParams,
    };
}
