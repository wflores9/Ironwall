#pragma once
#include "config.hpp"
#include <string>
#include <fstream>
#include <sstream>
#include <iostream>

namespace ironwall {

// Minimal JSON-ish config loader (no external deps)
// Supports simple key: value lines or basic {"key": "value"} 
inline Config load_config(const std::string& path) {
    Config cfg;
    std::ifstream in(path);
    if (!in) {
        std::cerr << "[config] using defaults (file not found: " << path << ")\n";
        return cfg;
    }
    std::string line;
    while (std::getline(in, line)) {
        // strip comments
        auto hash = line.find('#');
        if (hash != std::string::npos) line = line.substr(0, hash);
        auto colon = line.find(':');
        if (colon == std::string::npos) continue;
        std::string key = line.substr(0, colon);
        std::string val = line.substr(colon + 1);
        // trim
        auto trim = [](std::string& s) {
            while (!s.empty() && (s.front()==' '||s.front()=='"'||s.front()=='\t')) s.erase(s.begin());
            while (!s.empty() && (s.back()==' '||s.back()=='"'||s.back()==','||s.back()=='\r')) s.pop_back();
        };
        trim(key); trim(val);
        if (key == "player_id") cfg.player_id = val;
        else if (key == "hcs_topic_id") cfg.hcs_topic_id = val;
        else if (key == "xrpl_account") cfg.xrpl_account = val;
        else if (key == "tick_rate_hz") cfg.tick_rate_hz = static_cast<uint32_t>(std::stoul(val));
        else if (key == "max_speed") cfg.max_speed = std::stof(val);
        else if (key == "demo_ticks") cfg.demo_ticks = std::stoull(val);
    }
    return cfg;
}

inline void save_config_example(const std::string& path) {
    std::ofstream out(path);
    out << "# Ironwall thin client config\n"
        << "player_id: player_001\n"
        << "hcs_topic_id: 0.0.123456\n"
        << "xrpl_account: rIronwallAnchorXXXXXXXXXXXXXXXXXX\n"
        << "tick_rate_hz: 60\n"
        << "max_speed: 10.0\n"
        << "demo_ticks: 5\n";
}

} // namespace ironwall
