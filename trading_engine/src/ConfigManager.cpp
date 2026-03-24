#include "ConfigManager.hpp"

#include <iostream>
#include <nlohmann/json.hpp>

#include "MarketDataParser.hpp"
#include "RedisKeys.hpp"
#include "StrategyFactory.hpp"

using json = nlohmann::json;

ConfigManager::ConfigManager(sw::redis::Redis* redis) : redis_(redis) {
}

std::vector<StrategyInstance> ConfigManager::load_strategies(
    std::function<void(const std::string&, const std::string&)> preload_cb) {
    std::vector<StrategyInstance> new_strategies;
    if (!redis_) return new_strategies;

    try {
        auto config_str = redis_->get(RedisKeys::ACTIVE_STRATEGIES);
        if (!config_str) return new_strategies;

        json strategies_list = json::parse(*config_str);
        if (!strategies_list.is_array()) return new_strategies;

        for (auto& item : strategies_list) {
            std::string name = item.value("name", "");
            std::string epic = item.value("epic", "");
            std::string res = item.value("resolution", "MINUTE");
            bool active = item.value("active", true);

            std::map<std::string, double> params = MarketDataParser::parse_parameters(item);
            std::unique_ptr<IStrategy> strat = StrategyFactory::instance().create(name, params);

            if (strat) {
                new_strategies.push_back({item.value("id", ""), name, epic, res, active, item.value("use_ml", false),
                                          item.value("position_size", 0.01), item.value("sizing_type", "FIXED"),
                                          std::move(strat)});
                if (active && preload_cb) {
                    preload_cb(epic, res);
                }
            }
        }
    } catch (const std::exception& e) {
        std::cerr << "[ERROR] Exception in ConfigManager::load_strategies: " << e.what() << std::endl;
    } catch (...) {
        std::cerr << "[ERROR] Unknown exception in ConfigManager::load_strategies" << std::endl;
    }
    return new_strategies;
}

std::map<std::string, Position> ConfigManager::sync_positions(
    const std::map<std::string, Position>& current_positions) {
    std::map<std::string, Position> new_positions;
    if (!redis_) return new_positions;

    try {
        auto positions_str = redis_->get(RedisKeys::CACHED_OPEN_TRADES);

        if (positions_str) {
            nlohmann::json pos_list = nlohmann::json::parse(*positions_str);
            for (auto& item : pos_list) {
                Position p = MarketDataParser::parse_position(item);

                // Maintain local tracking of extremes
                auto it = current_positions.find(p.deal_id);
                if (it != current_positions.end()) {
                    p.highest_high = it->second.highest_high;
                    p.lowest_low = it->second.lowest_low;
                } else {
                    p.highest_high = p.entry_price;
                    p.lowest_low = p.entry_price;
                }

                if (!p.deal_id.empty()) new_positions[p.deal_id] = p;
            }
        }
    } catch (const std::exception& e) {
        std::cerr << "[ERROR] Exception in ConfigManager::sync_positions: " << e.what() << std::endl;
    } catch (...) {
        std::cerr << "[ERROR] Unknown exception in ConfigManager::sync_positions" << std::endl;
    }
    return new_positions;
}
