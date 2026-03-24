#include "EngineCore.hpp"

#include <iostream>
#include <nlohmann/json.hpp>
#include <thread>

using json = nlohmann::json;

EngineCore::EngineCore()
    : context_(1),
      tick_subscriber_(context_, zmq::socket_type::sub),
      ohlc_subscriber_(context_, zmq::socket_type::sub) {
    const char* zmq_host_env = std::getenv("ZMQ_HOST");
    zmq_host_ = (zmq_host_env != nullptr) ? zmq_host_env : "127.0.0.1";

    const char* zmq_tick_port_env = std::getenv("ZMQ_TICK_PORT");
    zmq_tick_port_ = (zmq_tick_port_env != nullptr) ? zmq_tick_port_env : "5555";

    const char* zmq_ohlc_port_env = std::getenv("ZMQ_OHLC_PORT");
    zmq_ohlc_port_ = (zmq_ohlc_port_env != nullptr) ? zmq_ohlc_port_env : "5556";

    const char* redis_host_env = std::getenv("REDIS_HOST");
    std::string redis_host = (redis_host_env != nullptr) ? redis_host_env : "127.0.0.1";

    const char* redis_port_env = std::getenv("REDIS_PORT");
    int redis_port = (redis_port_env != nullptr) ? std::stoi(redis_port_env) : 6379;

    const char* redis_pass_env = std::getenv("REDIS_PASSWORD");
    std::string redis_pass = (redis_pass_env != nullptr) ? redis_pass_env : "";

    // Tick Subscriber
    tick_subscriber_.set(zmq::sockopt::rcvhwm, EngineConstants::ZMQ_TICK_HWM);
    tick_subscriber_.connect("tcp://" + zmq_host_ + ":" + zmq_tick_port_);
    tick_subscriber_.set(zmq::sockopt::subscribe, EngineConstants::ZMQ_TOPIC_PRICE);

    // OHLC Subscriber
    ohlc_subscriber_.set(zmq::sockopt::rcvhwm, EngineConstants::ZMQ_OHLC_HWM);
    ohlc_subscriber_.connect("tcp://" + zmq_host_ + ":" + zmq_ohlc_port_);
    ohlc_subscriber_.set(zmq::sockopt::subscribe, EngineConstants::ZMQ_TOPIC_PRICE);

    std::cout << "[INFO] Connected to ZMQ:" << zmq_tick_port_ << " and ZMQ:" << zmq_ohlc_port_ << std::endl;

    try {
        sw::redis::ConnectionOptions opts;
        opts.host = redis_host;
        opts.port = redis_port;
        if (!redis_pass.empty()) opts.password = redis_pass;
        redis_ = std::make_unique<sw::redis::Redis>(opts);
        config_manager_ = std::make_unique<ConfigManager>(redis_.get());
        history_preloader_ = std::make_unique<HistoryPreloader>(redis_.get());

        redis_sub_ = std::make_unique<sw::redis::Subscriber>(redis_->subscriber());
        redis_sub_->on_message([this](std::string channel, std::string msg) {
            if (channel == RedisKeys::CH_STRATEGY_UPDATED || channel == RedisKeys::CH_CONFIG_UPDATED) {
                config_dirty_ = true;
            } else if (channel == RedisKeys::CH_POSITIONS_UPDATED) {
                positions_dirty_ = true;
            }
        });
        redis_sub_->subscribe(RedisKeys::CH_STRATEGY_UPDATED);
        redis_sub_->subscribe(RedisKeys::CH_CONFIG_UPDATED);
        redis_sub_->subscribe(RedisKeys::CH_POSITIONS_UPDATED);

        redis_thread_ = std::thread([this]() {
            while (is_running_) {
                try {
                    if (redis_sub_)
                        redis_sub_->consume();
                    else
                        std::this_thread::sleep_for(std::chrono::milliseconds(EngineConstants::REDIS_IDLE_WAIT_MS));
                } catch (...) {
                    std::this_thread::sleep_for(std::chrono::milliseconds(EngineConstants::REDIS_ERROR_WAIT_MS));
                }
            }
        });
        if (config_dirty_) {
            auto strategies = config_manager_->load_strategies([this](const std::string& epic, const std::string& res) {
                history_preloader_->preload(
                    epic, res, [this, epic, res]() { return is_history_empty(epic, res); },
                    [this, epic, res](const std::deque<Bar>& bars) { on_history_loaded(epic, res, bars); });
            });
            std::lock_guard<std::mutex> lock(strategies_mutex_);
            active_strategies_ = std::move(strategies);
            config_dirty_ = false;
        }
    } catch (const std::exception& e) {
        std::cerr << "[ERROR] Redis failure: " << e.what() << std::endl;
    }
}

