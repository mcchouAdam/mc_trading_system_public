import React from 'react';
import { apiClient } from '../../api/apiClient';
import { calculatePnL } from '../Chart/chartUtils';

interface PositionEditOverlayProps {
    trade: any;
    editSL: string;
    editTP: string;
    isSaving: boolean;
    onSLChange: (v: string) => void;
    onTPChange: (v: string) => void;
    onSave: () => void;
    onCancel: (e: React.MouseEvent) => void;
}

const PnLHint: React.FC<{ trade: any; value: string }> = ({ trade, value }) => {
    const calc = calculatePnL(trade, value);
    if (!calc || calc.pnl === null) return null;
    return (
        <div className={`edit-pnl-hint ${calc.pnl >= 0 ? 'win' : 'loss'}`}>
            {calc.pnl > 0 ? '+' : ''}{calc.pnl.toFixed(2)} ({calc.pct?.toFixed(2)}%)
        </div>
    );
};

export const PositionEditOverlay: React.FC<PositionEditOverlayProps> = ({
    trade, editSL, editTP, isSaving,
    onSLChange, onTPChange, onSave, onCancel
}) => (
    <div className="edit-overlay">
        <div className="edit-overlay-fields">
            <div className="edit-overlay-field">
                <label className="edit-overlay-label">Stop Loss</label>
                <input
                    className="search-input edit-overlay-input"
                    value={editSL}
                    onChange={e => onSLChange(e.target.value)}
                    placeholder="SL Price"
                />
                <PnLHint trade={trade} value={editSL} />
            </div>
            <div className="edit-overlay-field">
                <label className="edit-overlay-label">Take Profit</label>
                <input
                    className="search-input edit-overlay-input"
                    value={editTP}
                    onChange={e => onTPChange(e.target.value)}
                    placeholder="TP Price"
                />
                <PnLHint trade={trade} value={editTP} />
            </div>
        </div>
        <div className="edit-overlay-actions">
            <button className="search-btn edit-overlay-save" onClick={onSave} disabled={isSaving}>
                {isSaving ? 'Saving...' : 'SAVE CHANGES'}
            </button>
            <button className="search-btn edit-overlay-cancel" onClick={onCancel}>
                CANCEL
            </button>
        </div>
    </div>
);

/**
 * Hook encapsulating the SL/TP edit logic for a single position.
 * Handles API call, optimistic update, and loading state.
 */
export function usePositionEdit(
    onUpdateOptimistically: (dealId: string, sl: number | null, tp: number | null) => void,
    onRefresh: () => void,
    onNotify: (title: string, message: string, type: 'info' | 'error' | 'confirm') => void
) {
    const [editingId, setEditingId] = React.useState<string | null>(null);
    const [editSL, setEditSL] = React.useState('');
    const [editTP, setEditTP] = React.useState('');
    const [isSaving, setIsSaving] = React.useState(false);

    const startEdit = (e: React.MouseEvent, trade: any) => {
        e.stopPropagation();
        setEditingId(trade.deal_id);
        setEditSL(trade.stop_level ? trade.stop_level.toString() : '');
        setEditTP(trade.profit_level ? trade.profit_level.toString() : '');
    };

    const cancelEdit = (e: React.MouseEvent) => {
        e.stopPropagation();
        setEditingId(null);
    };

    const save = async (dealId: string) => {
        setIsSaving(true);
        try {
            const sl = parseFloat(editSL);
            const tp = parseFloat(editTP);
            const body: Record<string, number> = {};
            if (!isNaN(sl) && sl > 0) body.stopLevel = sl;
            if (!isNaN(tp) && tp > 0) body.profitLevel = tp;

            await apiClient.api.tradePositionLimitsUpdate(dealId, body);

            onUpdateOptimistically(dealId, body.stopLevel ?? null, body.profitLevel ?? null);
            setEditingId(null);
            setTimeout(onRefresh, 1500);
        } catch (error: any) {
            onNotify("Update Failed", error.message, 'error');
        } finally {
            setIsSaving(false);
        }
    };

    return { editingId, editSL, editTP, isSaving, startEdit, cancelEdit, save, setEditSL, setEditTP };
}
