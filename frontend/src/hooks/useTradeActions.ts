import { useState, useCallback } from 'react';
import { apiClient } from '../api/apiClient';
import type { OpenTrade, NotifyFn } from '../types';

export function useTradeActions(notify: NotifyFn, onRefresh: () => void) {
    const [closingIds, setClosingIds] = useState<Set<string>>(new Set());
    const [pendingSLIds, setPendingSLIds] = useState<Set<string>>(new Set());
    const [pendingTPIds, setPendingTPIds] = useState<Set<string>>(new Set());

    const closePosition = useCallback(async (dealId: string) => {
        notify(
            "Confirm Close",
            `Are you sure you want to close position ${dealId}?`,
            'confirm',
            async () => {
                try {
                    setClosingIds(prev => new Set(prev).add(dealId));
                    await apiClient.api.tradeCloseDelete(dealId);
                    onRefresh();

                    // Fallback timeout: clear if socket confirmation never arrives
                    setTimeout(() => {
                        setClosingIds(prev => {
                            if (prev.has(dealId)) {
                                notify("Close Timeout", `Position ${dealId} is still open after 7s.`, 'error');
                                const next = new Set(prev);
                                next.delete(dealId);
                                return next;
                            }
                            return prev;
                        });
                    }, 7000);
                } catch (error: any) {
                    notify("Error", error.message, 'error');
                    setClosingIds(prev => {
                        const next = new Set(prev);
                        next.delete(dealId);
                        return next;
                    });
                }
            }
        );
    }, [notify, onRefresh]);

    const updateOptimistically = useCallback((
        dealId: string,
        sl: number | null,
        tp: number | null,
        setTrades: React.Dispatch<React.SetStateAction<OpenTrade[]>>
    ) => {
        if (sl !== null) {
            setPendingSLIds(prev => new Set(prev).add(dealId));
            setTimeout(() => setPendingSLIds(prev => {
                const n = new Set(prev); n.delete(dealId); return n;
            }), 8000);
        }
        if (tp !== null) {
            setPendingTPIds(prev => new Set(prev).add(dealId));
            setTimeout(() => setPendingTPIds(prev => {
                const n = new Set(prev); n.delete(dealId); return n;
            }), 8000);
        }

        setTrades(prev => prev.map(t => {
            if (t.deal_id === dealId) {
                return {
                    ...t,
                    stop_level: sl !== null ? sl : t.stop_level,
                    profit_level: tp !== null ? tp : t.profit_level
                };
            }
            return t;
        }));
    }, []);

    const clearFinishedActions = useCallback((trades: OpenTrade[]) => {
        const currentIds = new Set(trades.map(t => t.deal_id));

        setClosingIds(prev => {
            const next = new Set(prev);
            prev.forEach(id => { if (!currentIds.has(id)) next.delete(id); });
            return next.size !== prev.size ? next : prev;
        });

        setPendingSLIds(prev => {
            const next = new Set(prev);
            prev.forEach(id => {
                const trade = trades.find(x => x.deal_id === id);
                // Clear if trade is gone or if stop_level has been set on server
                if (!trade || trade.stop_level != null) next.delete(id);
            });
            return next.size !== prev.size ? next : prev;
        });

        setPendingTPIds(prev => {
            const next = new Set(prev);
            prev.forEach(id => {
                const trade = trades.find(x => x.deal_id === id);
                if (!trade || trade.profit_level != null) next.delete(id);
            });
            return next.size !== prev.size ? next : prev;
        });
    }, []);

    return {
        closingIds, pendingSLIds, pendingTPIds,
        closePosition, updateOptimistically, clearFinishedActions
    };
}
