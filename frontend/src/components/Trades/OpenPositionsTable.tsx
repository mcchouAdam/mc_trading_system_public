import React from 'react';
import { calculatePnL } from '../Chart/chartUtils';
import { TableHeader } from './TableHeader';
import { PositionEditOverlay, usePositionEdit } from './PositionEditOverlay';
import type { OpenTrade } from '../../types';
import type { NotifyFn } from '../../types';

interface OpenPositionsTableProps {
    trades: OpenTrade[];
    selectedDealId: string | null;
    onSelect: (dealId: string | null) => void;
    onJump: (ts: any) => void;
    onClose: (dealId: string) => void;
    onRefresh: () => void;
    onUpdateOptimistically: (dealId: string, sl: number | null, tp: number | null) => void;
    onNotify: NotifyFn;
    closingIds: Set<string>;
    pendingSLIds: Set<string>;
    pendingTPIds: Set<string>;
}

const LevelCell: React.FC<{ trade: OpenTrade; levelKey: 'stop_level' | 'profit_level'; isPending: boolean }> = ({
    trade, levelKey, isPending
}) => {
    const value = trade[levelKey];
    if (isPending) return <span className="td-syncing">Syncing...</span>;
    return (
        <div className="td-level-cell">
            <span>{value ? (value as number).toFixed(2) : '-'}</span>
            {value && (() => {
                const p = calculatePnL(trade, value.toString());
                return p && p.pnl !== null && (
                    <span className={`edit-pnl-hint ${p.pnl >= 0 ? 'win' : 'loss'}`}>
                        {p.pnl.toFixed(2)} ({p.pct?.toFixed(2)}%)
                    </span>
                );
            })()}
        </div>
    );
};

export const OpenPositionsTable: React.FC<OpenPositionsTableProps> = ({
    trades, selectedDealId, onSelect, onJump, onClose, onRefresh,
    onUpdateOptimistically, onNotify, closingIds, pendingSLIds, pendingTPIds
}) => {
    const edit = usePositionEdit(onUpdateOptimistically, onRefresh, onNotify);
    const totalPnL = trades.reduce((s, t) => s + (t.unrealized_pnl || 0), 0);

    return (
        <div className="open-pane" style={{ width: '100%', overflowX: 'auto', overflowY: 'hidden', display: 'flex', flexDirection: 'column', minWidth: 0 }}>
            <div style={{ minWidth: 'fit-content', display: 'flex', flexDirection: 'column', flex: 1 }}>
                <TableHeader title="Open Positions" pnl={totalPnL} count={trades.length} badgeColor="#00E676" />

                <div className="table-wrapper">
                    <table className="trades-table">
                        <thead>
                            <tr>
                                <th>Strategy</th>
                                <th>Epic</th>
                                <th>Dir</th>
                                <th>Qty</th>
                                <th>Entry</th>
                                <th>U-PnL</th>
                                <th>SL</th>
                                <th>TP</th>
                                <th className="td-center">Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            {trades.map(t => {
                                const isEditing = edit.editingId === t.deal_id;
                                return (
                                    <tr
                                        key={t.deal_id}
                                        onClick={() => !isEditing && (onJump(t.entry_time), onSelect(selectedDealId === t.deal_id ? null : t.deal_id!))}
                                        className={t.deal_id === selectedDealId && !isEditing ? 'row--selected' : ''}
                                    >
                                        <td className="td-strategy">{t.strategy || 'MANUAL'}</td>
                                        <td>{t.epic}</td>
                                        <td><span className={t.direction === 'BUY' ? 'win' : 'loss'}>{t.direction}</span></td>
                                        <td>{t.size}</td>
                                        <td>{t.entry_price!.toFixed(2)}</td>
                                        <td><span className={(t.unrealized_pnl || 0) >= 0 ? 'win' : 'loss'}>{(t.unrealized_pnl || 0).toFixed(2)}</span></td>

                                        <td colSpan={2} style={{ padding: 0, position: 'relative' }}>
                                            {isEditing ? (
                                                <PositionEditOverlay
                                                    trade={t}
                                                    editSL={edit.editSL}
                                                    editTP={edit.editTP}
                                                    isSaving={edit.isSaving}
                                                    onSLChange={edit.setEditSL}
                                                    onTPChange={edit.setEditTP}
                                                    onSave={() => edit.save(t.deal_id!)}
                                                    onCancel={(e: React.MouseEvent) => edit.cancelEdit(e)}
                                                />
                                            ) : (
                                                <div style={{ display: 'flex', width: '100%' }}>
                                                    <div style={{ flex: 1, padding: '10px 12px' }}>
                                                        <LevelCell trade={t} levelKey="stop_level" isPending={pendingSLIds.has(t.deal_id!)} />
                                                    </div>
                                                    <div style={{ flex: 1, padding: '10px 12px' }}>
                                                        <LevelCell trade={t} levelKey="profit_level" isPending={pendingTPIds.has(t.deal_id!)} />
                                                    </div>
                                                </div>
                                            )}
                                        </td>

                                        <td className="td-center">
                                            <div className="td-action-btns">
                                                {closingIds.has(t.deal_id!) ? (
                                                    <span className="td-closing">Closing...</span>
                                                ) : (
                                                    <>
                                                        <button className={`btn-icon ${isEditing ? 'btn-icon--hidden' : ''}`} onClick={e => edit.startEdit(e, t)}>✏️</button>
                                                        <button className={`btn-icon ${isEditing ? 'btn-icon--hidden' : ''}`} onClick={e => { e.stopPropagation(); onClose(t.deal_id!); }}>🗑️</button>
                                                    </>
                                                )}
                                            </div>
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
};
