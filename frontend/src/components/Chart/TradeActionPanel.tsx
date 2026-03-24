import React, { useState } from 'react';
import './TradingChart.css';

interface TradeActionPanelProps {
    isPlacingOrder: boolean;
    initialSize?: number;
    onPlaceOrder: (direction: 'BUY' | 'SELL', size: number) => void;
}

export const TradeActionPanel: React.FC<TradeActionPanelProps> = ({
    isPlacingOrder,
    initialSize = 0.05,
    onPlaceOrder
}) => {
    const [size, setSize] = useState<number>(initialSize);

    return (
        <div className="trade-action-panel">
            <button
                className={`trade-btn trade-btn--sell ${isPlacingOrder ? 'trade-btn--disabled' : ''}`}
                disabled={isPlacingOrder}
                onClick={() => onPlaceOrder('SELL', size)}
            >
                SELL
            </button>

            <div className="trade-size-box">
                <div className="trade-size-label">SIZE</div>
                <input
                    className="trade-size-input"
                    type="number"
                    step="0.01"
                    min="0.01"
                    value={size}
                    onChange={e => setSize(parseFloat(e.target.value) || 0)}
                    onFocus={e => e.target.select()}
                />
            </div>

            <button
                className={`trade-btn trade-btn--buy ${isPlacingOrder ? 'trade-btn--disabled' : ''}`}
                disabled={isPlacingOrder}
                onClick={() => onPlaceOrder('BUY', size)}
            >
                BUY
            </button>
        </div>
    );
};