EngineCore::~EngineCore() {
    is_running_ = false;
    if (redis_thread_.joinable()) redis_thread_.join();
}

void EngineCore::run_config_loop() {
    if (config_dirty_ && config_manager_) {
        auto strategies = config_manager_->load_strategies([this](const std::string& epic, const std::string& res) {
            history_preloader_->preload(
                epic, res, [this, epic, res]() { return is_history_empty(epic, res); },
                [this, epic, res](const std::deque<Bar>& bars) { on_history_loaded(epic, res, bars); });
        });
        std::lock_guard<std::mutex> lock(strategies_mutex_);
        active_strategies_ = std::move(strategies);
        config_dirty_ = false;
    }

    if (positions_dirty_ && config_manager_) {
        std::map<std::string, Position> current_positions;
        {
            std::lock_guard<std::mutex> lock(positions_mutex_);
            current_positions = active_positions_;
        }
        auto new_positions = config_manager_->sync_positions(current_positions);
        {
            std::lock_guard<std::mutex> lock(positions_mutex_);
            active_positions_ = std::move(new_positions);
            positions_dirty_ = false;
        }
    }
}

bool EngineCore::is_history_empty(const std::string& epic, const std::string& res) {
    std::lock_guard<std::mutex> lock(history_mutex_);
    return market_history_[epic][res].empty();
}

void EngineCore::on_history_loaded(const std::string& epic, const std::string& res, const std::deque<Bar>& bars) {
    {
        std::lock_guard<std::mutex> lock(history_mutex_);
        market_history_[epic][res] = bars;
    }
    {
        std::lock_guard<std::mutex> s_lock(strategies_mutex_);
        for (auto& s : active_strategies_) {
            if (s.active && s.epic == epic && s.resolution == res) {
                for (const auto& b : bars) {
                    s.strategy->on_bar(b);
                }
            }
        }
    }
}

void EngineCore::run() {
    std::cerr << "[DEBUG] ZMQ Run loop started. Host: " << zmq_host_ << std::endl;

    zmq::pollitem_t items[] = {{static_cast<void*>(tick_subscriber_), 0, (short)ZMQ_POLLIN, 0},
                               {static_cast<void*>(ohlc_subscriber_), 0, (short)ZMQ_POLLIN, 0}};

    int loop_counter = 0;
    while (is_running_) {
        try {
            run_config_loop();

            int poll_result = zmq::poll(&items[0], 2, std::chrono::milliseconds(EngineConstants::ZMQ_POLL_TIMEOUT_MS));

            if (poll_result > 0) {
                process_zmq_events(items, 2);
            }
        } catch (const std::exception& e) {
            std::cerr << "[CRITICAL] Exception in poll loop: " << e.what() << std::endl;
            std::this_thread::sleep_for(std::chrono::milliseconds(EngineConstants::ZMQ_ERROR_WAIT_MS));
        } catch (...) {
            std::cerr << "[CRITICAL] Unknown exception in poll loop!" << std::endl;
            std::this_thread::sleep_for(std::chrono::milliseconds(EngineConstants::ZMQ_ERROR_WAIT_MS));
        }
    }
}

