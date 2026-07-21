#include "ironwall/recorder.hpp"
#include <iostream>
#include <iomanip>

int main(int argc, char** argv) {
    using namespace ironwall;
    std::string path = argc > 1 ? argv[1] : "ironwall_match.tsv";
    auto events = MatchRecorder::load(path);
    std::cout << "Loaded " << events.size() << " events from " << path << "\n\n";

    uint64_t proofs = 0, challenges = 0, heartbeats = 0, attests = 0;
    for (auto& e : events) {
        if (e.event_type == "attest") ++attests;
        else if (e.event_type == "proof") ++proofs;
        else if (e.event_type == "challenge") ++challenges;
        else if (e.event_type == "heartbeat") ++heartbeats;

        std::cout << std::setw(10) << e.event_type
                  << "  session=" << e.session_id.substr(0, 8)
                  << "  player=" << e.player_id
                  << "  proof=" << (e.proof_id.empty() ? "-" : e.proof_id.substr(0, 8));
        if (e.event_type == "proof") {
            std::cout << "  speed=" << std::fixed << std::setprecision(2) << e.speed
                      << "  hash=" << e.combined_hash.substr(0, 12) << "...";
        }
        std::cout << "\n";
    }
    std::cout << "\nSummary: attest=" << attests
              << " proof=" << proofs
              << " challenge=" << challenges
              << " heartbeat=" << heartbeats << "\n";
    return 0;
}
