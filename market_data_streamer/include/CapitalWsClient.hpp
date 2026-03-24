#ifndef CAPITAL_WS_CLIENT_HPP
#define CAPITAL_WS_CLIENT_HPP

#include <atomic>
#include <condition_variable>
#include <functional>
#include <mutex>
#include <nlohmann/json.hpp>
#include <string>
#include <thread>
#include <unordered_map>

#include "RedisService.hpp"
#include "WebSocketSession.hpp"
#include "ZmqService.hpp"

using json = nlohmann::json;

class CapitalWsClient {
public:
    CapitalWsClient();
    ~CapitalWsClient();
    void run();

private:
    bool initialize_session();
    void connect_and_handshake();
    void subscribe_all();
    void message_loop();
    void start_background_threads();
    void handle_message(const std::string& data);
    void process_ohlc(const json& payload);
    void process_tick(json payload);  // by-value: needs to add "type":"tick" field
    void process_ping(const json& payload);
    void cleanup();

    void setup_message_handlers();
    using MessageHandler = std::function<void(const json&)>;
    std::unordered_map<std::string, MessageHandler> message_handlers_;

    WebSocketSession ws_session_;

    RedisService redis_service_;
    ZmqService zmq_service_;

    std::string cst_;
    std::string token_;

    std::mutex shutdown_mutex_;
    std::condition_variable shutdown_cv_;
    std::atomic<bool> is_running_{false};

    std::thread ping_thread_;
    std::thread config_sub_thread_;
};

#endif  // CAPITAL_WS_CLIENT_HPP
