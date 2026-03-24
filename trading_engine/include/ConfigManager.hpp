#pragma once

#include <sw/redis++/redis++.h>

#include <functional>
#include <map>
#include <string>
#include <vector>

#include "Position.hpp"
#include "StrategyInstance.hpp"

class ConfigManager {
public:
    ConfigManager(sw::redis::Redis* redis);

    // Returns a new list of strategies.
    // Triggers preload_cb for each active strategy.
    std::vector<StrategyInstance> load_strategies(
        std::function<void(const std::string&, const std::string&)> preload_cb);

    // Syncs positions from Redis, preserving local extreme prices from current_positions.
    std::map<std::string, Position> sync_positions(const std::map<std::string, Position>& current_positions);

private:
    sw::redis::Redis* redis_;
};
