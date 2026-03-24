import React, { useState, useEffect } from 'react';
import './RiskPanel.css';
import type { RiskStatus } from '../../types';

// Colour palette per status — single source of truth
const STATUS_COLORS = {
    win: '#00E676',
    loss: '#F44336',
    warning: '#FFC107',
} as const;

type StatusColor = keyof typeof STATUS_COLORS;

interface RiskMetricBarProps {
    label: string;
    currentValue: number;
    limitValue: number;
    enabled: boolean;
    editing: boolean;
    onToggle: (enabled: boolean) => void;
    onLimitUpdate: (val: number) => void;
    color: string;
}

const RiskMetricBar: React.FC<RiskMetricBarProps> = ({
    label, currentValue, limitValue, enabled, editing,
    onToggle, onLimitUpdate, color
}) => {
    const ratio = Math.min(100, (Math.max(0, -currentValue) / Math.max(0.1, limitValue)) * 100);
    const isExceeded = -currentValue >= limitValue && enabled;
    const barColor = isExceeded ? STATUS_COLORS.loss : (ratio > 80 ? STATUS_COLORS.warning : color);

    return (
        <div className={`risk-bar-container ${(!editing && !enabled) ? 'risk-bar-container--disabled' : ''}`}>
            <div className="risk-bar-info">
                <div className="risk-bar-label-row">
                    <span className="risk-bar-label">{label}</span>
                    {editing && (
                        <input
                            type="checkbox"
                            checked={enabled}
                            onChange={e => onToggle(e.target.checked)}
                        />
                    )}
                </div>

                {editing ? (
                    <div className="risk-bar-input-group">
                        <input
                            className="risk-input"
                            type="number"
                            step="0.1"
                            value={limitValue}
                            disabled={!enabled}
                            onChange={e => onLimitUpdate(parseFloat(e.target.value))}
                        />
                        <span className={`risk-bar-pct-unit ${enabled ? 'risk-bar-pct-unit--enabled' : 'risk-bar-pct-unit--disabled'}`}>
                            %
                        </span>
                    </div>
                ) : (
                    <span className={`risk-bar-value ${isExceeded ? 'loss' : ''}`}>
                        {!enabled && <span className="risk-bar-disabled">DISABLED</span>}
                        {currentValue.toFixed(2)}% / -{limitValue}%
                    </span>
                )}
            </div>

            <div className="progress-track">
                <div
                    className="progress-fill"
                    style={{
                        '--fill-width': `${ratio}%`,
                        '--fill-color': barColor,
                        '--fill-shadow': ratio > 0 ? `0 0 8px ${barColor}aa` : 'none',
                    } as React.CSSProperties}
                />
            </div>
        </div>
    );
};

interface RiskPanelProps {
    riskStatus: RiskStatus | null;
    onResume: () => void;
    onSaveLimits: (daily: number, dailyEnabled: boolean, monthly: number, monthlyEnabled: boolean) => void;
    width?: string;
}

export const RiskPanel: React.FC<RiskPanelProps> = ({
    riskStatus, onResume, onSaveLimits, width
}) => {
    const [editingLimits, setEditingLimits] = useState(false);

    // Limit Form State
    const [dailyLimitInput, setDailyLimitInput] = useState(5);
    const [dailyEnabled, setDailyEnabled] = useState(true);
    const [monthlyLimitInput, setMonthlyLimitInput] = useState(15);
    const [monthlyEnabled, setMonthlyEnabled] = useState(true);

    useEffect(() => {
        if (riskStatus && !editingLimits) {
            setDailyLimitInput(riskStatus.daily_limit_pct || 5);
            setDailyEnabled(riskStatus.daily_limit_enabled ?? true);
            setMonthlyLimitInput(riskStatus.monthly_limit_pct || 15);
            setMonthlyEnabled(riskStatus.monthly_limit_enabled ?? true);
        }
    }, [riskStatus, editingLimits]);

    const handleSave = () => {
        onSaveLimits(dailyLimitInput, dailyEnabled, monthlyLimitInput, monthlyEnabled);
        setEditingLimits(false);
    };

    // Derive status
    const isOverride = riskStatus?.is_resume_override;
    const isHalted = riskStatus?.is_halted;
    const statColor: StatusColor = isOverride ? 'warning' : (isHalted ? 'loss' : 'win');
    const statLabel = isOverride ? 'RESUMED' : (isHalted ? 'HALTED' : 'ACTIVE');

    const equity = riskStatus?.equity || 0;
    const dailyStart = riskStatus?.start_day_balance || 0;
    const monthlyStart = riskStatus?.start_month_balance || 0;
    const dailyPnlPct = riskStatus?.daily_pnl_pct ?? 0;
    const monthlyPnlPct = riskStatus?.monthly_pnl_pct ?? 0;

    return (
        <div className="risk-pane" style={{ width }}>
            <div className="risk-content">

                {/* Account Equity Card */}
                <div className={`metric-card metric-card--${statColor}`}>
                    <div className="mc-header">
                        <div className="mc-title">Account Equity</div>
                        <div className={`status-badge status-badge--${statColor}`}>
                            <span className="status-dot" />
                            {statLabel}
                        </div>
                    </div>
                    <div className="mc-val">
                        ${Number(equity).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        <span className={`mc-val-pnl ${dailyPnlPct >= 0 ? 'win' : 'loss'}`}>
                            {dailyPnlPct >= 0 ? '▲' : '▼'}{Math.abs(dailyPnlPct).toFixed(2)}%
                        </span>
                    </div>
                    {(dailyStart > 0 || monthlyStart > 0) && (
                        <div className="mc-subtext">
                            {dailyStart > 0 && <div className="mc-subtext-item">Today Start: ${Number(dailyStart).toLocaleString()}</div>}
                            {monthlyStart > 0 && <div className="mc-subtext-item">This Month: ${Number(monthlyStart).toLocaleString()}</div>}
                        </div>
                    )}
                </div>

                {/* Drawdown Bars */}
                <div className="risk-metric-bars">
                    <RiskMetricBar
                        label="Daily Drawdown"
                        currentValue={dailyPnlPct}
                        limitValue={dailyLimitInput}
                        enabled={editingLimits ? dailyEnabled : (riskStatus?.daily_limit_enabled !== false)}
                        editing={editingLimits}
                        onToggle={setDailyEnabled}
                        onLimitUpdate={setDailyLimitInput}
                        color={STATUS_COLORS.win}
                    />
                    <RiskMetricBar
                        label="Monthly Drawdown"
                        currentValue={monthlyPnlPct}
                        limitValue={monthlyLimitInput}
                        enabled={editingLimits ? monthlyEnabled : (riskStatus?.monthly_limit_enabled !== false)}
                        editing={editingLimits}
                        onToggle={setMonthlyEnabled}
                        onLimitUpdate={setMonthlyLimitInput}
                        color="#2962FF"
                    />
                </div>

                {/* Action Buttons */}
                <div className="risk-action-row">
                    <button
                        className="action-btn btn-resume"
                        onClick={onResume}
                        disabled={!riskStatus?.can_resume}
                    >
                        RESUME
                    </button>
                    {editingLimits ? (
                        <>
                            <button className="action-btn btn-save" onClick={handleSave}>SAVE</button>
                            <button className="action-btn btn-cancel" onClick={() => setEditingLimits(false)}>CANCEL</button>
                        </>
                    ) : (
                        <button className="action-btn btn-edit" onClick={() => setEditingLimits(true)}>EDIT</button>
                    )}
                </div>
            </div>
        </div>
    );
};
