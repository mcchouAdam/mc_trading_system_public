#pragma once

#include <nlohmann/json.hpp>
#include <string>

#include "Bar.hpp"
#include "Signal.hpp"
#include "StrategyInstance.hpp"

class MarketDataParser {
public:
    static Bar parse_realtime_tick(const std::string& epic, const nlohmann::json& data);
    static Bar parse_realtime_bar(const std::string& epic, const std::string& res, const nlohmann::json& data);
    static Bar parse_history_bar(const std::string& epic, const std::string& res, const nlohmann::json& row);
    static Position parse_position(const nlohmann::json& item);
    static std::map<std::string, double> parse_parameters(const nlohmann::json& item);

    // Serialization
    static nlohmann::json serialize_position_update(const std::string& deal_id, const std::string& epic,
                                                    const Signal& sig, const std::string& strategy_name,
                                                    const std::string& source);
    static nlohmann::json serialize_trade_signal(const Signal& sig, const StrategyInstance& s,
                                                 const std::string& resolution);
};
