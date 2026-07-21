#pragma once
#include "types.hpp"
#include "hmac.hpp"
#include "wire.hpp"
#include "wire_auth.hpp"
#include "protocol.hpp"
#include "tee.hpp"
#include <string>
#include <optional>
#include <unordered_map>
#include <mutex>
#include <chrono>

namespace ironwall {

struct SessionTicket {
    std::string ticket_id;
    std::string player_id;
    std::string quote_hash;
    int64_t     issued_unix = 0;
    int64_t     expires_unix = 0;
    std::string hmac_hex;   // over ticket fields
};

struct LobbyConfig {
    std::string shared_secret = "ironwall-lobby-dev-secret";
    int64_t ticket_ttl_sec = 300;
};

class Lobby {
public:
    explicit Lobby(LobbyConfig cfg = {});

    // Client-side: build Hello + request ticket material
    SessionTicket issue_ticket(const std::string& player_id, const TeeAttestationResult& att);

    // Server-side: validate ticket HMAC + expiry
    bool validate_ticket(const SessionTicket& t) const;

    // Full handshake helpers using IWAL frames
    std::vector<uint8_t> make_hello_frame(const std::string& player_id,
                                          const std::string& version,
                                          const TeeAttestationResult& att) const;
    std::vector<uint8_t> make_welcome_frame(const std::string& session_id) const;

    // Track active sessions
    std::string open_session(const SessionTicket& t);
    void close_session(const std::string& session_id);
    bool session_active(const std::string& session_id) const;
    size_t active_count() const;

private:
    LobbyConfig cfg_;
    mutable std::mutex mtx_;
    std::unordered_map<std::string, SessionTicket> sessions_; // session_id -> ticket
};

} // namespace ironwall
