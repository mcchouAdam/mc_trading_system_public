#pragma once
#include <string>

namespace PositionDirection {
constexpr const char* BUY = "BUY";
constexpr const char* SELL = "SELL";
}  // namespace PositionDirection

struct Position {
    std::string deal_id;
    std::string epic;
    std::string direction;
    double entry_price;
    double current_stop;
    double current_tp;
    double highest_high;
    double lowest_low;
    std::string strategy_name;
};
