#pragma once

namespace EngineConstants {
constexpr const char* ZMQ_TOPIC_PRICE = "PRICE:";

// Timeouts and Delays (in milliseconds)
constexpr int REDIS_IDLE_WAIT_MS = 100;
constexpr int REDIS_ERROR_WAIT_MS = 500;
constexpr int REDIS_POLL_WAIT_MS = 100;

constexpr int ZMQ_POLL_TIMEOUT_MS = 200;
constexpr int ZMQ_ERROR_WAIT_MS = 500;

// ZMQ High Water Mark
constexpr int ZMQ_TICK_HWM = 5000;
constexpr int ZMQ_OHLC_HWM = 1000;

constexpr char ZMQ_TOPIC_SEPARATOR = ':';
constexpr const char* ZMQ_KEY_SEPARATOR = ":";
constexpr const char* ID_SEPARATOR = "_";
constexpr const char* ISO_DATETIME_FORMAT = "%d-%d-%dT%d:%d:%d";
constexpr const char* RESOLUTION_TICK = "TICK";
constexpr int MAX_HISTORY_SIZE = 200;

// Signal Strings
constexpr const char* SIGNAL_ACTION_UPDATE_SL = "UPDATE_SL";
constexpr const char* SIGNAL_ACTION_CLOSE = "CLOSE";
constexpr const char* SIGNAL_SOURCE_AUTO_TRAIL_TICK = "AUTO_TRAIL";
constexpr const char* SIGNAL_SOURCE_AUTO_TRAIL_BAR = "AUTO_TRAIL_BAR";
constexpr const char* SIGNAL_SOURCE_OPPOSITE = "OPPOSITE_SIGNAL_CLOSE";
}  // namespace EngineConstants
