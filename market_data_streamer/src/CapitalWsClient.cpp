#include "CapitalWsClient.hpp"

#include <future>
#include <iostream>
#include <set>

#include "AppConfig.hpp"

using json = nlohmann::json;

namespace {
void run_safe_thread(const std::string& name, std::function<void()> task) {
    try {
        task();
    } catch (const std::exception& e) {
        std::cerr << "[CRITICAL THREAD ERROR] " << name << " crashed: " << e.what() << std::endl;
    } catch (...) {
        std::cerr << "[CRITICAL THREAD ERROR] " << name << " crashed with unknown error." << std::endl;
    }
}
}  // namespace

CapitalWsClient::CapitalWsClient() {
    setup_message_handlers();
}

CapitalWsClient::~CapitalWsClient() {
    cleanup();
}

void CapitalWsClient::run() {
    if (!initialize_session()) {
        std::cerr << "[ERROR] Session initialization failed." << std::endl;
        return;
    }

    try {
        connect_and_handshake();
        subscribe_all();
        start_background_threads();
        message_loop();
    } catch (const std::exception& e) {
        if (is_running_) {
            std::cerr << "[CRITICAL] run() error: " << e.what() << std::endl;
        }
    }
    cleanup();
}

bool CapitalWsClient::initialize_session() {
    auto cst_opt = redis_service_.fetch_value("CAPITAL_CST");
    auto token_opt = redis_service_.fetch_value("CAPITAL_TOKEN");

    if (!cst_opt || !token_opt) {
        std::cerr << "[ERROR] CST or Token missing from Redis." << std::endl;
        return false;
    }
    cst_ = *cst_opt;
    token_ = *token_opt;
    std::cout << "[SUCCESS] Retrieved Tokens from Redis." << std::endl;
    return true;
}

void CapitalWsClient::connect_and_handshake() {
    std::string host = AppConfig::WS_HOST;
    std::string port = AppConfig::WS_PORT;
    std::string path = AppConfig::WS_PATH;
    std::cout << "[INFO] Connecting to " << host << "..." << std::endl;

    ws_session_.connect(host, port, path, [this](websocket::request_type& req) {
        req.set(boost::beast::http::field::user_agent, "TradingBot/1.0");
        req.set("CST", cst_);
        req.set("X-SECURITY-TOKEN", token_);
    });
    std::cout << "[SUCCESS] WebSocket Handshake Completed." << std::endl;
}

void CapitalWsClient::subscribe_all() {
    auto market_data_str = redis_service_.fetch_value("MARKET_DATA_SUBSCRIBE");
    auto ohlc_subs_str = redis_service_.fetch_value("OHLC_DATA_SUBSCRIBE");

    // 1. Tick Data Subscriptions
    if (market_data_str) {
        try {
            json epics = json::parse(*market_data_str);
            if (epics.is_array() && !epics.empty()) {
                json tick_msg = {{"destination", "marketData.subscribe"},
                                 {"cst", cst_},
                                 {"securityToken", token_},
                                 {"payload", {{"epics", epics}}}};
                ws_session_.send(tick_msg.dump());
                std::cout << "[INFO] Subscribed Tick for " << epics.size() << " epics." << std::endl;
            }
        } catch (const std::exception& e) {
            std::cerr << "[ERROR] Tick subscription failed: " << e.what() << std::endl;
        } catch (...) {
            std::cerr << "[ERROR] Tick subscription failed with unknown error." << std::endl;
        }
    }

    // 2. OHLC Data Subscriptions based on manual OHLC_DATA_SUBSCRIBE key
    if (ohlc_subs_str) {
        try {
            json subs_list = json::parse(*ohlc_subs_str);
            if (subs_list.is_array()) {
                std::set<std::pair<std::string, std::string>> unique_subs;
                for (auto& item : subs_list) {
                    std::string ep = item.value("epic", "");
                    std::string res = item.value("resolution", "MINUTE");
                    if (!ep.empty()) unique_subs.insert({ep, res});
                }

                for (auto& sub : unique_subs) {
                    json ohlc_msg = {{"destination", "OHLCMarketData.subscribe"},
                                     {"cst", cst_},
                                     {"securityToken", token_},
                                     {"payload",
                                      {{"epics", json::array({sub.first})},
                                       {"resolutions", json::array({sub.second})},
                                       {"maxQuotesPerEpic", 10}}}};
                    ws_session_.send(ohlc_msg.dump());
                    std::cout << "[INFO] Subscribed OHLC: " << sub.first << " (" << sub.second << ")" << std::endl;
                }
            }
        } catch (const std::exception& e) {
            std::cerr << "[ERROR] OHLC subscription failed: " << e.what() << std::endl;
        } catch (...) {
            std::cerr << "[ERROR] OHLC subscription failed with unknown error." << std::endl;
        }
    }
}

