import React from 'react';

interface TableHeaderProps {
    title: string;
    pnl: number;
    count: number;
    badgeColor?: string;
    children?: React.ReactNode;
}

export const TableHeader: React.FC<TableHeaderProps> = ({
    title, pnl, count, badgeColor = '#787B86', children
}) => (
    <div className="table-header">
        <div className="table-title">
            {title}
            <div className="table-title-badges">
                <span className={`pnl-badge ${pnl >= 0 ? 'win' : 'loss'}`}>
                    {pnl.toFixed(2)}
                </span>
                <span className="badge-count" style={{ background: badgeColor, color: '#131722' }}>
                    {count}
                </span>
            </div>
        </div>
        {children}
    </div>
);
