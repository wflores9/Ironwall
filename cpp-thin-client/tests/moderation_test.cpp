#include "ironwall/moderation.hpp"
#include <cassert>
#include <iostream>
#include <thread>
#include <chrono>

int main() {
    using namespace ironwall;
    RateLimitConfig cfg;
    cfg.max_events = 3;
    cfg.window_sec = 1.0;
    cfg.ban_after_violations = 2;
    cfg.ban_duration_sec = 2.0;
    ModerationEngine mod(cfg);

    assert(mod.allow("a", "p"));
    assert(mod.allow("a", "p"));
    assert(mod.allow("a", "p"));
    assert(!mod.allow("a", "p")); // 4th in window -> strike
    assert(!mod.allow("a", "p")); // another -> ban
    assert(mod.is_banned("a"));

    mod.unban("a");
    assert(!mod.is_banned("a"));
    assert(mod.allow("a", "p"));

    std::cout << "moderation_test OK\n";
    return 0;
}
