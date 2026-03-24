#ifndef APP_CONFIG_HPP
#define APP_CONFIG_HPP

#include <string>
#include <string_view>

struct AppConfig {
    static void load_env(std::string_view filename = ".env");

    static std::string get_redis_host();
    static std::string get_redis_port();
    static std::string get_redis_password();

    // WebSocket Configuration
    static constexpr const char* WS_HOST = "api-streaming-capital.backend-capital.com";
    static constexpr const char* WS_PORT = "443";
    static constexpr const char* WS_PATH = "/connect";

    // ZeroMQ Ports and Settings
    static constexpr int ZMQ_TICK_PORT = 5555;
    static constexpr int ZMQ_OHLC_PORT = 5556;
    static constexpr int ZMQ_TICK_HWM = 5000;
    static constexpr int ZMQ_OHLC_HWM = 1000;
    static constexpr const char* ZMQ_BIND_HOST = "tcp://0.0.0.0";

    // ZMQ Topics
    static constexpr const char* ZMQ_TOPIC_PREFIX = "PRICE:";
    static constexpr const char* ZMQ_TICK_SUFFIX = "TICK";

    // Message Payload Definitions
    static constexpr const char* MSG_KEY_TYPE = "type";
    static constexpr const char* MSG_VAL_TICK = "tick";

    // System Timers
    static constexpr int PING_INTERVAL_SECONDS = 300;
    static constexpr int RESTART_DELAY_MS = 500;

private:
    static std::string get_env(std::string_view key, std::string_view default_val);
};

#endif  // APP_CONFIG_HPP
