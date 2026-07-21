#pragma once
#include "moderation.hpp"
#include <string>
#include <fstream>
#include <sstream>
#include <iostream>
#include <ctime>

namespace ironwall {

// Simple JSON-lines ban store (no deps)
// each line: {"player":"...","reason":"...","until_unix":123}
class BanStore {
public:
    explicit BanStore(std::string path);

    void load_into(ModerationEngine& mod);
    void save_ban(const std::string& player, const std::string& reason, double duration_sec);
    void save_unban(const std::string& player);
    const std::string& path() const { return path_; }

private:
    std::string path_;
    void append_line(const std::string& line);
};

} // namespace ironwall
