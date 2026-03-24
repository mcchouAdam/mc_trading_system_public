import React, { useState } from 'react';
import '../Watchlist/Watchlist.css';

interface StrategyFormProps {
    mode: 'add' | 'edit';
    initialValues: {
        name: string;
        epic: string;
        resolution: string;
        params: any;
        size: number;
        sizingType: string;
    };
    availableStrategies: any[];
    supportedEpics: string[];
    onSave: (data: any) => void;
}

export const StrategyForm: React.FC<StrategyFormProps> = ({
    mode, initialValues, availableStrategies, supportedEpics, onSave
}) => {
    const [name, setName] = useState(initialValues.name);
    const [epic, setEpic] = useState(initialValues.epic);
    const [res, setRes] = useState(initialValues.resolution);
    const [params, setParams] = useState(initialValues.params);
    const [size, setSize] = useState(initialValues.size);
    const [sizingType, setSizingType] = useState(initialValues.sizingType);

    const resOptions = [
        { label: 'm1', value: 'MINUTE' }, { label: 'm5', value: 'MINUTE_5' },
        { label: 'm15', value: 'MINUTE_15' }, { label: 'h1', value: 'HOUR' },
        { label: 'h4', value: 'HOUR_4' }, { label: 'D1', value: 'DAY' }
    ];

    const handleSubmit = () => {
        onSave({ name, epic, resolution: res, params, size, sizingType });
    };

    return (
        <div className="strategy-form">
            {mode === 'add' && (
                <>
                    <div className="form-group">
                        <label className="form-label">Strategy Type</label>
                        <select
                            className="form-select"
                            value={name}
                            onChange={e => {
                                setName(e.target.value);
                                const s = availableStrategies.find(x => x.name === e.target.value);
                                if (s) setParams({ ...s.default_parameters });
                            }}
                        >
                            {availableStrategies.map(s => <option key={s.name} value={s.name}>{s.name}</option>)}
                        </select>
                    </div>
                    <div className="form-row">
                        <div className="form-group">
                            <label className="form-label">Epic</label>
                            <select className="form-select" value={epic} onChange={e => setEpic(e.target.value)}>
                                {supportedEpics.map(ep => <option key={ep} value={ep}>{ep}</option>)}
                            </select>
                        </div>
                        <div className="form-group">
                            <label className="form-label">Resolution</label>
                            <select className="form-select" value={res} onChange={e => setRes(e.target.value)}>
                                {resOptions.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
                            </select>
                        </div>
                    </div>
                </>
            )}

            <div className="form-row">
                <div className="form-group">
                    <label className="form-label">Size</label>
                    <input className="form-input" type="number" step="0.01" value={size} onChange={e => setSize(parseFloat(e.target.value))} />
                </div>
                <div className="form-group">
                    <label className="form-label">Sizing Method</label>
                    <select className="form-select" value={sizingType} onChange={e => setSizingType(e.target.value)}>
                        <option value="FIXED">FIXED (Units)</option>
                        <option value="RISK">RISK (%)</option>
                    </select>
                </div>
            </div>

            <div className="params-section">
                <label className="form-label">Risk & Strategy Parameters</label>
                {Object.entries(params).map(([key, val]: [string, any]) => (
                    <div key={key} className="param-row">
                        <span className="param-key">{key}</span>
                        <input
                            className="form-input param-input"
                            type="number"
                            value={val}
                            onChange={e => setParams({ ...params, [key]: parseFloat(e.target.value) })}
                        />
                    </div>
                ))}
            </div>

            <button className="btn-form-submit" onClick={handleSubmit}>
                UPDATE
            </button>
        </div>
    );
};
