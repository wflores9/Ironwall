#pragma once
#include "protocol.hpp"
#include <string>
#include <thread>
#include <atomic>
#include <functional>
#include <optional>

namespace ironwall {

class TcpClient {
public:
    TcpClient() = default;
    ~TcpClient();
    bool connect(const std::string& host, uint16_t port);
    void disconnect();
    bool send(const ClientMessage& msg);
    std::optional<ServerMessage> recv(int timeout_ms = 1000);
    bool connected() const { return sock_ >= 0; }
private:
    int sock_ = -1;
};

class TcpServer {
public:
    using Handler = std::function<void(ClientMessage, std::function<void(ServerMessage)>)>;
    TcpServer() = default;
    ~TcpServer();
    bool listen(uint16_t port);
    void set_handler(Handler h) { handler_ = std::move(h); }
    void start();
    void stop();
private:
    void accept_loop();
    int listen_sock_ = -1;
    std::atomic<bool> running_{false};
    std::thread accept_thread_;
    Handler handler_;
};

} // namespace ironwall
