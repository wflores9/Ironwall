#pragma once
#include "protocol.hpp"
#include <queue>
#include <mutex>
#include <optional>
#include <functional>

namespace ironwall {

// Simple in-process loopback transport (replace with TCP/QUIC later)
class NetLoopback {
public:
    void client_send(ClientMessage msg);
    std::optional<ServerMessage> client_recv();
    void server_send(ServerMessage msg);
    std::optional<ClientMessage> server_recv();

    // Demo server handler
    void run_server_once();
private:
    std::mutex mtx_;
    std::queue<ClientMessage> to_server_;
    std::queue<ServerMessage> to_client_;
};

} // namespace ironwall
