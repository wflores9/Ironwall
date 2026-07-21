#include "ironwall/udp_net.hpp"
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <cstring>
#include <poll.h>
#include <iostream>

namespace ironwall {

UdpSocket::~UdpSocket() { close(); }

void UdpSocket::close() {
    if (fd_ >= 0) { ::close(fd_); fd_ = -1; }
}

bool UdpSocket::bind(uint16_t port) {
    close();
    fd_ = ::socket(AF_INET, SOCK_DGRAM, 0);
    if (fd_ < 0) return false;
    int opt = 1;
    setsockopt(fd_, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));
    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    addr.sin_port = htons(port);
    if (::bind(fd_, reinterpret_cast<sockaddr*>(&addr), sizeof(addr)) < 0) {
        close();
        return false;
    }
    return true;
}

bool UdpSocket::connect(const std::string& host, uint16_t port) {
    if (fd_ < 0) {
        fd_ = ::socket(AF_INET, SOCK_DGRAM, 0);
        if (fd_ < 0) return false;
    }
    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_port = htons(port);
    if (inet_pton(AF_INET, host.c_str(), &addr.sin_addr) <= 0) return false;
    return ::connect(fd_, reinterpret_cast<sockaddr*>(&addr), sizeof(addr)) == 0;
}

uint16_t UdpSocket::local_port() const {
    if (fd_ < 0) return 0;
    sockaddr_in addr{};
    socklen_t len = sizeof(addr);
    if (getsockname(fd_, reinterpret_cast<sockaddr*>(&addr), &len) < 0) return 0;
    return ntohs(addr.sin_port);
}

bool UdpSocket::send(const std::vector<uint8_t>& datagram) {
    if (fd_ < 0 || datagram.empty()) return false;
    return ::send(fd_, datagram.data(), datagram.size(), 0) == static_cast<ssize_t>(datagram.size());
}

std::optional<std::vector<uint8_t>> UdpSocket::recv(int timeout_ms) {
    if (fd_ < 0) return std::nullopt;
    pollfd pfd{fd_, POLLIN, 0};
    if (poll(&pfd, 1, timeout_ms) <= 0) return std::nullopt;
    std::vector<uint8_t> buf(2048);
    ssize_t n = ::recv(fd_, buf.data(), buf.size(), 0);
    if (n <= 0) return std::nullopt;
    buf.resize(static_cast<size_t>(n));
    return buf;
}

bool UdpSocket::send_client(const ClientMessage& msg, const std::string& secret) {
    return send(wire::encode_client_signed(msg, secret));
}
bool UdpSocket::send_server(const ServerMessage& msg, const std::string& secret) {
    return send(wire::encode_server_signed(msg, secret));
}

std::optional<ClientMessage> UdpSocket::recv_client(const std::string& secret, int timeout_ms) {
    auto dg = recv(timeout_ms);
    if (!dg) return std::nullopt;
    auto body = wire::verify_frame(dg->data(), dg->size(), secret);
    if (!body) return std::nullopt;
    size_t consumed = 0;
    return wire::decode_client(body->data(), body->size(), consumed);
}

std::optional<ServerMessage> UdpSocket::recv_server(const std::string& secret, int timeout_ms) {
    auto dg = recv(timeout_ms);
    if (!dg) return std::nullopt;
    auto body = wire::verify_frame(dg->data(), dg->size(), secret);
    if (!body) return std::nullopt;
    size_t consumed = 0;
    return wire::decode_server(body->data(), body->size(), consumed);
}

bool udp_echo_demo(const std::vector<uint8_t>& payload, std::vector<uint8_t>& response) {
    // Bidirectional connected UDP: bind both, connect to each other
    UdpSocket a, b;
    if (!a.bind(0) || !b.bind(0)) return false;
    uint16_t pa = a.local_port();
    uint16_t pb = b.local_port();
    if (!a.connect("127.0.0.1", pb)) return false;
    if (!b.connect("127.0.0.1", pa)) return false;

    if (!a.send(payload)) return false;
    auto got = b.recv(1000);
    if (!got || *got != payload) return false;

    std::vector<uint8_t> ack = {'A','C','K',':'};
    ack.insert(ack.end(), got->begin(), got->end());
    if (!b.send(ack)) return false;
    auto back = a.recv(1000);
    if (!back) return false;
    response = *back;
    return response.size() >= 4 && response[0]=='A' && response[1]=='C' && response[2]=='K';
}

} // namespace ironwall
