#pragma once
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <mutex>
#include <chrono>
#include <deque>
#include <vector>

namespace ironwall {

struct RateLimitConfig {
    size_t max_events = 30;          // max events
    double window_sec = 10.0;        // per window
    size_t ban_after_violations = 3; // strikes
    double ban_duration_sec = 300.0; // 5 min
};

class ModerationEngine {
public:
    explicit ModerationEngine(RateLimitConfig cfg = {});

    // returns true if allowed, false if rate-limited or banned
    bool allow(const std::string& player_id, const std::string& event_type);

    void ban(const std::string& player_id, const std::string& reason);
    void unban(const std::string& player_id);
    bool is_banned(const std::string& player_id) const;

    std::vector<std::string> banned_players() const;
    size_t strike_count(const std::string& player_id) const;

private:
    using Clock = std::chrono::steady_clock;
    RateLimitConfig cfg_;
    mutable std::mutex mtx_;
    std::unordered_map<std::string, std::deque<Clock::time_point>> windows_;
    std::unordered_map<std::string, size_t> strikes_;
    std::unordered_map<std::string, Clock::time_point> bans_; // until
    std::unordered_map<std::string, std::string> ban_reasons_;
};

} // namespace ironwall
