#pragma once
#include "zk.hpp"
#include "anchors.hpp"
#include "tee.hpp"
#include "types.hpp"
#include <string>
#include <fstream>
#include <vector>
#include <mutex>
#include <optional>

namespace ironwall {

struct RecordedEvent {
    std::string event_type;   // "attest" | "proof" | "challenge" | "heartbeat"
    std::string session_id;
    std::string player_id;
    std::string proof_id;
    std::string quote_hash;
    std::string combined_hash;
    Vec3 from{};
    Vec3 to{};
    float speed = 0.f;
    uint32_t delta_t_ms = 0;
    int64_t unix_ts = 0;
};

class MatchRecorder {
public:
    explicit MatchRecorder(std::string path);
    ~MatchRecorder();

    void record_attest(const std::string& session_id, const std::string& player_id,
                       const TeeAttestationResult& att);
    void record_proof(const std::string& session_id, const ZkMovementProof& proof,
                      const DualAnchorReceipt& anchor);
    void record_challenge(const std::string& session_id, const std::string& challenge_id);
    void record_heartbeat(const std::string& session_id, const Vec3& pos);

    // Load all events (for replay / audit)
    static std::vector<RecordedEvent> load(const std::string& path);

    const std::string& path() const { return path_; }
    uint64_t count() const { return count_; }

private:
    void write_line(const RecordedEvent& e);
    std::string path_;
    std::ofstream out_;
    std::mutex mtx_;
    uint64_t count_ = 0;
};

} // namespace ironwall
