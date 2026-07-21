#pragma once
#include "wire.hpp"
#include "wire_auth.hpp"
#include <string>
#include <vector>
#include <optional>
#include <cstdint>

namespace ironwall {

// Simple UDP datagram transport carrying IWAL frames (optionally HMAC-signed).
// Max payload ~1200 bytes to stay under common MTU.
class UdpSocket {
public:
    UdpSocket() = default;
    ~UdpSocket();

    bool bind(uint16_t port);                         // 0 = ephemeral
    bool connect(const std::string& host, uint16_t port);
    uint16_t local_port() const;

    bool send(const std::vector<uint8_t>& datagram);
    std::optional<std::vector<uint8_t>> recv(int timeout_ms = 1000);

    // Convenience: send/recv signed client/server messages
    bool send_client(const ClientMessage& msg, const std::string& secret);
    bool send_server(const ServerMessage& msg, const std::string& secret);
    std::optional<ClientMessage> recv_client(const std::string& secret, int timeout_ms = 1000);
    std::optional<ServerMessage> recv_server(const std::string& secret, int timeout_ms = 1000);

    void close();
    bool valid() const { return fd_ >= 0; }

private:
    int fd_ = -1;
};

// One-shot localhost echo demo used by tests / smoke
bool udp_echo_demo(const std::vector<uint8_t>& payload, std::vector<uint8_t>& response);

} // namespace ironwall
