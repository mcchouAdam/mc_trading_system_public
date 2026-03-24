#pragma once
#include <cmath>
#include <optional>
#include <string>
#include <vector>

#include "Bar.hpp"
#include "BatchUtils.hpp"
#include "Position.hpp"
#include "Signal.hpp"

namespace StrategyKeys {
constexpr const char* RISK_REWARD = "RISK_REWARD";
constexpr const char* TSTOP_LOSS_PERCENT = "TSTOP_LOSS_PERCENT";
constexpr const char* LOOKBACK_PERIOD = "LOOKBACK_PERIOD";
constexpr const char* RECOVERY_BARS = "RECOVERY_BARS";
constexpr const char* SHADOW_RATIO = "SHADOW_RATIO";
constexpr const char* GAP_BARS = "GAP_BARS";
constexpr const char* FAST_PERIOD = "FAST";
constexpr const char* SLOW_PERIOD = "SLOW";
constexpr const char* SIGNAL_PERIOD = "SIGNAL";
constexpr const char* STOP_LOSS_PERCENT = "STOP_LOSS_PERCENT";
}  // namespace StrategyKeys

class IStrategy {
public:
    virtual ~IStrategy() = default;

    // Process a new bar and return a signal
    virtual Signal on_bar(const Bar& current_bar) = 0;

    // Process a current position update based on new price data
    virtual Signal on_position_update(const Position& pos, const Bar& current_bar) = 0;

    // Process a new tick and return a signal (for scalping)
    virtual Signal on_tick(const Bar& tick) = 0;

    // Batch processing for backtesting
    virtual BatchResult run_batch(const MarketDataBatch& data) = 0;

    virtual std::string name() const = 0;

protected:
    bool check_exit_condition(const Bar& b, double tstop_loss_percent, double& highest_high, double& current_sl,
                              double initial_sl, double take_profit, double& exit_price) const {
        highest_high = std::max(highest_high, b.high);

        if (tstop_loss_percent > 0) {
            double trail_stop = highest_high * (1.0 - tstop_loss_percent / 100.0);
            current_sl = std::max(initial_sl, trail_stop);
            if (b.low <= current_sl) {
                exit_price = std::min(b.open, current_sl);
                return true;
            }
        } else {
            if (b.low <= current_sl) {
                exit_price = std::min(b.open, current_sl);
                return true;
            } else if (take_profit > 0 && b.high >= take_profit) {
                exit_price = std::max(b.open, take_profit);
                return true;
            }
        }
        return false;
    }

    void handle_entry_signal(const Signal& sig, const Bar& b, double& initial_sl, double& current_sl,
                             double& take_profit, double& highest_high) const {
        initial_sl = sig.stop_loss;
        current_sl = initial_sl;
        take_profit = sig.take_profit;
        highest_high = b.high;
    }

    void handle_short_entry_signal(const Signal& sig, const Bar& b, double& initial_sl, double& current_sl,
                                   double& take_profit, double& lowest_low) const {
        initial_sl = sig.stop_loss;
        current_sl = initial_sl;
        take_profit = sig.take_profit;
        lowest_low = b.low;
    }

    bool check_short_exit_condition(const Bar& b, double tstop_loss_percent, double& lowest_low, double& current_sl,
                                    double initial_sl, double take_profit, double& exit_price) const {
        lowest_low = (lowest_low == 0) ? b.low : std::min(lowest_low, b.low);

        if (tstop_loss_percent > 0) {
            double trail_stop = lowest_low * (1.0 + tstop_loss_percent / 100.0);
            current_sl = std::min(initial_sl, trail_stop);
            if (b.high >= current_sl) {
                exit_price = std::max(b.open, current_sl);
                return true;
            }
        } else {
            if (b.high >= current_sl) {
                exit_price = std::max(b.open, current_sl);
                return true;
            } else if (take_profit > 0 && b.low <= take_profit) {
                exit_price = std::min(b.open, take_profit);
                return true;
            }
        }
        return false;
    }

    void evaluate_long_exits(bool& in_long, size_t i, const Bar& b, BatchResult& res, double tstop_loss_percent,
                             double& highest_high, double& current_sl, double initial_sl, double take_profit) const {
        if (!in_long) return;
        double exit_price = 0;
        if (check_exit_condition(b, tstop_loss_percent, highest_high, current_sl, initial_sl, take_profit,
                                 exit_price)) {
            res.exits[i] = true;
            res.exit_prices[i] = exit_price;
            in_long = false;
            current_sl = std::nan("");
        }
    }

    void evaluate_short_exits(bool& in_short, size_t i, const Bar& b, BatchResult& res, double tstop_loss_percent,
                              double& lowest_low, double& current_sl, double initial_sl, double take_profit) const {
        if (!in_short) return;
        double exit_price = 0;
        if (check_short_exit_condition(b, tstop_loss_percent, lowest_low, current_sl, initial_sl, take_profit,
                                       exit_price)) {
            res.short_exits[i] = true;
            res.exit_prices[i] = exit_price;
            in_short = false;
            current_sl = std::nan("");
        }
    }

    std::optional<Signal> evaluate_long_trailing_stop(const Position& pos, const Bar& current_bar,
                                                      double tstop_loss_percent, double& potential_stop) const {
        double highest = std::max(pos.highest_high, current_bar.high);
        double trail_stop = highest * (1.0 - tstop_loss_percent / 100.0);
        potential_stop = std::max(pos.current_stop, trail_stop);

        if (current_bar.low <= potential_stop) {
            return Signal{pos.epic, SignalAction::CLOSE, current_bar.close, 0, 0, name()};
        }
        return std::nullopt;
    }

    std::optional<Signal> evaluate_short_trailing_stop(const Position& pos, const Bar& current_bar,
                                                       double tstop_loss_percent, double& potential_stop) const {
        double lowest = (pos.lowest_low == 0) ? current_bar.low : std::min(pos.lowest_low, current_bar.low);
        double trail_stop = lowest * (1.0 + tstop_loss_percent / 100.0);
        potential_stop = (pos.current_stop == 0) ? trail_stop : std::min(pos.current_stop, trail_stop);

        if (current_bar.high >= potential_stop) {
            return Signal{pos.epic, SignalAction::CLOSE, current_bar.close, 0, 0, name()};
        }
        return std::nullopt;
    }

    Signal process_position_update(const Position& pos, const Bar& current_bar, double tstop_loss_percent,
                                   double tstop_update_threshold) const {
        if (tstop_loss_percent <= 0.0) return {pos.epic, SignalAction::NONE, 0, 0, 0, name()};

        double potential_stop = pos.current_stop;
        std::optional<Signal> close_signal = std::nullopt;

        if (pos.direction == PositionDirection::BUY) {
            close_signal = evaluate_long_trailing_stop(pos, current_bar, tstop_loss_percent, potential_stop);
        } else {
            close_signal = evaluate_short_trailing_stop(pos, current_bar, tstop_loss_percent, potential_stop);
        }

        if (close_signal.has_value()) {
            return close_signal.value();
        }

        if (std::abs(potential_stop - pos.current_stop) > pos.current_stop * tstop_update_threshold) {
            return {pos.epic, SignalAction::UPDATE_SL, current_bar.close, potential_stop, pos.current_tp, name()};
        }

        return {pos.epic, SignalAction::NONE, 0, 0, 0, name()};
    }
};
