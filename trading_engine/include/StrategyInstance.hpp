#pragma once
#include <memory>
#include <string>

#include "IStrategy.hpp"

struct StrategyInstance {
    std::string id;
    std::string name;
    std::string epic;
    std::string resolution;
    bool active;
    bool use_ml;
    double position_size;
    std::string sizing_type;
    std::unique_ptr<IStrategy> strategy;
};
