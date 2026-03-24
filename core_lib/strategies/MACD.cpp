#include "MACD.hpp"

#include <cmath>
#include <numeric>

MACD::MACD(std::map<std::string, double> params) {
    fast_period_ = params.count(StrategyKeys::FAST_PERIOD) ? (int)params[StrategyKeys::FAST_PERIOD] : 12;
    slow_period_ = params.count(StrategyKeys::SLOW_PERIOD) ? (int)params[StrategyKeys::SLOW_PERIOD] : 26;
    signal_period_ = params.count(StrategyKeys::SIGNAL_PERIOD) ? (int)params[StrategyKeys::SIGNAL_PERIOD] : 9;
    stop_loss_percent_ = params.count(StrategyKeys::STOP_LOSS_PERCENT) ? params[StrategyKeys::STOP_LOSS_PERCENT] : 2.0;
    risk_reward_ = params.count(StrategyKeys::RISK_REWARD) ? params[StrategyKeys::RISK_REWARD] : 2.0;
    tstop_loss_percent_ =
        params.count(StrategyKeys::TSTOP_LOSS_PERCENT) ? params[StrategyKeys::TSTOP_LOSS_PERCENT] : 0.0;
}

namespace {
constexpr double TSTOP_UPDATE_THRESHOLD = 0.0001;
}

std::vector<double> MACD::compute_ema(const std::vector<double>& data, int period) {
    std::vector<double> ema(data.size(), 0.0);
    if (data.size() < (size_t)period) return ema;

    double multiplier = 2.0 / (period + 1);

    double sum = std::accumulate(data.begin(), data.begin() + period, 0.0);
    ema[period - 1] = sum / period;

    for (size_t i = period; i < data.size(); ++i) {
        ema[i] = (data[i] - ema[i - 1]) * multiplier + ema[i - 1];
    }
    return ema;
}

Signal MACD::generate_entry_signal(const std::string& epic, SignalAction action, double close) const {
    double sl = 0;
    double tp = 0;
    if (stop_loss_percent_ > 0) {
        if (action == SignalAction::BUY) {
            sl = std::round(close * (1.0 - stop_loss_percent_ / 100.0) * 100.0) / 100.0;
            if (risk_reward_ > 0) {
                tp = std::round(close * (1.0 + (stop_loss_percent_ * risk_reward_) / 100.0) * 100.0) / 100.0;
            }
        } else if (action == SignalAction::SELL) {
            sl = std::round(close * (1.0 + stop_loss_percent_ / 100.0) * 100.0) / 100.0;
            if (risk_reward_ > 0) {
                tp = std::round(close * (1.0 - (stop_loss_percent_ * risk_reward_) / 100.0) * 100.0) / 100.0;
            }
        }
    }
    return {epic, action, close, sl, tp, name()};
}

Signal MACD::on_bar(const Bar& current_bar) {
    double close = current_bar.close;
    history_closes_.push_back(close);
    ticks_processed_++;

    if (ticks_processed_ == fast_period_) {
        double sum = std::accumulate(history_closes_.begin(), history_closes_.begin() + fast_period_, 0.0);
        fast_ema_ = sum / fast_period_;
    } else if (ticks_processed_ > fast_period_) {
        fast_ema_ = (close - fast_ema_) * (2.0 / (fast_period_ + 1)) + fast_ema_;
    }

    if (ticks_processed_ == slow_period_) {
        double sum = std::accumulate(history_closes_.begin() + (ticks_processed_ - slow_period_),
                                     history_closes_.begin() + ticks_processed_, 0.0);
        slow_ema_ = sum / slow_period_;
    } else if (ticks_processed_ > slow_period_) {
        slow_ema_ = (close - slow_ema_) * (2.0 / (slow_period_ + 1)) + slow_ema_;
    }

    if (ticks_processed_ >= slow_period_) {
        double current_macd = fast_ema_ - slow_ema_;
        macd_history_.push_back(current_macd);

        int signal_start_tick = slow_period_ + signal_period_ - 1;

        if (ticks_processed_ == signal_start_tick) {
            double sum = std::accumulate(macd_history_.begin(), macd_history_.begin() + signal_period_, 0.0);
            signal_ema_ = sum / signal_period_;
            prev_macd_ = current_macd;
            prev_signal_ = signal_ema_;
        } else if (ticks_processed_ > signal_start_tick) {
            signal_ema_ = (current_macd - signal_ema_) * (2.0 / (signal_period_ + 1)) + signal_ema_;

            bool buy_signal = (prev_macd_ <= prev_signal_ && current_macd > signal_ema_);
            bool sell_signal = (prev_macd_ >= prev_signal_ && current_macd < signal_ema_);

            prev_macd_ = current_macd;
            prev_signal_ = signal_ema_;

            if (buy_signal) {
                return generate_entry_signal(current_bar.epic, SignalAction::BUY, close);
            } else if (sell_signal) {
                return generate_entry_signal(current_bar.epic, SignalAction::SELL, close);
            }
        }
    }

    return {current_bar.epic, SignalAction::NONE, 0, 0, 0, name()};
}

