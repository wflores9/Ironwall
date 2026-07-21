#pragma once
#include "lobby.hpp"
#include "moderation.hpp"
#include "ban_store.hpp"
#include <string>
#include <vector>
#include <queue>
#include <mutex>
#include <optional>
#include <chrono>

namespace ironwall {

struct Match {
    std::string match_id;
    std::vector<std::string> players; // session_ids
    int64_t created_unix = 0;
};

struct MatchmakerConfig {
    size_t players_per_match = 2;
    LobbyConfig lobby;
    RateLimitConfig rate;
    std::string ban_path = "ironwall_bans.jsonl";
};

class Matchmaker {
public:
    explicit Matchmaker(MatchmakerConfig cfg = {});

    // Player presents ticket -> session_id or empty on reject
    std::string enqueue(const SessionTicket& ticket);

    // Try form matches from queue; returns newly created matches
    std::vector<Match> tick();

    std::optional<Match> get_match(const std::string& match_id) const;
    size_t queue_size() const;
    size_t active_matches() const;
    Lobby& lobby() { return lobby_; }
    ModerationEngine& moderation() { return mod_; }

private:
    MatchmakerConfig cfg_;
    Lobby lobby_;
    ModerationEngine mod_;
    BanStore bans_;
    mutable std::mutex mtx_;
    std::queue<std::string> queue_; // session_ids
    std::unordered_map<std::string, Match> matches_;
};

} // namespace ironwall
