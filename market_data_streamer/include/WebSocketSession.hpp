#ifndef WEBSOCKET_SESSION_HPP
#define WEBSOCKET_SESSION_HPP

#include <boost/asio/io_context.hpp>
#include <boost/asio/ip/tcp.hpp>
#include <boost/asio/ssl.hpp>
#include <boost/beast/core.hpp>
#include <boost/beast/websocket.hpp>
#include <boost/beast/websocket/ssl.hpp>
#include <functional>
#include <mutex>
#include <string>

namespace net = boost::asio;
namespace ssl = boost::asio::ssl;
namespace websocket = boost::beast::websocket;
using tcp = boost::asio::ip::tcp;

class WebSocketSession {
public:
    WebSocketSession();
    ~WebSocketSession();

    void connect(const std::string& host, const std::string& port, const std::string& path,
                 const std::function<void(websocket::request_type&)>& decorator);

    void send(const std::string& msg);
    void run_message_loop(const std::function<void(const std::string&)>& on_message,
                          const std::function<bool()>& check_running);

    void force_close();
    static bool is_connection_error(const boost::beast::system_error& se);

private:
    net::io_context ioc_;
    ssl::context ctx_{ssl::context::tlsv12_client};
    websocket::stream<ssl::stream<tcp::socket>> ws_;
    std::mutex ws_mutex_;
};

#endif  // WEBSOCKET_SESSION_HPP
