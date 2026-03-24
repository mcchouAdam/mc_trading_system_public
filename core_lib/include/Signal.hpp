#pragma once
#include <string>

enum class SignalAction { NONE, BUY, SELL, UPDATE_SL, CLOSE };

struct Signal {
    std::string epic;
    SignalAction action;
    double price;
    double stop_loss;
    double take_profit;
    std::string strategy_name;
};
