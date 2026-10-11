#include "ironwall/udp_net.hpp"
#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
#else
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <cstring>
#include <poll.h>
#endif
#include <iostream>

namespace ironwall {

#ifdef _WIN32
static bool winsock_init() { static const bool ok = [] { WSADATA w{}; return WSAStartup(MAKEWORD(2,2), &w)==0; }(); return ok; }
#endif
UdpSocket::~UdpSocket() { close(); }

void UdpSocket::close() {
    if (fd_ >= 0) {
#ifdef _WIN32
::closesocket(static_cast<SOCKET>(fd_));
#else
::close(fd_);
#endif
        fd_ = -1;
    }
}

bool UdpSocket::bind(uint16_t port) {
    close();
#ifdef _WIN32
    if (!winsock_init()) return false;
#endif
    fd_ = static_cast<std::intptr_t>(::socket(AF_INET, SOCK_DGRAM, 0));
    if (fd_ < 0) return false;
    int opt = 1;
#ifdef _WIN32
    setsockopt(static_cast<SOCKET>(fd_), SOL_SOCKET, SO_REUSEADDR, reinterpret_cast<const char*>(&opt), sizeof(opt));
#else
    setsockopt(fd_, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));
#endif
    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    addr.sin_port = htons(port);
    if (::bind(static_cast<decltype(::socket(0,0,0))>(fd_), reinterpret_cast<sockaddr*>(&addr), sizeof(addr)) < 0) {
        close();
        return false;
    }
    return true;
}

bool UdpSocket::connect(const std::string& host, uint16_t port) {
    if (fd_ < 0) {
#ifdef _WIN32
        if (!winsock_init()) return false;
#endif
        fd_ = static_cast<std::intptr_t>(::socket(AF_INET, SOCK_DGRAM, 0));
        if (fd_ < 0) return false;
    }
    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_port = htons(port);
    if (inet_pton(AF_INET, host.c_str(), &addr.sin_addr) <= 0) return false;
    return ::connect(static_cast<decltype(::socket(0,0,0))>(fd_), reinterpret_cast<sockaddr*>(&addr), sizeof(addr)) == 0;
}

uint16_t UdpSocket::local_port() const {
    if (fd_ < 0) return 0;
    sockaddr_in addr{};
#ifdef _WIN32
    int len = sizeof(addr);
#else
    socklen_t len = sizeof(addr);
#endif
    if (getsockname(static_cast<decltype(::socket(0,0,0))>(fd_), reinterpret_cast<sockaddr*>(&addr), &len) < 0) return 0;
    return ntohs(addr.sin_port);
}

bool UdpSocket::send(const std::vector<uint8_t>& datagram) {
    if (fd_ < 0 || datagram.empty()) return false;
#ifdef _WIN32
    return ::send(static_cast<SOCKET>(fd_), reinterpret_cast<const char*>(datagram.data()), static_cast<int>(datagram.size()), 0) == static_cast<int>(datagram.size());
#else
    return ::send(fd_, datagram.data(), datagram.size(), 0) == static_cast<ssize_t>(datagram.size());
#endif
}

std::optional<std::vector<uint8_t>> UdpSocket::recv(int timeout_ms) {
    if (fd_ < 0) return std::nullopt;
#ifdef _WIN32
    WSAPOLLFD pfd{static_cast<SOCKET>(fd_), POLLRDNORM, 0};
    if (WSAPoll(&pfd, 1, timeout_ms) <= 0) return std::nullopt;
#else
    pollfd pfd{static_cast<int>(fd_), POLLIN, 0};
    if (poll(&pfd, 1, timeout_ms) <= 0) return std::nullopt;
#endif
    std::vector<uint8_t> buf(2048);
#ifdef _WIN32
    int n = ::recv(static_cast<SOCKET>(fd_), reinterpret_cast<char*>(buf.data()), static_cast<int>(buf.size()), 0);
#else
    ssize_t n = ::recv(fd_, buf.data(), buf.size(), 0);
#endif
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
