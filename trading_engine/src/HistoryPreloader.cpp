#include "HistoryPreloader.hpp"

#include <iostream>
#include <nlohmann/json.hpp>
#include <thread>

#include "EngineConstants.hpp"
#include "MarketDataParser.hpp"
#include "RedisKeys.hpp"

using json = nlohmann::json;

HistoryPreloader::HistoryPreloader(sw::redis::Redis* redis) : redis_(redis) {
}

void HistoryPreloader::preload(const std::string& epic, const std::string& resolution,
                               std::function<bool()> check_if_empty,
                               std::function<void(const std::deque<Bar>&)> on_history_loaded) {
    if (!redis_) return;

    {
        std::lock_guard<std::mutex> lock(preload_mutex_);
        std::string key = epic + EngineConstants::ZMQ_KEY_SEPARATOR + resolution;
        if (preloading_tasks_.count(key)) return;

        if (!check_if_empty()) return;
        preloading_tasks_.insert(key);
    }

    std::string request_id = epic + EngineConstants::ID_SEPARATOR + resolution + EngineConstants::ID_SEPARATOR +
                             std::to_string(time(nullptr));
    json request = {{"epic", epic},
                    {"resolution", resolution},
                    {"request_id", request_id},
                    {"limit", EngineConstants::MAX_HISTORY_SIZE}};

    try {
        redis_->lpush(RedisKeys::CH_HISTORY_REQ, request.dump());
        std::string response_key = std::string(RedisKeys::PREFIX_HISTORY_RESP) + request_id;

        for (int i = 0; i < 100; ++i) {
            auto resp = redis_->get(response_key);
            if (resp) {
                json r_data = json::parse(*resp);
                std::deque<Bar> bars;
                for (auto& row : r_data["data"]) {
                    Bar b = MarketDataParser::parse_history_bar(epic, resolution, row);
                    bars.push_back(b);
                }

                // Trigger the callback with the loaded bars
                on_history_loaded(bars);

                std::cout << "[WARM-UP] Success: " << epic << " [" << resolution << "]" << std::endl;
                redis_->del(response_key);
                break;
            }
            std::this_thread::sleep_for(std::chrono::milliseconds(EngineConstants::REDIS_POLL_WAIT_MS));
        }
    } catch (const std::exception& e) {
        std::cerr << "[ERROR] Exception in HistoryPreloader for " << epic << ": " << e.what() << std::endl;
    } catch (...) {
        std::cerr << "[ERROR] Unknown exception in HistoryPreloader for " << epic << std::endl;
    }

    std::lock_guard<std::mutex> lock(preload_mutex_);
    preloading_tasks_.erase(epic + EngineConstants::ZMQ_KEY_SEPARATOR + resolution);
}
