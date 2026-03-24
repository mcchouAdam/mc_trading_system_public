import React from 'react';

interface EpicsListProps {
    epics: string[];
    current: string;
    onSelect: (epic: string) => void;
    heightPercent: number;
}

export const EpicsList: React.FC<EpicsListProps> = ({ epics, current, onSelect, heightPercent }) => {
    return (
        <div style={{ height: `${heightPercent}%`, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            <div className="watch-section-header">Epics</div>
            <div style={{ flex: 1, overflowY: 'auto' }}>
                {epics.map(item => (
                    <div
                        key={item}
                        className={`epic-item ${current === item ? 'active' : ''}`}
                        onClick={() => onSelect(item)}
                    >
                        <span>{item}</span>
                        {current === item && <span className="live-badge">LIVE</span>}
                    </div>
                ))}
            </div>
        </div>
    );
};
