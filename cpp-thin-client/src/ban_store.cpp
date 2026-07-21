#include "ironwall/ban_store.hpp"
#include <chrono>

namespace ironwall {

static int64_t unix_now() {
    return std::chrono::duration_cast<std::chrono::seconds>(
        std::chrono::system_clock::now().time_since_epoch()).count();
}

BanStore::BanStore(std::string path) : path_(std::move(path)) {}

void BanStore::append_line(const std::string& line) {
    std::ofstream out(path_, std::ios::app);
    if (out) out << line << "\n";
}

void BanStore::save_ban(const std::string& player, const std::string& reason, double duration_sec) {
    int64_t until = unix_now() + static_cast<int64_t>(duration_sec);
    std::ostringstream ss;
    ss << "{\"op\":\"ban\",\"player\":\"" << player
       << "\",\"reason\":\"" << reason
       << "\",\"until_unix\":" << until << "}";
    append_line(ss.str());
}

void BanStore::save_unban(const std::string& player) {
    std::ostringstream ss;
    ss << "{\"op\":\"unban\",\"player\":\"" << player << "\"}";
    append_line(ss.str());
}

void BanStore::load_into(ModerationEngine& mod) {
    std::ifstream in(path_);
    if (!in) {
        std::cerr << "[ban_store] no file " << path_ << " (starting empty)\n";
        return;
    }
    std::string line;
    int loaded = 0;
    while (std::getline(in, line)) {
        if (line.find("\"op\":\"ban\"") != std::string::npos) {
            // crude extract player
            auto p0 = line.find("\"player\":\"");
            if (p0 == std::string::npos) continue;
            p0 += 10;
            auto p1 = line.find('"', p0);
            std::string player = line.substr(p0, p1 - p0);

            auto r0 = line.find("\"reason\":\"");
            std::string reason = "persisted";
            if (r0 != std::string::npos) {
                r0 += 10;
                auto r1 = line.find('"', r0);
                reason = line.substr(r0, r1 - r0);
            }

            auto u0 = line.find("\"until_unix\":");
            int64_t until = 0;
            if (u0 != std::string::npos) until = std::stoll(line.substr(u0 + 13));

            if (until > unix_now()) {
                mod.ban(player, reason + " (persisted)");
                ++loaded;
            }
        } else if (line.find("\"op\":\"unban\"") != std::string::npos) {
            auto p0 = line.find("\"player\":\"");
            if (p0 == std::string::npos) continue;
            p0 += 10;
            auto p1 = line.find('"', p0);
            mod.unban(line.substr(p0, p1 - p0));
        }
    }
    std::cerr << "[ban_store] loaded " << loaded << " active bans from " << path_ << "\n";
}

} // namespace ironwall