void EngineCore::process_zmq_events(zmq::pollitem_t* items, int count) {
    for (int i = count - 1; i >= 0; --i) {
        if (items[i].revents & ZMQ_POLLIN) {
            zmq::message_t topic_msg, payload_msg;
            auto& socket = (i == 0 ? tick_subscriber_ : ohlc_subscriber_);

            // Read multi-part message: [Topic, Payload]
            if (socket.recv(topic_msg, zmq::recv_flags::dontwait)) {
                if (socket.recv(payload_msg, zmq::recv_flags::none)) {
                    handle_market_data(std::string(static_cast<char*>(topic_msg.data()), topic_msg.size()),
                                       std::string(static_cast<char*>(payload_msg.data()), payload_msg.size()));
                }
            }
        }
    }
}

void EngineCore::handle_market_data(const std::string& topic, const std::string& payload) {
    try {
        json d = json::parse(payload);
        size_t l_col = topic.find_last_of(EngineConstants::ZMQ_TOPIC_SEPARATOR);
        size_t f_col = topic.find(EngineConstants::ZMQ_TOPIC_SEPARATOR);
        if (l_col == std::string::npos || f_col == std::string::npos || l_col <= f_col) return;

        std::string res = topic.substr(l_col + 1);
        std::string epic = topic.substr(f_col + 1, l_col - f_col - 1);

        if (res == EngineConstants::RESOLUTION_TICK) {
            Bar tick = MarketDataParser::parse_realtime_tick(epic, d);
            process_tick(tick);
        } else {
            Bar bar = MarketDataParser::parse_realtime_bar(epic, res, d);
            process_bar(bar);
        }
    } catch (const std::exception& e) {
        std::cerr << "[ERROR] JSON parse error in handle_market_data: " << e.what() << " | Topic: " << topic
                  << std::endl;
    } catch (...) {
        std::cerr << "[ERROR] Unknown error in handle_market_data" << std::endl;
    }
}

void EngineCore::process_tick(const Bar& tick) {
    tick_count_++;

    std::lock_guard<std::mutex> lock(strategies_mutex_);
    for (auto& s : active_strategies_) {
        if (!s.active || s.epic != tick.epic) continue;
        Signal sig = s.strategy->on_tick(tick);
        if (sig.action != SignalAction::NONE && redis_) {
            json sj = MarketDataParser::serialize_trade_signal(sig, s, EngineConstants::RESOLUTION_TICK);
            redis_->publish(RedisKeys::TRADE_SIGNALS, sj.dump());
        }
    }

    // Continuous Position Monitoring (Trailing Stop / Intraday Exit)
    {
        std::lock_guard<std::mutex> p_lock(positions_mutex_);
        for (auto& [deal_id, pos] : active_positions_) {
            if (pos.epic != tick.epic) continue;

            // 1. Update extreme prices
            pos.highest_high = std::max(pos.highest_high, tick.close);
            pos.lowest_low = (pos.lowest_low == 0) ? tick.close : std::min(pos.lowest_low, tick.close);

            // 2. Ask the strategy if we should move SL or Close
            for (auto& s : active_strategies_) {
                if (s.name == pos.strategy_name && s.active) {
                    Signal sig = s.strategy->on_position_update(pos, tick);
                    if (sig.action != SignalAction::NONE) {
                        json sj = MarketDataParser::serialize_position_update(
                            deal_id, tick.epic, sig, s.name, EngineConstants::SIGNAL_SOURCE_AUTO_TRAIL_TICK);
                        redis_->publish(RedisKeys::TRADE_SIGNALS, sj.dump());

                        // Local update to avoid redundant signals before next sync
                        if (sig.action == SignalAction::UPDATE_SL) {
                            pos.current_stop = sig.stop_loss;
                        }
                    }
                    break;
                }
            }
        }
    }
}

