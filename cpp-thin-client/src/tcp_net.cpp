#include "ironwall/tcp_net.hpp"
#include "ironwall/wire.hpp"
#include "util.hpp"
#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
#else
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#endif
#include <cstring>
#include <vector>

namespace ironwall {

#ifdef _WIN32
static bool tcp_winsock_ready() { static const bool ready = [] { WSADATA d{}; return WSAStartup(MAKEWORD(2,2), &d) == 0; }(); return ready; }
#endif
static void close_tcp_socket(std::intptr_t fd) {
#ifdef _WIN32
    ::closesocket(static_cast<SOCKET>(fd));
#else
    ::close(static_cast<int>(fd));
#endif
}
static bool tcp_send_bytes(std::intptr_t fd, const uint8_t* data, size_t size) {
    if (size > static_cast<size_t>(2147483647)) return false;
#ifdef _WIN32
    return ::send(static_cast<SOCKET>(fd), reinterpret_cast<const char*>(data), static_cast<int>(size), 0) == static_cast<int>(size);
#else
    return ::send(static_cast<int>(fd), data, size, 0) == static_cast<ssize_t>(size);
#endif
}
static bool tcp_recv_exact(std::intptr_t fd, uint8_t* data, size_t size) {
    size_t received = 0;
    while (received < size) {
#ifdef _WIN32
        int n = ::recv(static_cast<SOCKET>(fd), reinterpret_cast<char*>(data + received), static_cast<int>(size - received), 0);
#else
        ssize_t n = ::recv(static_cast<int>(fd), data + received, size - received, 0);
#endif
        if (n <= 0) return false;
        received += static_cast<size_t>(n);
    }
    return true;
}


TcpClient::~TcpClient() { disconnect(); }

bool TcpClient::connect(const std::string& host, uint16_t port) {
    disconnect();
#ifdef _WIN32
    if (!tcp_winsock_ready()) return false;
#endif
    sock_ = static_cast<std::intptr_t>(::socket(AF_INET, SOCK_STREAM, 0));
    if (sock_ < 0) return false;
    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_port = htons(port);
    if (inet_pton(AF_INET, host.c_str(), &addr.sin_addr) <= 0) { disconnect(); return false; }
    if (::connect(static_cast<decltype(::socket(0,0,0))>(sock_), reinterpret_cast<sockaddr*>(&addr), sizeof(addr)) < 0) { disconnect(); return false; }
    return true;
}

void TcpClient::disconnect() {
    if (sock_ >= 0) { close_tcp_socket(sock_); sock_ = -1; }
}

bool TcpClient::send(const ClientMessage& msg) {
    if (sock_ < 0) return false;
    auto buf = wire::encode_client(msg);
    return tcp_send_bytes(sock_, buf.data(), buf.size());
}

std::optional<ServerMessage> TcpClient::recv(int) {
    if (sock_ < 0) return std::nullopt;
    uint8_t hdr[10];
    if (!tcp_recv_exact(sock_, hdr, 10)) return std::nullopt;
    uint32_t plen = hdr[6] | (hdr[7]<<8) | (hdr[8]<<16) | (hdr[9]<<24);
    if (plen > 1<<20) return std::nullopt;
    std::vector<uint8_t> buf(10 + plen);
    std::memcpy(buf.data(), hdr, 10);
    if (plen && !tcp_recv_exact(sock_, buf.data()+10, plen))
        return std::nullopt;
    size_t consumed = 0;
    return wire::decode_server(buf.data(), buf.size(), consumed);
}

TcpServer::~TcpServer() { stop(); }

bool TcpServer::listen(uint16_t port) {
    stop();
#ifdef _WIN32
    if (!tcp_winsock_ready()) return false;
#endif
    listen_sock_ = static_cast<std::intptr_t>(::socket(AF_INET, SOCK_STREAM, 0));
    if (listen_sock_ < 0) return false;
    int opt = 1;
#ifdef _WIN32
    setsockopt(static_cast<SOCKET>(listen_sock_), SOL_SOCKET, SO_REUSEADDR, reinterpret_cast<const char*>(&opt), sizeof(opt));
#else
    setsockopt(static_cast<int>(listen_sock_), SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));
#endif
    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = INADDR_ANY;
    addr.sin_port = htons(port);
    if (bind(static_cast<decltype(::socket(0,0,0))>(listen_sock_), reinterpret_cast<sockaddr*>(&addr), sizeof(addr)) < 0) { stop(); return false; }
    if (::listen(static_cast<decltype(::socket(0,0,0))>(listen_sock_), 16) < 0) { stop(); return false; }
    return true;
}

void TcpServer::start() {
    if (running_) return;
    running_ = true;
    accept_thread_ = std::thread([this]{ accept_loop(); });
}

void TcpServer::stop() {
    running_ = false;
    if (listen_sock_ >= 0) { close_tcp_socket(listen_sock_); listen_sock_ = -1; }
    if (accept_thread_.joinable()) accept_thread_.join();
}

void TcpServer::accept_loop() {
    while (running_) {
        sockaddr_in ca{};
 #ifdef _WIN32
        int len = sizeof(ca);
#else
        socklen_t len = sizeof(ca);
#endif
        auto cs = accept(static_cast<decltype(::socket(0,0,0))>(listen_sock_), reinterpret_cast<sockaddr*>(&ca), &len);
        if (cs < 0) continue;

        uint8_t hdr[10];
        if (tcp_recv_exact(static_cast<std::intptr_t>(cs), hdr, 10)) {
            uint32_t plen = hdr[6] | (hdr[7]<<8) | (hdr[8]<<16) | (hdr[9]<<24);
            if (plen < 1<<20) {
                std::vector<uint8_t> buf(10 + plen);
                std::memcpy(buf.data(), hdr, 10);
                bool ok = plen == 0 || tcp_recv_exact(static_cast<std::intptr_t>(cs), buf.data()+10, plen);
                if (ok) {
                    try {
                        size_t consumed = 0;
                        auto msg = wire::decode_client(buf.data(), buf.size(), consumed);
                        if (msg && handler_) {
                            handler_(*msg, [cs](ServerMessage reply) {
                                auto out = wire::encode_server(reply);
                                tcp_send_bytes(static_cast<std::intptr_t>(cs), out.data(), out.size());
                            });
                        }
                    } catch (...) {}
                }
            }
        }
        close_tcp_socket(static_cast<std::intptr_t>(cs));
    }
}

} // namespace ironwall
