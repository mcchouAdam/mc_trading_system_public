#pragma once
#include <sw/redis++/redis++.h>

#include <atomic>
#include <deque>
#include <map>
#include <memory>
#include <mutex>
#include <nlohmann/json.hpp>
#include <set>
#include <string>
#include <thread>
#include <vector>
#include <zmq.hpp>

#include "Bar.hpp"
#include "ConfigManager.hpp"
#include "EngineConstants.hpp"
#include "HistoryPreloader.hpp"
#include "IStrategy.hpp"
#include "MarketDataParser.hpp"
#include "RedisKeys.hpp"
#include "StrategyInstance.hpp"

class EngineCore {
public:
    EngineCore();
    virtual ~EngineCore();
    void run();

private:
    void handle_market_data(const std::string& topic, const std::string& payload);
    void process_tick(const Bar& tick);
    void process_bar(const Bar& bar);
    void run_config_loop();
    void process_zmq_events(zmq::pollitem_t* items, int count);

    bool is_history_empty(const std::string& epic, const std::string& resolution);
    void on_history_loaded(const std::string& epic, const std::string& resolution, const std::deque<Bar>& bars);

    zmq::context_t context_;
    zmq::socket_t tick_subscriber_;
    zmq::socket_t ohlc_subscriber_;

    std::unique_ptr<sw::redis::Redis> redis_;
    std::unique_ptr<sw::redis::Subscriber> redis_sub_;

    // Epic -> Resolution -> History
    std::map<std::string, std::map<std::string, std::deque<Bar>>> market_history_;
    std::mutex history_mutex_;

    std::vector<StrategyInstance> active_strategies_;
    std::mutex strategies_mutex_;

    std::map<std::string, Position> active_positions_;
    std::mutex positions_mutex_;

    std::atomic<bool> is_running_{true};
    std::atomic<bool> config_dirty_{true};
    std::atomic<bool> positions_dirty_{true};

    std::unique_ptr<ConfigManager> config_manager_;
    std::unique_ptr<HistoryPreloader> history_preloader_;

    std::thread redis_thread_;
    int tick_count_ = 0;

    std::string zmq_host_;
    std::string zmq_tick_port_;
    std::string zmq_ohlc_port_;
};
