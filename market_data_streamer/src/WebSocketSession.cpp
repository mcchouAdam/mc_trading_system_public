#include "WebSocketSession.hpp"

#include <boost/asio/connect.hpp>
#include <iostream>

WebSocketSession::WebSocketSession() : ws_(ioc_, ctx_) {
    ctx_.set_default_verify_paths();
}

WebSocketSession::~WebSocketSession() {
    force_close();
}

void WebSocketSession::connect(const std::string& host, const std::string& port, const std::string& path,
                               const std::function<void(websocket::request_type&)>& decorator) {
    tcp::resolver resolver(ioc_);
    auto const results = resolver.resolve(host, port);
    net::connect(ws_.next_layer().next_layer(), results);
    ws_.next_layer().handshake(ssl::stream_base::client);

    if (decorator) {
        ws_.set_option(websocket::stream_base::decorator(decorator));
    }

    ws_.handshake(host, path);
}

void WebSocketSession::send(const std::string& msg) {
    std::lock_guard<std::mutex> lock(ws_mutex_);
    ws_.write(net::buffer(msg));
}

void WebSocketSession::force_close() {
    boost::system::error_code ec;
    ws_.next_layer().next_layer().close(ec);
}

bool WebSocketSession::is_connection_error(const boost::beast::system_error& se) {
    auto ec = se.code();
    return ec == websocket::error::closed || ec == net::error::eof || ec == net::error::operation_aborted ||
           ec == net::error::connection_reset;
}

void WebSocketSession::run_message_loop(const std::function<void(const std::string&)>& on_message,
                                        const std::function<bool()>& check_running) {
    boost::beast::flat_buffer buffer;
    while (check_running && check_running()) {
        try {
            ws_.read(buffer);
            if (check_running && !check_running()) break;

            std::string data = boost::beast::buffers_to_string(buffer.data());
            buffer.consume(buffer.size());
            if (on_message) {
                on_message(data);
            }
        } catch (const boost::beast::system_error& se) {
            if (check_running && !check_running()) break;
            if (is_connection_error(se)) {
                std::cout << "[INFO] WebSocket connection closed: " << se.what() << std::endl;
                break;
            }
            throw;
        }
    }
}