void EngineCore::process_bar(const Bar& bar) {
    if (bar.timestamp == 0) return;  // Ignore invalid bars

    bool is_new_bar = false;
    {
        std::lock_guard<std::mutex> h_lock(history_mutex_);
        auto& history = market_history_[bar.epic][bar.resolution];
        if (!history.empty() && history.back().timestamp == bar.timestamp) {
            history.back().close = bar.close;
            history.back().high = std::max(history.back().high, bar.high);
            history.back().low = std::min(history.back().low, bar.low);
        } else {
            // This is a new bar for a new timestamp
            history.push_back(bar);
            if (history.size() > EngineConstants::MAX_HISTORY_SIZE) history.pop_front();
            is_new_bar = true;
        }
    }

    // Only trigger strategies on the FIRST message of a new bar to avoid duplicate entries
    if (!is_new_bar) return;

    std::cout << "[MARKET] New Bar: " << bar.epic << " [" << bar.resolution << "] @ " << bar.close << std::endl;

    // Use a copy of history to trigger strategies safely outside history_mutex
    std::deque<Bar> history_copy;
    {
        std::lock_guard<std::mutex> h_lock(history_mutex_);
        history_copy = market_history_[bar.epic][bar.resolution];
    }

    {
        std::lock_guard<std::mutex> s_lock(strategies_mutex_);
        std::lock_guard<std::mutex> p_lock(positions_mutex_);

        for (auto& s : active_strategies_) {
            if (!s.active || s.epic != bar.epic || s.resolution != bar.resolution) continue;

            Signal sig = s.strategy->on_bar(history_copy.back());
            if (sig.action != SignalAction::NONE && redis_) {
                // 1. Check for opposite position and close it first
                for (auto& [deal_id, pos] : active_positions_) {
                    if (pos.epic == bar.epic && pos.strategy_name == s.name) {
                        bool is_opposite =
                            (sig.action == SignalAction::BUY && pos.direction == PositionDirection::SELL) ||
                            (sig.action == SignalAction::SELL && pos.direction == PositionDirection::BUY);

                        if (is_opposite) {
                            Signal close_sig_obj = {bar.epic, SignalAction::CLOSE, 0, 0, 0, s.name};
                            nlohmann::json close_sig = MarketDataParser::serialize_position_update(
                                deal_id, bar.epic, close_sig_obj, s.name, EngineConstants::SIGNAL_SOURCE_OPPOSITE);
                            redis_->publish(RedisKeys::TRADE_SIGNALS, close_sig.dump());
                            std::cout << "[CORE] Sent CLOSE for " << deal_id << " due to opposite signal from "
                                      << s.name << std::endl;
                        }
                    }
                }

                // 2. Publish the new signal
                json sj = MarketDataParser::serialize_trade_signal(sig, s, bar.resolution);
                redis_->publish(RedisKeys::TRADE_SIGNALS, sj.dump());
                std::cout << "[SIGNAL] " << s.name << " " << (sig.action == SignalAction::BUY ? "BUY" : "SELL") << " "
                          << bar.epic << " [" << bar.resolution << "] @ " << sig.price << " (SL:" << sig.stop_loss
                          << " TP:" << sig.take_profit << ")" << std::endl;
            } else {
                // std::cout << "[DEBUG] " << s.name << " evaluated " << bar.epic << " [" << bar.resolution << "] ->
                // NONE" << std::endl;
            }
        }
    }

    // Monitoring existing positions at Bar-Close (Trailing Stop / TP / SL)
    {
        std::lock_guard<std::mutex> s_lock(strategies_mutex_);
        std::lock_guard<std::mutex> p_lock(positions_mutex_);

        for (auto& [deal_id, pos] : active_positions_) {
            if (pos.epic != bar.epic) continue;

            pos.highest_high = std::max(pos.highest_high, bar.high);
            pos.lowest_low = (pos.lowest_low == 0) ? bar.low : std::min(pos.lowest_low, bar.low);

            for (auto& s : active_strategies_) {
                if (s.name == pos.strategy_name && s.active) {
                    Signal sig = s.strategy->on_position_update(pos, bar);
                    if (sig.action != SignalAction::NONE) {
                        nlohmann::json sj = MarketDataParser::serialize_position_update(
                            deal_id, bar.epic, sig, s.name, EngineConstants::SIGNAL_SOURCE_AUTO_TRAIL_BAR);
                        redis_->publish(RedisKeys::TRADE_SIGNALS, sj.dump());
                        if (sig.action == SignalAction::UPDATE_SL) pos.current_stop = sig.stop_loss;
                    }
                    break;
                }
            }
        }
    }
}
