#pragma once

namespace RedisKeys {
constexpr const char* CH_STRATEGY_UPDATED = "CHANNEL_STRATEGY_UPDATED";
constexpr const char* CH_CONFIG_UPDATED = "CHANNEL_CONFIG_UPDATED";
constexpr const char* CH_POSITIONS_UPDATED = "CHANNEL_POSITIONS_UPDATED";
constexpr const char* CH_HISTORY_REQ = "CHANNEL_HISTORY_REQUEST";
constexpr const char* PREFIX_HISTORY_RESP = "HISTORY_RESPONSE:";

constexpr const char* ACTIVE_STRATEGIES = "ACTIVE_STRATEGIES";
constexpr const char* CACHED_OPEN_TRADES = "CACHED_OPEN_TRADES";
constexpr const char* TRADE_SIGNALS = "TRADE_SIGNALS";
}  // namespace RedisKeys
