/**
 * Centralised frontend types.
 *
 * API-contract types (OpenTrade, RiskStatus, etc.) are auto-generated in
 * api/Api.ts. This file adds *application-level* types that are not part of
 * the API schema.
 */

import type {
    OpenTrade,
    RiskStatus,
    StrategyInstance,
    AvailableStrategy,
    OhlcDataSubscription,
} from './api/Api';

// Re-export API types so the rest of the app imports from one place.
export type { OpenTrade, RiskStatus, StrategyInstance, AvailableStrategy, OhlcDataSubscription };

/** Shape of the system config aggregated by useSystemConfig. */
export interface SystemConfig {
    strategies: StrategyInstance[];
    marketData: string[];
    ohlcData: OhlcDataSubscription[];
}

/** Notify function signature, matches useNotification. */
export type NotifyFn = (
    title: string,
    message: string,
    type: 'info' | 'error' | 'confirm',
    onConfirm?: () => void
) => void;
