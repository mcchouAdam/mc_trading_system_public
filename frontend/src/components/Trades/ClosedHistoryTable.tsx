import React, { useState } from 'react';
import { formatToLocal } from '../../utils/dateUtils';
import { TableHeader } from './TableHeader';
import type { NotifyFn } from '../../types';

interface ClosedHistoryTableProps {
    trades: any[];
    fromDate: string;
    toDate: string;
    totalPnL: number;
    totalCount: number;
    currentPage: number;
    isFetching: boolean;
    currentEpic: string;
    selectedTrade: any | null;
    onSearch: (from: string, to: string) => void;
    onRefresh: (f?: string, t?: string, page?: number) => void;
    onSelect: (trade: any | null) => void;
    onNotify?: NotifyFn;
}

export const ClosedHistoryTable: React.FC<ClosedHistoryTableProps> = ({
    trades, fromDate, toDate, totalPnL, totalCount, currentPage, isFetching,
    currentEpic, selectedTrade, onSearch, onRefresh, onSelect, onNotify
}) => {
    const [localFrom, setLocalFrom] = useState(fromDate);
    const [localTo, setLocalTo] = useState(toDate);

    const handleSearch = async () => {
        await onSearch(localFrom, localTo);
        onRefresh(localFrom, localTo, 1);
    };

    const handleRowClick = (t: any) => {
        if (selectedTrade?.id === t.id) {
            onSelect(null);
            return;
        }
        if (t.epic !== currentEpic) {
            onNotify?.(
                "Epic Mismatch",
                `Selected trade is for ${t.epic}, but chart is showing ${currentEpic}.`,
                'info'
            );
            return;
        }
        onSelect(t);
    };

    const maxPage = Math.max(1, Math.ceil(totalCount / 10));

    return (
        <div className="closed-pane" style={{ width: '100%', overflowX: 'auto', overflowY: 'hidden', display: 'flex', flexDirection: 'column', minWidth: 0 }}>
            <div style={{ minWidth: 'fit-content', display: 'flex', flexDirection: 'column', flex: 1 }}>
                <TableHeader title="Closed History" pnl={totalPnL} count={totalCount}>
                    <div className="search-bar">
                        <input className="search-input" type="date" value={localFrom} onChange={e => setLocalFrom(e.target.value)} />
                        <input className="search-input" type="date" value={localTo} onChange={e => setLocalTo(e.target.value)} />
                        <button className="search-btn" onClick={handleSearch} disabled={isFetching}>Search</button>
                    </div>
                </TableHeader>

                <div className="table-wrapper">
                    {isFetching && (
                        <div className="table-loading-overlay">Loading...</div>
                    )}
                    <table className="trades-table">
                        <thead>
                            <tr>
                                <th>Strategy</th>
                                <th>Epic</th>
                                <th>Dir</th>
                                <th>Time</th>
                                <th>PnL</th>
                            </tr>
                        </thead>
                        <tbody>
                            {trades.map(t => (
                                <tr
                                    key={t.id}
                                    onClick={() => handleRowClick(t)}
                                    className={selectedTrade?.id === t.id ? 'row--selected' : ''}
                                >
                                    <td className="td-strategy">{t.strategy || 'MANUAL'}</td>
                                    <td>{t.epic}</td>
                                    <td className={t.direction === 'BUY' ? 'win' : 'loss'}>{t.direction}</td>
                                    <td className="td-timestamp">{formatToLocal(t.exit_time)}</td>
                                    <td><span className={t.pnl >= 0 ? 'win' : 'loss'}>{t.pnl.toFixed(2)}</span></td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>

                <div className="pagination-bar">
                    <button
                        className="search-btn btn-pagination"
                        disabled={currentPage <= 1 || isFetching}
                        onClick={() => onRefresh(localFrom, localTo, currentPage - 1)}
                    >
                        Prev
                    </button>
                    <span className="pagination-page-info">
                        Page <b>{currentPage}</b> of {maxPage}
                    </span>
                    <button
                        className="search-btn btn-pagination"
                        disabled={currentPage >= maxPage || isFetching}
                        onClick={() => onRefresh(localFrom, localTo, currentPage + 1)}
                    >
                        Next
                    </button>
                </div>
            </div>
        </div>
    );
};
