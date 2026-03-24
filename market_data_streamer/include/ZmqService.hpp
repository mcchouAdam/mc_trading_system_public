#pragma once
#include <string>
#include <zmq.hpp>

class ZmqService {
public:
    ZmqService();
    ~ZmqService();

    void publish_tick(const std::string& topic, const std::string& message);
    void publish_ohlc(const std::string& topic, const std::string& message);

private:
    zmq::context_t context_;
    zmq::socket_t tick_pub_;
    zmq::socket_t ohlc_pub_;
};
