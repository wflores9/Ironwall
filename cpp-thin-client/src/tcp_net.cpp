#include "ironwall/tcp_net.hpp"
#include "ironwall/wire.hpp"
#include "util.hpp"
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <cstring>
#include <vector>

namespace ironwall {

TcpClient::~TcpClient() { disconnect(); }

bool TcpClient::connect(const std::string& host, uint16_t port) {
    disconnect();
    sock_ = ::socket(AF_INET, SOCK_STREAM, 0);
    if (sock_ < 0) return false;
    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_port = htons(port);
    if (inet_pton(AF_INET, host.c_str(), &addr.sin_addr) <= 0) { disconnect(); return false; }
    if (::connect(sock_, reinterpret_cast<sockaddr*>(&addr), sizeof(addr)) < 0) { disconnect(); return false; }
    return true;
}

void TcpClient::disconnect() {
    if (sock_ >= 0) { ::close(sock_); sock_ = -1; }
}

bool TcpClient::send(const ClientMessage& msg) {
    if (sock_ < 0) return false;
    auto buf = wire::encode_client(msg);
    return ::send(sock_, buf.data(), buf.size(), 0) == static_cast<ssize_t>(buf.size());
}

std::optional<ServerMessage> TcpClient::recv(int) {
    if (sock_ < 0) return std::nullopt;
    uint8_t hdr[10];
    if (::recv(sock_, hdr, 10, MSG_WAITALL) != 10) return std::nullopt;
    uint32_t plen = hdr[6] | (hdr[7]<<8) | (hdr[8]<<16) | (hdr[9]<<24);
    if (plen > 1<<20) return std::nullopt;
    std::vector<uint8_t> buf(10 + plen);
    std::memcpy(buf.data(), hdr, 10);
    if (plen && ::recv(sock_, buf.data()+10, plen, MSG_WAITALL) != static_cast<ssize_t>(plen))
        return std::nullopt;
    size_t consumed = 0;
    return wire::decode_server(buf.data(), buf.size(), consumed);
}

TcpServer::~TcpServer() { stop(); }

bool TcpServer::listen(uint16_t port) {
    stop();
    listen_sock_ = ::socket(AF_INET, SOCK_STREAM, 0);
    if (listen_sock_ < 0) return false;
    int opt = 1;
    setsockopt(listen_sock_, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));
    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = INADDR_ANY;
    addr.sin_port = htons(port);
    if (bind(listen_sock_, reinterpret_cast<sockaddr*>(&addr), sizeof(addr)) < 0) { stop(); return false; }
    if (::listen(listen_sock_, 16) < 0) { stop(); return false; }
    return true;
}

void TcpServer::start() {
    if (running_) return;
    running_ = true;
    accept_thread_ = std::thread([this]{ accept_loop(); });
}

void TcpServer::stop() {
    running_ = false;
    if (listen_sock_ >= 0) { ::close(listen_sock_); listen_sock_ = -1; }
    if (accept_thread_.joinable()) accept_thread_.join();
}

void TcpServer::accept_loop() {
    while (running_) {
        sockaddr_in ca{};
        socklen_t len = sizeof(ca);
        int cs = accept(listen_sock_, reinterpret_cast<sockaddr*>(&ca), &len);
        if (cs < 0) continue;

        uint8_t hdr[10];
        if (::recv(cs, hdr, 10, MSG_WAITALL) == 10) {
            uint32_t plen = hdr[6] | (hdr[7]<<8) | (hdr[8]<<16) | (hdr[9]<<24);
            if (plen < 1<<20) {
                std::vector<uint8_t> buf(10 + plen);
                std::memcpy(buf.data(), hdr, 10);
                bool ok = plen == 0 || ::recv(cs, buf.data()+10, plen, MSG_WAITALL) == static_cast<ssize_t>(plen);
                if (ok) {
                    try {
                        size_t consumed = 0;
                        auto msg = wire::decode_client(buf.data(), buf.size(), consumed);
                        if (msg && handler_) {
                            handler_(*msg, [cs](ServerMessage reply) {
                                auto out = wire::encode_server(reply);
                                ::send(cs, out.data(), out.size(), 0);
                            });
                        }
                    } catch (...) {}
                }
            }
        }
        ::close(cs);
    }
}

} // namespace ironwall
