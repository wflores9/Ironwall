#include "ironwall/recorder.hpp"
#include "util.hpp"
#include <sstream>
#include <iostream>
#include <ctime>

namespace ironwall {

static int64_t unix_now() {
    return std::chrono::duration_cast<std::chrono::seconds>(
        std::chrono::system_clock::now().time_since_epoch()).count();
}

MatchRecorder::MatchRecorder(std::string path) : path_(std::move(path)) {
    out_.open(path_, std::ios::app);
    if (!out_) {
        std::cerr << "[recorder] failed to open " << path_ << "\n";
    } else {
        std::cerr << "[recorder] writing to " << path_ << "\n";
    }
}

MatchRecorder::~MatchRecorder() {
    if (out_) out_.flush();
}

void MatchRecorder::write_line(const RecordedEvent& e) {
    std::lock_guard lock(mtx_);
    if (!out_) return;
    // TSV: type session player proof quote combined fromx fromy fromz tox toy toz speed dt ts
    out_ << e.event_type << '\t'
         << e.session_id << '\t'
         << e.player_id << '\t'
         << e.proof_id << '\t'
         << e.quote_hash << '\t'
         << e.combined_hash << '\t'
         << e.from.x << '\t' << e.from.y << '\t' << e.from.z << '\t'
         << e.to.x << '\t' << e.to.y << '\t' << e.to.z << '\t'
         << e.speed << '\t'
         << e.delta_t_ms << '\t'
         << e.unix_ts << '\n';
    out_.flush();
    ++count_;
}

void MatchRecorder::record_attest(const std::string& session_id, const std::string& player_id,
                                  const TeeAttestationResult& att) {
    RecordedEvent e;
    e.event_type = "attest";
    e.session_id = session_id;
    e.player_id = player_id;
    e.quote_hash = att.quote_hash;
    e.unix_ts = unix_now();
    write_line(e);
}

void MatchRecorder::record_proof(const std::string& session_id, const ZkMovementProof& proof,
                                 const DualAnchorReceipt& anchor) {
    RecordedEvent e;
    e.event_type = "proof";
    e.session_id = session_id;
    e.player_id = proof.player_id;
    e.proof_id = proof.proof_id;
    e.combined_hash = anchor.combined_hash;
    e.from = proof.from;
    e.to = proof.to;
    e.speed = proof.speed;
    e.delta_t_ms = proof.delta_t_ms;
    e.unix_ts = unix_now();
    write_line(e);
}

void MatchRecorder::record_challenge(const std::string& session_id, const std::string& challenge_id) {
    RecordedEvent e;
    e.event_type = "challenge";
    e.session_id = session_id;
    e.proof_id = challenge_id;
    e.unix_ts = unix_now();
    write_line(e);
}

void MatchRecorder::record_heartbeat(const std::string& session_id, const Vec3& pos) {
    RecordedEvent e;
    e.event_type = "heartbeat";
    e.session_id = session_id;
    e.to = pos;
    e.unix_ts = unix_now();
    write_line(e);
}

std::vector<RecordedEvent> MatchRecorder::load(const std::string& path) {
    std::vector<RecordedEvent> out;
    std::ifstream in(path);
    if (!in) return out;
    std::string line;
    while (std::getline(in, line)) {
        if (line.empty()) continue;
        std::istringstream ss(line);
        RecordedEvent e;
        std::string tok;
        auto next = [&](auto& field) {
            if (!std::getline(ss, tok, '\t')) return false;
            if constexpr (std::is_same_v<std::decay_t<decltype(field)>, std::string>)
                field = tok;
            else if constexpr (std::is_same_v<std::decay_t<decltype(field)>, float>)
                field = std::stof(tok);
            else if constexpr (std::is_same_v<std::decay_t<decltype(field)>, uint32_t>)
                field = static_cast<uint32_t>(std::stoul(tok));
            else if constexpr (std::is_same_v<std::decay_t<decltype(field)>, int64_t>)
                field = std::stoll(tok);
            return true;
        };
        next(e.event_type);
        next(e.session_id);
        next(e.player_id);
        next(e.proof_id);
        next(e.quote_hash);
        next(e.combined_hash);
        next(e.from.x); next(e.from.y); next(e.from.z);
        next(e.to.x); next(e.to.y); next(e.to.z);
        next(e.speed);
        next(e.delta_t_ms);
        next(e.unix_ts);
        out.push_back(std::move(e));
    }
    return out;
}

} // namespace ironwall
