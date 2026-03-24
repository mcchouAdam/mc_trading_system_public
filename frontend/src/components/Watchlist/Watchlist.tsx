import React, { useState } from 'react';
import { Modal } from '../Common/Modal';
import { EpicsList } from './EpicsList';
import { StrategyItem } from './StrategyItem';
import { StrategyForm } from './StrategyForm';
import './Watchlist.css';

interface WatchlistProps {
    activeEpics: string[];
    currentEpic: string;
    onSelectEpic: (epic: string) => void;
    sidebarSplit: number;
    onMouseDownV: (e: React.MouseEvent) => void;
    systemConfig: any;
    onToggleStrategy: (id: string) => void;
    isHalted: boolean;
    availableStrategies: any[];
    supportedEpics: string[];
    onAddStrategy: (name: string, epic: string, res: string, params: any, size: number, sizingType: string) => void;
    onDeleteStrategy: (id: string) => void;
    onUpdateStrategyParams: (id: string, params: any, size: number, sizingType: string) => void;
    onToggleStrategyMl: (id: string) => void;
    width?: string;
    activeResizer?: string | null;
}

export const Watchlist: React.FC<WatchlistProps> = ({
    activeEpics, currentEpic, onSelectEpic, sidebarSplit, onMouseDownV,
    systemConfig, onToggleStrategy, isHalted, availableStrategies, supportedEpics,
    onAddStrategy, onDeleteStrategy, onUpdateStrategyParams, onToggleStrategyMl,
    width, activeResizer
}) => {
    const [isFormOpen, setIsFormOpen] = useState(false);
    const [modalMode, setModalMode] = useState<'add' | 'edit'>('add');
    const [editData, setEditData] = useState<any>(null);

    const handleAdd = () => {
        const firstStrat = availableStrategies[0];
        setModalMode('add');
        setEditData({
            name: firstStrat?.name || '',
            epic: supportedEpics[0] || '',
            resolution: 'MINUTE_5',
            params: { ...(firstStrat?.default_parameters || {}) },
            size: firstStrat?.default_position_size ?? 0.01,
            sizingType: firstStrat?.default_sizing_type ?? 'FIXED'
        });
        setIsFormOpen(true);
    };

    const handleEdit = (s: any) => {
        setModalMode('edit');
        setEditData({
            id: s.id,
            name: s.name,
            epic: s.epic,
            resolution: s.resolution,
            params: { ...s.parameters },
            size: s.position_size ?? 0.01,
            sizingType: s.sizing_type ?? 'FIXED'
        });
        setIsFormOpen(true);
    };

    const handleSave = (data: any) => {
        if (modalMode === 'add') {
            onAddStrategy(data.name, data.epic, data.resolution, data.params, data.size, data.sizingType);
        } else {
            onUpdateStrategyParams(editData.id, data.params, data.size, data.sizingType);
        }
        setIsFormOpen(false);
    };

    return (
        <div className="watchlist-pane" style={{ width }}>
            {/* Top: Epics List */}
            <EpicsList
                epics={activeEpics}
                current={currentEpic}
                onSelect={onSelectEpic}
                heightPercent={sidebarSplit}
            />

            {/* Splitter */}
            <div className={`v-splitter ${activeResizer === 'sidebar-v' ? 'active' : ''}`} onMouseDown={onMouseDownV} />

            {/* Bottom: Strategy List */}
            <div style={{
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
                minHeight: 0,
                overflow: 'hidden'
            }}>
                <div className="watch-section-header">
                    <span>Active Strategies</span>
                    <button
                        className="search-btn"
                        onClick={handleAdd}
                    >
                        + ADD
                    </button>
                </div>

                <div className="strategy-list-container" style={{ flex: 1, overflowY: 'auto' }}>
                    {systemConfig?.strategies?.map((s: any) => (
                        <StrategyItem
                            key={s.id}
                            strategy={s}
                            isHalted={isHalted}
                            supportsMl={availableStrategies.find(x => x.name === s.name)?.supports_ml}
                            onToggle={onToggleStrategy}
                            onToggleMl={onToggleStrategyMl}
                            onDelete={onDeleteStrategy}
                            onEdit={handleEdit}
                            onSelectEpic={onSelectEpic}
                        />
                    ))}
                </div>
            </div>

            {/* Common Modal for Settings */}
            <Modal
                isOpen={isFormOpen}
                title={modalMode === 'add' ? 'Add Strategy Target' : `Settings: ${editData?.name}`}
                onClose={() => setIsFormOpen(false)}
            >
                {editData && (
                    <StrategyForm
                        mode={modalMode}
                        initialValues={editData}
                        availableStrategies={availableStrategies}
                        supportedEpics={supportedEpics}
                        onSave={handleSave}
                    />
                )}
            </Modal>
        </div>
    );
};
