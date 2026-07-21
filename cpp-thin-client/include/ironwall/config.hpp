#pragma once
#include <string>
#include <cstdint>

namespace ironwall {

struct Config {
    std::string player_id        = "player_001";
    std::string hcs_topic_id     = "0.0.123456";
    std::string xrpl_account     = "rIronwallAnchorXXXXXXXXXXXXXXXXXX";
    uint32_t    tick_rate_hz     = 60;
    float       max_speed        = 10.0f;
    uint64_t    demo_ticks       = 5;
};

} // namespace ironwall
