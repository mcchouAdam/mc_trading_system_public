#pragma once
#include <deque>
#include <map>
#include <string>

#include "IStrategy.hpp"

class PineL4 : public IStrategy {
public:
    PineL4(std::map<std::string, double> params);
    Signal on_bar(const Bar& current_bar) override;
    Signal on_position_update(const Position& pos, const Bar& current_bar) override;
    Signal on_tick(const Bar& tick) override;
    BatchResult run_batch(const MarketDataBatch& data) override;
    std::string name() const override {
        return "PineL4";
    }

private:
    double tstop_loss_percent_;  // Trailing stop distance in percentage (e.g., 1.0 for 1%)
    double risk_reward_ratio_;   // Risk/Reward ratio for fixed TP if trail_percent is 0
    double shadow_ratio_;        // Lower shadow to body size ratio (e.g., 1.5)
    std::deque<Bar> history_window_;
};
