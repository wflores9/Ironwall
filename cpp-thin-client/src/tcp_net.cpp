#include "ironwall/tcp_net.hpp"
#include "util.hpp"
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <cstring>
#include <vector>

namespace ironwall {

namespace {
std::vector<uint8_t> serialize_client(const ClientMessage&) { return {0x01}; }
std::optional<ServerMessage> deserialize_server(const std::vector<uint8_t>&) {
    return WelcomeMsg{util::uuid4(), util::now()};
}
std::vector<uint8_t> serialize_server(const ServerMessage&) { return {0x02}; }
std::optional<ClientMessage> deserialize_client(const std::vector<uint8_t>&) {
    return HelloMsg{"remote", "0.1.0", {}};
}
}

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
    auto buf = serialize_client(msg);
    uint32_t len = htonl(static_cast<uint32_t>(buf.size()));
    if (::send(sock_, &len, 4, 0) != 4) return false;
    return ::send(sock_, buf.data(), buf.size(), 0) == static_cast<ssize_t>(buf.size());
}

std::optional<ServerMessage> TcpClient::recv(int) {
    if (sock_ < 0) return std::nullopt;
    uint32_t len_n = 0;
    if (::recv(sock_, &len_n, 4, MSG_WAITALL) != 4) return std::nullopt;
    uint32_t len = ntohl(len_n);
    if (len > 1<<20) return std::nullopt;
    std::vector<uint8_t> buf(len);
    if (::recv(sock_, buf.data(), len, MSG_WAITALL) != static_cast<ssize_t>(len)) return std::nullopt;
    return deserialize_server(buf);
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
        uint32_t len_n = 0;
        if (::recv(cs, &len_n, 4, MSG_WAITALL) == 4) {
            uint32_t blen = ntohl(len_n);
            if (blen < 1<<20) {
                std::vector<uint8_t> buf(blen);
                if (::recv(cs, buf.data(), blen, MSG_WAITALL) == static_cast<ssize_t>(blen)) {
                    auto msg = deserialize_client(buf);
                    if (msg && handler_) {
                        handler_(*msg, [cs](ServerMessage reply) {
                            auto out = serialize_server(reply);
                            uint32_t l = htonl(static_cast<uint32_t>(out.size()));
                            ::send(cs, &l, 4, 0);
                            ::send(cs, out.data(), out.size(), 0);
                        });
                    }
                }
            }
        }
        ::close(cs);
    }
}

} // namespace ironwall