Signal MACD::on_position_update(const Position& pos, const Bar& current_bar) {
    return process_position_update(pos, current_bar, tstop_loss_percent_, TSTOP_UPDATE_THRESHOLD);
}

BatchResult MACD::run_batch(const MarketDataBatch& data) {
    size_t n = data.opens.size();
    BatchResult res;
    res.entries.assign(n, false);
    res.exits.assign(n, false);
    res.short_entries.assign(n, false);
    res.short_exits.assign(n, false);
    res.exit_prices.assign(n, 0.0);
    res.stop_lines.assign(n, std::nan(""));

    if (n < (size_t)(slow_period_ + signal_period_)) return res;

    auto fast_ema = compute_ema(data.closes, fast_period_);
    auto slow_ema = compute_ema(data.closes, slow_period_);

    std::vector<double> macd_line(n);
    for (size_t i = 0; i < n; ++i) {
        macd_line[i] = fast_ema[i] - slow_ema[i];
    }

    auto signal_line = compute_ema(macd_line, signal_period_);

    bool in_long = false;
    bool in_short = false;
    double current_sl = std::nan("");
    double initial_sl = 0;
    double take_profit = 0;
    double highest_high = 0;
    double lowest_low = 0;

    for (size_t i = 1; i < n; ++i) {
        Bar b;
        b.open = data.opens[i];
        b.high = data.highs[i];
        b.low = data.lows[i];
        b.close = data.closes[i];
        b.volume = data.volumes[i];

        // 1. Evaluate Exits if in position
        evaluate_long_exits(in_long, i, b, res, tstop_loss_percent_, highest_high, current_sl, initial_sl, take_profit);
        evaluate_short_exits(in_short, i, b, res, tstop_loss_percent_, lowest_low, current_sl, initial_sl, take_profit);

        // 2. Evaluate Entry Signals (Golden Cross / Death Cross)
        bool buy_signal = (macd_line[i - 1] <= signal_line[i - 1] && macd_line[i] > signal_line[i]);
        bool sell_signal = (macd_line[i - 1] >= signal_line[i - 1] && macd_line[i] < signal_line[i]);

        if (buy_signal) {
            if (in_short) {
                res.short_exits[i] = true;
                res.exit_prices[i] = data.closes[i];
                in_short = false;
            }
            if (!in_long) {
                res.entries[i] = true;
                in_long = true;
                Signal sig = generate_entry_signal("", SignalAction::BUY, data.closes[i]);
                handle_entry_signal(sig, b, initial_sl, current_sl, take_profit, highest_high);
            }
        } else if (sell_signal) {
            if (in_long) {
                res.exits[i] = true;
                res.exit_prices[i] = data.closes[i];
                in_long = false;
            }
            if (!in_short) {
                res.short_entries[i] = true;
                in_short = true;
                Signal sig = generate_entry_signal("", SignalAction::SELL, data.closes[i]);
                handle_short_entry_signal(sig, b, initial_sl, current_sl, take_profit, lowest_low);
            }
        }

        // Record stop loss line
        if (in_long || in_short) {
            res.stop_lines[i] = current_sl;
        } else {
            res.stop_lines[i] = std::nan("");
        }
    }
    return res;
}

Signal MACD::on_tick(const Bar& tick) {
    return {tick.epic, SignalAction::NONE, 0, 0, 0, name()};
}
