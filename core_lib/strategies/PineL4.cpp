#include "PineL4.hpp"

#include <algorithm>
#include <cmath>

PineL4::PineL4(std::map<std::string, double> params) {
    // trail_percent_ is interpreted as a percentage (e.g. 1.0 = 1%)
    tstop_loss_percent_ =
        params.count(StrategyKeys::TSTOP_LOSS_PERCENT) ? params[StrategyKeys::TSTOP_LOSS_PERCENT] : 1.0;
    risk_reward_ratio_ = params.count(StrategyKeys::RISK_REWARD) ? params[StrategyKeys::RISK_REWARD] : 3.0;
    shadow_ratio_ = params.count(StrategyKeys::SHADOW_RATIO) ? params[StrategyKeys::SHADOW_RATIO] : 1.5;
}

namespace {
constexpr double SL_PADDING_PCT = 0.001;  // 0.1% for stop loss padding
constexpr double UPPER_SHADOW_MAX_PCT = 0.5;
constexpr double TSTOP_UPDATE_THRESHOLD = 1.0001;
}  // namespace

Signal PineL4::on_bar(const Bar& current_bar) {
    history_window_.push_back(current_bar);
    if (history_window_.size() > 4) {
        history_window_.pop_front();
    }

    if (history_window_.size() < 4) return {"", SignalAction::NONE, 0, 0, 0, name()};

    const Bar& current = history_window_[3];
    const Bar& prev1 = history_window_[2];
    const Bar& prev2 = history_window_[1];
    const Bar& prev3 = history_window_[0];

    // 1. Three Consecutive Red Bars (prev1, prev2, prev3)
    bool red1 = prev1.close < prev1.open;
    bool red2 = prev2.close < prev2.open;
    bool red3 = prev3.close < prev3.open;

    // 2. Lower Shadow > x Body Size on previous bar (prev1)
    double body_size = std::abs(prev1.close - prev1.open);
    double body_bottom = std::min(prev1.open, prev1.close);
    double lower_shadow = body_bottom - prev1.low;
    bool has_support = lower_shadow > shadow_ratio_ * body_size;

    // 3. Current Bar is Green
    bool current_green = current.close > current.open;

    if (red1 && red2 && red3 && has_support && current_green) {
        double stop_loss = prev1.low * (1.0 - SL_PADDING_PCT);
        double take_profit = 0;

        // If trail is disabled (~0), use fixed Risk/Reward TP
        if (tstop_loss_percent_ < 1e-6) {
            double risk = current.close - stop_loss;
            if (risk > 0 && risk_reward_ratio_ > 0) {
                take_profit = current.close + (risk * risk_reward_ratio_);
            }
        }

        return {current.epic, SignalAction::BUY, current.close, stop_loss, take_profit, name()};
    }
    return {current.epic, SignalAction::NONE, 0, 0, 0, name()};
}

Signal PineL4::on_position_update(const Position& pos, const Bar& current) {
    return process_position_update(pos, current, tstop_loss_percent_, TSTOP_UPDATE_THRESHOLD);
}

BatchResult PineL4::run_batch(const MarketDataBatch& data) {
    size_t n = data.opens.size();
    BatchResult res;
    res.entries.assign(n, false);
    res.exits.assign(n, false);
    res.short_entries.assign(n, false);
    res.short_exits.assign(n, false);
    res.exit_prices.assign(n, 0.0);
    res.stop_lines.assign(n, std::nan(""));

    if (n < 4) return res;

    bool in_pos = false;
    double entry_price = 0.0;
    double initial_stop = 0.0;
    double current_stop = std::nan("");
    double take_profit = 0.0;
    double highest_high = 0.0;

    history_window_.clear();

    for (size_t i = 0; i < n; ++i) {
        Bar b;
        b.open = data.opens[i];
        b.high = data.highs[i];
        b.low = data.lows[i];
        b.close = data.closes[i];
        b.volume = data.volumes[i];

        Signal sig = on_bar(b);

        // 1. Evaluate Exits (if holding a position)
        evaluate_long_exits(in_pos, i, b, res, tstop_loss_percent_, highest_high, current_stop, initial_stop,
                            take_profit);
        // 2. Evaluate Entries (only if NOT holding a position)
        if (!in_pos) {
            if (sig.action == SignalAction::BUY) {
                res.entries[i] = true;
                in_pos = true;
                handle_entry_signal(sig, b, initial_stop, current_stop, take_profit, highest_high);
            }
        }

        if (in_pos) {
            res.stop_lines[i] = current_stop;
        }
    }
    return res;
}

Signal PineL4::on_tick(const Bar& tick) {
    // Trailing stop logic could go here if we want sub-bar management
    return {tick.epic, SignalAction::NONE, 0, 0, 0, name()};
}