void CapitalWsClient::start_background_threads() {
    is_running_ = true;

    // Ping thread
    ping_thread_ = std::thread([this]() {
        run_safe_thread("PingThread", [this]() {
            while (is_running_) {
                std::unique_lock<std::mutex> lk(shutdown_mutex_);
                if (shutdown_cv_.wait_for(lk, std::chrono::seconds(AppConfig::PING_INTERVAL_SECONDS),
                                          [this] { return !is_running_.load(); })) {
                    break;
                }
                if (!is_running_) break;
                try {
                    // Refresh tokens from Redis before each ping (to maintain session without restart)
                    auto cst_opt = redis_service_.fetch_value("CAPITAL_CST");
                    auto token_opt = redis_service_.fetch_value("CAPITAL_TOKEN");
                    if (cst_opt && token_opt) {
                        cst_ = *cst_opt;
                        token_ = *token_opt;
                    }

                    json ping = {
                        {"destination", "ping"}, {"correlationId", "ka"}, {"cst", cst_}, {"securityToken", token_}};
                    ws_session_.send(ping.dump());
                } catch (const std::exception& e) {
                    std::cerr << "[ERROR] Ping logic error: " << e.what() << std::endl;
                    break;
                }
            }
        });
    });

    // Config update thread
    config_sub_thread_ = std::thread([this]() {
        run_safe_thread("ConfigSubThread", [this]() {
            try {
                auto sub = redis_service_.client().subscriber();
                sub.subscribe("CHANNEL_CONFIG_UPDATED");
                sub.on_message([this](std::string channel, std::string msg) {
                    if (!is_running_) return;
                    std::cout << "[INFO] Config update received. Restarting Client..." << std::endl;
                    is_running_ = false;
                    ws_session_.force_close();
                });
                while (is_running_) {
                    try {
                        sub.consume();
                    } catch (const sw::redis::Error&) {
                        if (!is_running_) break;
                        std::this_thread::sleep_for(std::chrono::milliseconds(AppConfig::RESTART_DELAY_MS));
                    }
                }
            } catch (const std::exception& e) {
                std::cerr << "[ERROR] Config subscriber thread error: " << e.what() << std::endl;
            }
        });
    });
}

void CapitalWsClient::message_loop() {
    std::cout << "[INFO] Entering Message Loop..." << std::endl;
    ws_session_.run_message_loop([this](const std::string& data) { handle_message(data); },
                                 [this]() { return is_running_.load(); });
}

void CapitalWsClient::handle_message(const std::string& data) {
    redis_service_.set_last_seen("HEALTH:MARKET_DATA_STREAMER");

    try {
        json msg = json::parse(data);

        if (!msg.contains("destination")) return;

        std::string dest = msg["destination"];
        auto it = message_handlers_.find(dest);
        if (it != message_handlers_.end()) {
            it->second(msg["payload"]);
        } else {
            std::cout << "[INFO] Unhandled destination: " << dest << std::endl;
        }
    } catch (const std::exception& e) {
        std::cerr << "[ERROR] handle_message: " << e.what() << std::endl;
    }
}

void CapitalWsClient::process_ohlc(const json& payload) {
    std::string epic = payload.value("epic", "");
    std::string res = payload.value("resolution", "");
    if (epic.empty() || res.empty()) return;

    std::string topic = std::string(AppConfig::ZMQ_TOPIC_PREFIX) + epic + ":" + res;
    std::string data = payload.dump();
    zmq_service_.publish_ohlc(topic, data);
}

void CapitalWsClient::process_tick(json payload) {
    std::string epic = payload.value("epic", "");
    if (epic.empty()) return;

    payload[AppConfig::MSG_KEY_TYPE] = AppConfig::MSG_VAL_TICK;
    std::string topic = std::string(AppConfig::ZMQ_TOPIC_PREFIX) + epic + ":" + AppConfig::ZMQ_TICK_SUFFIX;
    std::string data = payload.dump();
    zmq_service_.publish_tick(topic, data);
}

void CapitalWsClient::process_ping(const json& payload) {
    // Keep silent on ping to maintain performance
}

void CapitalWsClient::setup_message_handlers() {
    message_handlers_["ohlc.event"] = [this](const json& payload) { process_ohlc(payload); };
    message_handlers_["quote"] = [this](const json& payload) { process_tick(payload); };
    message_handlers_["ping"] = [this](const json& payload) { process_ping(payload); };
}

void CapitalWsClient::cleanup() {
    is_running_ = false;
    shutdown_cv_.notify_all();
    if (ping_thread_.joinable()) {
        auto f = std::async(std::launch::async, [this] { ping_thread_.join(); });
        if (f.wait_for(std::chrono::seconds(2)) == std::future_status::timeout) {
            ping_thread_.detach();
        }
    }
    if (config_sub_thread_.joinable()) {
        config_sub_thread_.detach();
    }
}
