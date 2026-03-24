import React from 'react';
import '../Watchlist/Watchlist.css';

interface StrategyItemProps {
    strategy: any;
    isHalted: boolean;
    supportsMl: boolean;
    onToggle: (id: string) => void;
    onToggleMl: (id: string) => void;
    onDelete: (id: string) => void;
    onEdit: (s: any) => void;
    onSelectEpic: (epic: string) => void;
}

export const StrategyItem: React.FC<StrategyItemProps> = ({
    strategy, isHalted, supportsMl, onToggle, onToggleMl, onDelete, onEdit, onSelectEpic
}) => {
    const isActive = strategy.active !== false;

    const mlTagClass = !supportsMl
        ? 'ml-tag ml-tag--disabled'
        : strategy.use_ml
            ? 'ml-tag ml-tag--on'
            : 'ml-tag ml-tag--off';

    return (
        <div className={`strategy-card ${(!isActive || isHalted) ? 'disabled' : ''}`}>
            <div className="strategy-item-row">
                <div className="strategy-item-left">
                    <div className="strat-name">{strategy.name}</div>
                    <div
                        className="strat-epic strat-epic-link"
                        onClick={() => onSelectEpic(strategy.epic)}
                    >
                        {strategy.epic}{' '}
                        <span className="strat-resolution">{strategy.resolution}</span>
                    </div>

                    <div className="strat-tag-row">
                        <span
                            className={mlTagClass}
                            title={supportsMl ? "Toggle ML" : "ML N/A"}
                            onClick={() => supportsMl && onToggleMl(strategy.id)}
                        >
                            {strategy.use_ml ? 'ML: ON' : 'ML: OFF'}
                        </span>
                        <span
                            className="ml-tag ml-tag--edit"
                            onClick={() => onEdit(strategy)}
                        >
                            EDIT ⚙️
                        </span>
                    </div>
                </div>

                <div className="strategy-item-right">
                    <button
                        className="btn-delete"
                        onClick={() => onDelete(strategy.id)}
                    >
                        ✕
                    </button>
                    <label className="switch">
                        <input
                            type="checkbox"
                            disabled={isHalted}
                            checked={isActive}
                            onChange={() => onToggle(strategy.id)}
                        />
                        <span className="slider"></span>
                    </label>
                </div>
            </div>
        </div>
    );
};
