#include "ironwall/net.hpp"
#include "util.hpp"
#include <iostream>

namespace ironwall {

void NetLoopback::client_send(ClientMessage msg) {
    std::lock_guard lock(mtx_);
    to_server_.push(std::move(msg));
}

std::optional<ServerMessage> NetLoopback::client_recv() {
    std::lock_guard lock(mtx_);
    if (to_client_.empty()) return std::nullopt;
    auto m = std::move(to_client_.front());
    to_client_.pop();
    return m;
}

void NetLoopback::server_send(ServerMessage msg) {
    std::lock_guard lock(mtx_);
    to_client_.push(std::move(msg));
}

std::optional<ClientMessage> NetLoopback::server_recv() {
    std::lock_guard lock(mtx_);
    if (to_server_.empty()) return std::nullopt;
    auto m = std::move(to_server_.front());
    to_server_.pop();
    return m;
}

void NetLoopback::run_server_once() {
    auto msg = server_recv();
    if (!msg) return;

    std::visit([this](auto&& m) {
        using T = std::decay_t<decltype(m)>;
        if constexpr (std::is_same_v<T, HelloMsg>) {
            std::cout << "[server] got Hello from " << m.player_id << "\n";
            server_send(WelcomeMsg{util::uuid4(), util::now()});
        } else if constexpr (std::is_same_v<T, MovementProofMsg>) {
            std::cout << "[server] got MovementProof " << m.proof.proof_id << "\n";
            server_send(AckMsg{m.proof.proof_id, true, std::nullopt});
        } else if constexpr (std::is_same_v<T, ChallengeResponseMsg>) {
            std::cout << "[server] got ChallengeResponse " << m.response.challenge_id << "\n";
            server_send(AckMsg{m.response.challenge_id, true, std::string("challenge cleared")});
        } else if constexpr (std::is_same_v<T, HeartbeatMsg>) {
            std::cout << "[server] got Heartbeat pos=(" << m.position.x << ","
                      << m.position.y << "," << m.position.z << ")\n";
        }
    }, *msg);
}

} // namespace ironwall
