#pragma once
#include <deque>
#include <map>
#include <string>
#include <tuple>
#include <vector>

#include "IStrategy.hpp"

class YuBrokenBottom : public IStrategy {
public:
    YuBrokenBottom(std::map<std::string, double> params);

    Signal on_bar(const Bar& current_bar) override;
    Signal on_position_update(const Position& pos, const Bar& current_bar) override;
    Signal on_tick(const Bar& tick) override;
    BatchResult run_batch(const MarketDataBatch& data) override;
    std::string name() const override {
        return "YuBrokenBottom";
    }

private:
    std::tuple<double, double, double> get_candle_features(const Bar& candle);

    int lookback_period_;
    int recovery_bars_;
    int gap_bars_;
    double shadow_ratio_threshold_;
    double risk_reward_ratio_;
    double tstop_loss_percent_;
    std::deque<Bar> history_window_;
};
