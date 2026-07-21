#include "ironwall/moderation.hpp"
#include <iostream>

namespace ironwall {

ModerationEngine::ModerationEngine(RateLimitConfig cfg) : cfg_(std::move(cfg)) {}

bool ModerationEngine::allow(const std::string& player_id, const std::string& event_type) {
    std::lock_guard lock(mtx_);
    auto now = Clock::now();

    // expire ban?
    if (auto it = bans_.find(player_id); it != bans_.end()) {
        if (now < it->second) {
            std::cerr << "[mod] DENY banned player=" << player_id
                      << " reason=" << ban_reasons_[player_id] << "\n";
            return false;
        }
        bans_.erase(it);
        ban_reasons_.erase(player_id);
    }

    auto& q = windows_[player_id];
    auto window = std::chrono::duration<double>(cfg_.window_sec);
    while (!q.empty() && (now - q.front()) > window) q.pop_front();
    q.push_back(now);

    if (q.size() > cfg_.max_events) {
        size_t& s = strikes_[player_id];
        ++s;
        std::cerr << "[mod] RATE LIMIT player=" << player_id
                  << " event=" << event_type
                  << " count=" << q.size()
                  << " strike=" << s << "\n";
        if (s >= cfg_.ban_after_violations) {
            bans_[player_id] = now + std::chrono::duration_cast<Clock::duration>(
                std::chrono::duration<double>(cfg_.ban_duration_sec));
            ban_reasons_[player_id] = "rate_limit";
            std::cerr << "[mod] BAN player=" << player_id << " for "
                      << cfg_.ban_duration_sec << "s\n";
        }
        return false;
    }
    return true;
}

void ModerationEngine::ban(const std::string& player_id, const std::string& reason) {
    std::lock_guard lock(mtx_);
    bans_[player_id] = Clock::now() + std::chrono::duration_cast<Clock::duration>(
        std::chrono::duration<double>(cfg_.ban_duration_sec));
    ban_reasons_[player_id] = reason;
    std::cerr << "[mod] MANUAL BAN player=" << player_id << " reason=" << reason << "\n";
}

void ModerationEngine::unban(const std::string& player_id) {
    std::lock_guard lock(mtx_);
    bans_.erase(player_id);
    ban_reasons_.erase(player_id);
    strikes_.erase(player_id);
    windows_.erase(player_id);
}

bool ModerationEngine::is_banned(const std::string& player_id) const {
    std::lock_guard lock(mtx_);
    auto it = bans_.find(player_id);
    if (it == bans_.end()) return false;
    return Clock::now() < it->second;
}

std::vector<std::string> ModerationEngine::banned_players() const {
    std::lock_guard lock(mtx_);
    std::vector<std::string> out;
    auto now = Clock::now();
    for (auto& [id, until] : bans_) {
        if (now < until) out.push_back(id);
    }
    return out;
}

size_t ModerationEngine::strike_count(const std::string& player_id) const {
    std::lock_guard lock(mtx_);
    auto it = strikes_.find(player_id);
    return it == strikes_.end() ? 0 : it->second;
}

} // namespace ironwall
