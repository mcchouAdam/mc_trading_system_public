import React from 'react';
import { OpenPositionsTable } from './OpenPositionsTable';
import { ClosedHistoryTable } from './ClosedHistoryTable';
import './TradesTables.css';

interface TradesTablesProps {
    openTrades: any[];
    closedTrades: any[];
    fromDate: string;
    toDate: string;
    onClosePosition: (dealId: string) => void;
    onJumpTo?: (ts: any) => void;
    selectedDealId: string | null;
    onSelectTrade: (dealId: string | null) => void;
    onRefresh: () => void;
    onRefreshClosed: (f?: string, t?: string, page?: number) => void;
    onSearch: (from: string, to: string) => void;
    onUpdateOptimistically: (dealId: string, sl: number | null, tp: number | null) => void;
    onNotify: (title: string, message: string, type: 'info' | 'error' | 'confirm', onConfirm?: () => void) => void;
    closingDealIds?: Set<string>;
    pendingSLDealIds?: Set<string>;
    pendingTPDealIds?: Set<string>;
    isFetchingClosed?: boolean;
    closedTotalCount?: number;
    closedTotalPnL?: number;
    currentPage?: number;
    selectedHistoryTrade?: any | null;
    onSelectHistoryTrade?: (trade: any | null) => void;
    currentEpic: string;
    openWidth?: string;
    onMouseDownOpen?: () => void;
    activeResizer?: string | null;
}

export const TradesTables: React.FC<TradesTablesProps> = ({
    openTrades, closedTrades, fromDate, toDate,
    onClosePosition, onJumpTo = () => { }, selectedDealId, onSelectTrade,
    onRefresh, onRefreshClosed, onSearch, onUpdateOptimistically, onNotify,
    closingDealIds = new Set(), pendingSLDealIds = new Set(), pendingTPDealIds = new Set(),
    isFetchingClosed = false, closedTotalCount = 0, closedTotalPnL = 0, currentPage = 1,
    selectedHistoryTrade = null, onSelectHistoryTrade = () => { },
    currentEpic, openWidth, onMouseDownOpen, activeResizer
}) => {
    return (
        <div className="trades-container">
            <div style={{ width: openWidth, display: 'flex', minWidth: 0 }}>
                <OpenPositionsTable
                    trades={openTrades}
                    selectedDealId={selectedDealId}
                    onSelect={onSelectTrade}
                    onJump={onJumpTo}
                    onClose={onClosePosition}
                    onRefresh={onRefresh}
                    onUpdateOptimistically={onUpdateOptimistically}
                    onNotify={onNotify}
                    closingIds={closingDealIds}
                    pendingSLIds={pendingSLDealIds}
                    pendingTPIds={pendingTPDealIds}
                />
            </div>

            <div
                className={`v-splitter-h ${activeResizer === 'open-closed' ? 'active' : ''}`}
                onMouseDown={onMouseDownOpen}
            />

            <div style={{ flex: 1, display: 'flex', minWidth: 0 }}>
                <ClosedHistoryTable
                    trades={closedTrades}
                    fromDate={fromDate}
                    toDate={toDate}
                    totalPnL={closedTotalPnL}
                    totalCount={closedTotalCount}
                    currentPage={currentPage}
                    isFetching={isFetchingClosed}
                    currentEpic={currentEpic}
                    selectedTrade={selectedHistoryTrade}
                    onSearch={onSearch}
                    onRefresh={onRefreshClosed}
                    onSelect={onSelectHistoryTrade}
                    onNotify={onNotify}
                />
            </div>
        </div>
    );
};
