#include "ironwall/matchmaker.hpp"
#include "util.hpp"
#include <iostream>

namespace ironwall {

static int64_t unix_now() {
    return std::chrono::duration_cast<std::chrono::seconds>(
        std::chrono::system_clock::now().time_since_epoch()).count();
}

Matchmaker::Matchmaker(MatchmakerConfig cfg)
    : cfg_(std::move(cfg))
    , lobby_(cfg_.lobby)
    , mod_(cfg_.rate)
    , bans_(cfg_.ban_path)
{
    bans_.load_into(mod_);
}

std::string Matchmaker::enqueue(const SessionTicket& ticket) {
    if (!lobby_.validate_ticket(ticket)) {
        std::cerr << "[mm] reject invalid ticket player=" << ticket.player_id << "\n";
        return {};
    }
    if (!mod_.allow(ticket.player_id, "enqueue")) {
        std::cerr << "[mm] reject moderated player=" << ticket.player_id << "\n";
        return {};
    }
    auto sid = lobby_.open_session(ticket);
    if (sid.empty()) return {};
    std::lock_guard lock(mtx_);
    queue_.push(sid);
    std::cerr << "[mm] enqueued session=" << sid << " queue=" << queue_.size() << "\n";
    return sid;
}

std::vector<Match> Matchmaker::tick() {
    std::lock_guard lock(mtx_);
    std::vector<Match> created;
    while (queue_.size() >= cfg_.players_per_match) {
        Match m;
        m.match_id = util::uuid4();
        m.created_unix = unix_now();
        for (size_t i = 0; i < cfg_.players_per_match; ++i) {
            m.players.push_back(queue_.front());
            queue_.pop();
        }
        matches_[m.match_id] = m;
        created.push_back(m);
        std::cerr << "[mm] match formed " << m.match_id << " players=" << m.players.size() << "\n";
    }
    return created;
}

std::optional<Match> Matchmaker::get_match(const std::string& match_id) const {
    std::lock_guard lock(mtx_);
    auto it = matches_.find(match_id);
    if (it == matches_.end()) return std::nullopt;
    return it->second;
}

size_t Matchmaker::queue_size() const {
    std::lock_guard lock(mtx_);
    return queue_.size();
}

size_t Matchmaker::active_matches() const {
    std::lock_guard lock(mtx_);
    return matches_.size();
}

} // namespace ironwall
