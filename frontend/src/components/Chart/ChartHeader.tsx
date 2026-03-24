import React from 'react';
import './TradingChart.css';

interface ChartHeaderProps {
    epic: string;
    resolution: string;
    onResolutionChange: (res: string) => void;
}

const RESOLUTIONS = [
    { l: '1m', v: 'MINUTE' },
    { l: '5m', v: 'MINUTE_5' },
    { l: '15m', v: 'MINUTE_15' },
    { l: '1H', v: 'HOUR' },
    { l: '4H', v: 'HOUR_4' },
    { l: 'D1', v: 'DAY' },
];

export const ChartHeader: React.FC<ChartHeaderProps> = ({ epic, resolution, onResolutionChange }) => (
    <div className="chart-overlay-header">
        <div>
            Live Trading DashBoard — <span className="chart-epic-label">[{epic}]</span>
        </div>
        <div className="resolution-group">
            {RESOLUTIONS.map(r => (
                <button
                    key={r.v}
                    className={`resolution-btn ${resolution === r.v ? 'resolution-btn--active' : ''}`}
                    onClick={() => onResolutionChange(r.v)}
                >
                    {r.l}
                </button>
            ))}
        </div>
    </div>
);
