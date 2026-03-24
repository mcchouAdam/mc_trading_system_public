#include "ZmqService.hpp"

#include <iostream>

#include "AppConfig.hpp"

ZmqService::ZmqService()
    : context_(1), tick_pub_(context_, zmq::socket_type::pub), ohlc_pub_(context_, zmq::socket_type::pub) {
    try {
        // Tick publisher
        int tick_hwm = AppConfig::ZMQ_TICK_HWM;
        tick_pub_.set(zmq::sockopt::sndhwm, tick_hwm);
        std::string tick_bind = std::string(AppConfig::ZMQ_BIND_HOST) + ":" + std::to_string(AppConfig::ZMQ_TICK_PORT);
        tick_pub_.bind(tick_bind);
        std::cout << "[INFO] ZMQ Tick Publisher bound to " << tick_bind << " (HWM=" << tick_hwm << ")" << std::endl;

        // OHLC publisher
        int ohlc_hwm = AppConfig::ZMQ_OHLC_HWM;
        ohlc_pub_.set(zmq::sockopt::sndhwm, ohlc_hwm);
        std::string ohlc_bind = std::string(AppConfig::ZMQ_BIND_HOST) + ":" + std::to_string(AppConfig::ZMQ_OHLC_PORT);
        ohlc_pub_.bind(ohlc_bind);
        std::cout << "[INFO] ZMQ OHLC Publisher bound to " << ohlc_bind << " (HWM=" << ohlc_hwm << ")" << std::endl;

    } catch (const zmq::error_t& e) {
        std::cerr << "[ERROR] ZeroMQ Bind Failed: " << e.what() << std::endl;
    }
}

ZmqService::~ZmqService() {
    tick_pub_.close();
    ohlc_pub_.close();
}

void ZmqService::publish_tick(const std::string& topic, const std::string& message) {
    try {
        zmq::message_t topic_msg(topic.begin(), topic.end());
        zmq::message_t payload_msg(message.begin(), message.end());

        tick_pub_.send(topic_msg, zmq::send_flags::sndmore);
        tick_pub_.send(payload_msg, zmq::send_flags::none);
    } catch (const zmq::error_t& e) {
        std::cerr << "[ERROR] ZMQ Tick Publish Failed: " << e.what() << std::endl;
    }
}

void ZmqService::publish_ohlc(const std::string& topic, const std::string& message) {
    try {
        zmq::message_t topic_msg(topic.begin(), topic.end());
        zmq::message_t payload_msg(message.begin(), message.end());

        ohlc_pub_.send(topic_msg, zmq::send_flags::sndmore);
        ohlc_pub_.send(payload_msg, zmq::send_flags::none);
    } catch (const zmq::error_t& e) {
        std::cerr << "[ERROR] ZMQ OHLC Publish Failed: " << e.what() << std::endl;
    }
}
