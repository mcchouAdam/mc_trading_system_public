import { useState, useCallback } from 'react';
import { apiClient } from '../api/apiClient';
import type { StrategyInstance, AvailableStrategy, SystemConfig, NotifyFn } from '../types';

const DEFAULT_CONFIG: SystemConfig = { strategies: [], marketData: [], ohlcData: [] };

export function useSystemConfig(notify: NotifyFn) {
    const [config, setConfig] = useState<SystemConfig>(DEFAULT_CONFIG);
    const [availableStrategies, setAvailableStrategies] = useState<AvailableStrategy[]>([]);
    const [supportedEpics, setSupportedEpics] = useState<string[]>([]);

    const fetchAll = useCallback(async () => {
        try {
            const [strats, md, ohlc, avail, supp] = await Promise.all([
                apiClient.api.systemStrategiesList(),
                apiClient.api.systemSubscriptionMarketDataList(),
                apiClient.api.systemSubscriptionOhlcDataList(),
                apiClient.api.systemAvailableStrategiesList(),
                apiClient.api.systemSupportedEpicsList(),
            ]);

            setConfig({
                strategies: strats.data,
                marketData: md.data,
                ohlcData: ohlc.data,
            });
            setAvailableStrategies(avail.data);
            setSupportedEpics(supp.data);
        } catch (error) {
            console.error('Config fetch failed:', error);
        }
    }, []);

    const updateStrategies = async (newStrats: StrategyInstance[]): Promise<boolean> => {
        try {
            await apiClient.api.systemStrategiesCreate(newStrats);
            setConfig(prev => ({ ...prev, strategies: newStrats }));
            return true;
        } catch {
            notify("Error", "Failed to update strategies", "error");
            return false;
        }
    };

    const addStrategy = async (
        name: string,
        epic: string,
        resolution: string,
        params: Record<string, number>,
        size: number,
        sizingType: string
    ) => {
        const newStrat: StrategyInstance = {
            id: crypto.randomUUID(),
            name, epic, resolution,
            active: true,
            use_ml: false,
            parameters: params,
            position_size: size,
            sizing_type: sizingType,
        };
        const newStrats = [...(config.strategies || []), newStrat];

        if (await updateStrategies(newStrats)) {
            // Proactive subscription if epic not already subscribed
            if (!config.marketData.includes(epic)) {
                await apiClient.api.systemSubscriptionMarketDataCreate([...config.marketData, epic]);
            }
            fetchAll();
        }
    };

    const deleteStrategy = (id: string) => {
        updateStrategies(config.strategies.filter(s => s.id !== id));
    };

    const toggleStrategy = (id: string, field: 'active' | 'use_ml') => {
        const next = config.strategies.map(s =>
            s.id === id ? { ...s, [field]: !s[field] } : s
        );
        updateStrategies(next);
    };

    const updateParams = (
        id: string,
        params: Record<string, number>,
        size?: number,
        sizingType?: string
    ) => {
        const next = config.strategies.map(s =>
            s.id === id
                ? { ...s, parameters: params, position_size: size ?? s.position_size, sizing_type: sizingType ?? s.sizing_type }
                : s
        );
        updateStrategies(next);
    };

    return {
        config, availableStrategies, supportedEpics,
        fetchAll, addStrategy, deleteStrategy, toggleStrategy, updateParams
    };
}
