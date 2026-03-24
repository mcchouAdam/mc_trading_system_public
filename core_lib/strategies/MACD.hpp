#pragma once
#include <map>
#include <string>
#include <vector>

#include "IStrategy.hpp"

class MACD : public IStrategy {
public:
    MACD(std::map<std::string, double> params);
    Signal on_bar(const Bar& current_bar) override;
    Signal on_position_update(const Position& pos, const Bar& current_bar) override;
    Signal on_tick(const Bar& tick) override;
    BatchResult run_batch(const MarketDataBatch& data) override;
    std::string name() const override {
        return "MACD";
    }

private:
    std::vector<double> compute_ema(const std::vector<double>& data, int period);
    Signal generate_entry_signal(const std::string& epic, SignalAction action, double close) const;

    int fast_period_;
    int slow_period_;
    int signal_period_;
    double stop_loss_percent_;
    double risk_reward_;
    double tstop_loss_percent_;

    // Stateful variables for on_bar
    int ticks_processed_ = 0;
    double fast_ema_ = 0;
    double slow_ema_ = 0;
    double signal_ema_ = 0;
    double prev_macd_ = 0;
    double prev_signal_ = 0;
    std::vector<double> history_closes_;
    std::vector<double> macd_history_;
};
