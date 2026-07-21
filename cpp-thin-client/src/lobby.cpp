#include "ironwall/lobby.hpp"
#include "util.hpp"
#include <sstream>
#include <iostream>

namespace ironwall {

static int64_t unix_now() {
    return std::chrono::duration_cast<std::chrono::seconds>(
        std::chrono::system_clock::now().time_since_epoch()).count();
}

Lobby::Lobby(LobbyConfig cfg) : cfg_(std::move(cfg)) {}

SessionTicket Lobby::issue_ticket(const std::string& player_id, const TeeAttestationResult& att) {
    SessionTicket t;
    t.ticket_id = util::uuid4();
    t.player_id = player_id;
    t.quote_hash = att.quote_hash;
    t.issued_unix = unix_now();
    t.expires_unix = t.issued_unix + cfg_.ticket_ttl_sec;

    std::string msg = t.ticket_id + "|" + t.player_id + "|" + t.quote_hash + "|" +
                      std::to_string(t.issued_unix) + "|" + std::to_string(t.expires_unix);
    Bytes b(msg.begin(), msg.end());
    t.hmac_hex = crypto::hmac_sha256_hex(cfg_.shared_secret, b);
    return t;
}

bool Lobby::validate_ticket(const SessionTicket& t) const {
    if (unix_now() > t.expires_unix) {
        std::cerr << "[lobby] ticket expired\n";
        return false;
    }
    std::string msg = t.ticket_id + "|" + t.player_id + "|" + t.quote_hash + "|" +
                      std::to_string(t.issued_unix) + "|" + std::to_string(t.expires_unix);
    Bytes b(msg.begin(), msg.end());
    auto expect = crypto::hmac_sha256_hex(cfg_.shared_secret, b);
    if (expect != t.hmac_hex) {
        std::cerr << "[lobby] ticket HMAC invalid\n";
        return false;
    }
    return true;
}

std::vector<uint8_t> Lobby::make_hello_frame(const std::string& player_id,
                                             const std::string& version,
                                             const TeeAttestationResult& att) const {
    HelloMsg h;
    h.player_id = player_id;
    h.client_version = version;
    h.attestation = att;
    return wire::encode_client_signed(h, cfg_.shared_secret);
}

std::vector<uint8_t> Lobby::make_welcome_frame(const std::string& session_id) const {
    WelcomeMsg w;
    w.session_id = session_id;
    w.server_time = util::now();
    return wire::encode_server_signed(w, cfg_.shared_secret);
}

std::string Lobby::open_session(const SessionTicket& t) {
    if (!validate_ticket(t)) return {};
    std::lock_guard lock(mtx_);
    std::string sid = util::uuid4();
    sessions_[sid] = t;
    std::cerr << "[lobby] session opened " << sid << " player=" << t.player_id << "\n";
    return sid;
}

void Lobby::close_session(const std::string& session_id) {
    std::lock_guard lock(mtx_);
    sessions_.erase(session_id);
    std::cerr << "[lobby] session closed " << session_id << "\n";
}

bool Lobby::session_active(const std::string& session_id) const {
    std::lock_guard lock(mtx_);
    return sessions_.count(session_id) > 0;
}

size_t Lobby::active_count() const {
    std::lock_guard lock(mtx_);
    return sessions_.size();
}

} // namespace ironwall
