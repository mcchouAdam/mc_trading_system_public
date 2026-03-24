#include "YuBrokenBottom.hpp"

#include <algorithm>
#include <cmath>
#include <limits>

YuBrokenBottom::YuBrokenBottom(std::map<std::string, double> params) {
    lookback_period_ = params.count(StrategyKeys::LOOKBACK_PERIOD) ? (int)params[StrategyKeys::LOOKBACK_PERIOD] : 20;
    recovery_bars_ = params.count(StrategyKeys::RECOVERY_BARS) ? (int)params[StrategyKeys::RECOVERY_BARS] : 3;
    gap_bars_ = params.count(StrategyKeys::GAP_BARS) ? (int)params[StrategyKeys::GAP_BARS] : 5;
    shadow_ratio_threshold_ = params.count(StrategyKeys::SHADOW_RATIO) ? params[StrategyKeys::SHADOW_RATIO] : 0.6;
    risk_reward_ratio_ = params.count(StrategyKeys::RISK_REWARD) ? params[StrategyKeys::RISK_REWARD] : 5.0;
    tstop_loss_percent_ =
        params.count(StrategyKeys::TSTOP_LOSS_PERCENT) ? params[StrategyKeys::TSTOP_LOSS_PERCENT] : 0.0;
}

namespace {
constexpr double SL_PADDING_PCT = 0.0002;
constexpr double TSTOP_UPDATE_THRESHOLD = 1.0001;
}  // namespace

std::tuple<double, double, double> YuBrokenBottom::get_candle_features(const Bar& candle) {
    double body_top = std::max(candle.open, candle.close);
    double body_bottom = std::min(candle.open, candle.close);
    double bar_height = candle.high - candle.low;

    if (bar_height <= 0.0000001) return {0, 0, 0};

    double lower_shadow = body_bottom - candle.low;
    double upper_shadow = candle.high - body_top;
    double body_size = body_top - body_bottom;

    return {lower_shadow / bar_height, upper_shadow / bar_height, body_size / bar_height};
}

Signal YuBrokenBottom::on_bar(const Bar& current_bar) {
    history_window_.push_back(current_bar);
    if (history_window_.size() > (size_t)lookback_period_) {
        history_window_.pop_front();
    }

    if (history_window_.size() < (size_t)lookback_period_) return {"", SignalAction::NONE, 0, 0, 0, name()};

    const Bar& current = history_window_.back();

    // 1. Search for support level in lookback range (excluding the gap_bars_)
    auto support_it = std::min_element(history_window_.end() - lookback_period_, history_window_.end() - gap_bars_,
                                       [](const Bar& a, const Bar& b) { return a.low < b.low; });
    double support_level = support_it->low;

    // 2. Check for fake breakout in recent window
    auto fake_out_it = std::min_element(history_window_.end() - recovery_bars_, history_window_.end(),
                                        [](const Bar& a, const Bar& b) { return a.low < b.low; });
    double best_fake_out_low = fake_out_it->low;

    bool has_broken = best_fake_out_low < support_level;
    bool is_recovered = current.close > support_level;

    auto [lower_ratio, upper_ratio, body_ratio] = get_candle_features(current);
    bool is_pointed = lower_ratio >= shadow_ratio_threshold_;

    if (has_broken && is_recovered && is_pointed) {
        double stop_loss = best_fake_out_low - (support_level * SL_PADDING_PCT);
        double risk = std::abs(current.close - stop_loss);
        double take_profit = (risk_reward_ratio_ > 0) ? current.close + (risk * risk_reward_ratio_) : 0;
        return {current.epic, SignalAction::BUY, current.close, stop_loss, take_profit, name()};
    }
    return {current.epic, SignalAction::NONE, 0, 0, 0, name()};
}

Signal YuBrokenBottom::on_position_update(const Position& pos, const Bar& current_bar) {
    return process_position_update(pos, current_bar, tstop_loss_percent_, TSTOP_UPDATE_THRESHOLD);
}

BatchResult YuBrokenBottom::run_batch(const MarketDataBatch& data) {
    size_t n = data.opens.size();
    BatchResult res;
    res.entries.assign(n, false);
    res.exits.assign(n, false);
    res.short_entries.assign(n, false);
    res.short_exits.assign(n, false);
    res.exit_prices.assign(n, 0.0);
    res.stop_lines.assign(n, std::nan(""));

    if (n < (size_t)lookback_period_) return res;

    history_window_.clear();

    bool in_position = false;
    double current_sl = std::nan("");
    double initial_sl = 0;
    double take_profit = 0;
    double highest_high = 0;

    for (size_t i = 0; i < n; ++i) {
        Bar b;
        b.open = data.opens[i];
        b.high = data.highs[i];
        b.low = data.lows[i];
        b.close = data.closes[i];
        b.volume = data.volumes[i];

        Signal sig = on_bar(b);

        // 1. Evaluate Exits (if holding a position)
        evaluate_long_exits(in_position, i, b, res, tstop_loss_percent_, highest_high, current_sl, initial_sl,
                            take_profit);
        // 2. Evaluate Entries (only if NOT holding a position)
        if (!in_position && history_window_.size() >= (size_t)lookback_period_) {
            if (sig.action == SignalAction::BUY) {
                res.entries[i] = true;
                in_position = true;
                handle_entry_signal(sig, b, initial_sl, current_sl, take_profit, highest_high);
            }
        }

        // 3. Record tracking metrics
        if (in_position) {
            res.stop_lines[i] = current_sl;
        }
    }
    return res;
}

Signal YuBrokenBottom::on_tick(const Bar& tick) {
    // Basic implementation; can be extended for intra-bar management
    return {tick.epic, SignalAction::NONE, 0, 0, 0, name()};
}
