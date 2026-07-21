#pragma once
#include "protocol.hpp"
#include <vector>
#include <cstdint>
#include <cstring>
#include <stdexcept>

namespace ironwall {
namespace wire {

// Frame: [magic u32][version u8][type u8][payload_len u32 LE][payload...]
// magic = 'IWAL' 0x4C415749
constexpr uint32_t kMagic = 0x4C415749;
constexpr uint8_t  kVersion = 1;

enum class MsgType : uint8_t {
    Hello = 1,
    MovementProof = 2,
    ChallengeResponse = 3,
    Heartbeat = 4,
    Welcome = 10,
    Challenge = 11,
    Ack = 12,
    Kick = 13,
};

inline void append_u8(std::vector<uint8_t>& b, uint8_t v) { b.push_back(v); }
inline void append_u32(std::vector<uint8_t>& b, uint32_t v) {
    b.push_back(v & 0xff);
    b.push_back((v >> 8) & 0xff);
    b.push_back((v >> 16) & 0xff);
    b.push_back((v >> 24) & 0xff);
}
inline void append_f32(std::vector<uint8_t>& b, float v) {
    uint32_t u;
    std::memcpy(&u, &v, 4);
    append_u32(b, u);
}
inline void append_str(std::vector<uint8_t>& b, const std::string& s) {
    append_u32(b, static_cast<uint32_t>(s.size()));
    b.insert(b.end(), s.begin(), s.end());
}

inline uint8_t read_u8(const uint8_t*& p, const uint8_t* end) {
    if (p >= end) throw std::runtime_error("wire: short u8");
    return *p++;
}
inline uint32_t read_u32(const uint8_t*& p, const uint8_t* end) {
    if (p + 4 > end) throw std::runtime_error("wire: short u32");
    uint32_t v = p[0] | (p[1]<<8) | (p[2]<<16) | (p[3]<<24);
    p += 4;
    return v;
}
inline float read_f32(const uint8_t*& p, const uint8_t* end) {
    uint32_t u = read_u32(p, end);
    float f;
    std::memcpy(&f, &u, 4);
    return f;
}
inline std::string read_str(const uint8_t*& p, const uint8_t* end) {
    uint32_t n = read_u32(p, end);
    if (p + n > end) throw std::runtime_error("wire: short str");
    std::string s(reinterpret_cast<const char*>(p), n);
    p += n;
    return s;
}

inline std::vector<uint8_t> encode_client(const ClientMessage& msg) {
    std::vector<uint8_t> payload;
    MsgType type;

    std::visit([&](auto&& m) {
        using T = std::decay_t<decltype(m)>;
        if constexpr (std::is_same_v<T, HelloMsg>) {
            type = MsgType::Hello;
            append_str(payload, m.player_id);
            append_str(payload, m.client_version);
            append_str(payload, m.attestation.quote_hash);
        } else if constexpr (std::is_same_v<T, MovementProofMsg>) {
            type = MsgType::MovementProof;
            append_str(payload, m.proof.proof_id);
            append_str(payload, m.proof.player_id);
            append_f32(payload, m.proof.from.x);
            append_f32(payload, m.proof.from.y);
            append_f32(payload, m.proof.from.z);
            append_f32(payload, m.proof.to.x);
            append_f32(payload, m.proof.to.y);
            append_f32(payload, m.proof.to.z);
            append_u32(payload, m.proof.delta_t_ms);
            append_str(payload, m.anchor.combined_hash);
        } else if constexpr (std::is_same_v<T, ChallengeResponseMsg>) {
            type = MsgType::ChallengeResponse;
            append_str(payload, m.response.challenge_id);
        } else if constexpr (std::is_same_v<T, HeartbeatMsg>) {
            type = MsgType::Heartbeat;
            append_f32(payload, m.position.x);
            append_f32(payload, m.position.y);
            append_f32(payload, m.position.z);
        }
    }, msg);

    std::vector<uint8_t> frame;
    append_u32(frame, kMagic);
    append_u8(frame, kVersion);
    append_u8(frame, static_cast<uint8_t>(type));
    append_u32(frame, static_cast<uint32_t>(payload.size()));
    frame.insert(frame.end(), payload.begin(), payload.end());
    return frame;
}

inline std::vector<uint8_t> encode_server(const ServerMessage& msg) {
    std::vector<uint8_t> payload;
    MsgType type;

    std::visit([&](auto&& m) {
        using T = std::decay_t<decltype(m)>;
        if constexpr (std::is_same_v<T, WelcomeMsg>) {
            type = MsgType::Welcome;
            append_str(payload, m.session_id);
        } else if constexpr (std::is_same_v<T, ChallengeMsg>) {
            type = MsgType::Challenge;
            append_str(payload, m.challenge.challenge_id);
            append_str(payload, m.challenge.proof_id);
            append_str(payload, m.challenge.reason);
        } else if constexpr (std::is_same_v<T, AckMsg>) {
            type = MsgType::Ack;
            append_str(payload, m.proof_id);
            append_u8(payload, m.accepted ? 1 : 0);
            append_str(payload, m.reason.value_or(""));
        } else if constexpr (std::is_same_v<T, KickMsg>) {
            type = MsgType::Kick;
            append_str(payload, m.reason);
        }
    }, msg);

    std::vector<uint8_t> frame;
    append_u32(frame, kMagic);
    append_u8(frame, kVersion);
    append_u8(frame, static_cast<uint8_t>(type));
    append_u32(frame, static_cast<uint32_t>(payload.size()));
    frame.insert(frame.end(), payload.begin(), payload.end());
    return frame;
}

// Returns nullopt on incomplete buffer; throws on corrupt
inline std::optional<ClientMessage> decode_client(const uint8_t* data, size_t len, size_t& consumed) {
    if (len < 10) return std::nullopt;
    const uint8_t* p = data;
    const uint8_t* end = data + len;
    uint32_t magic = read_u32(p, end);
    if (magic != kMagic) throw std::runtime_error("wire: bad magic");
    uint8_t ver = read_u8(p, end);
    if (ver != kVersion) throw std::runtime_error("wire: bad version");
    auto type = static_cast<MsgType>(read_u8(p, end));
    uint32_t plen = read_u32(p, end);
    if (static_cast<size_t>(end - p) < plen) return std::nullopt;
    const uint8_t* pend = p + plen;

    ClientMessage out;
    switch (type) {
        case MsgType::Hello: {
            HelloMsg m;
            m.player_id = read_str(p, pend);
            m.client_version = read_str(p, pend);
            m.attestation.quote_hash = read_str(p, pend);
            out = std::move(m);
            break;
        }
        case MsgType::MovementProof: {
            MovementProofMsg m;
            m.proof.proof_id = read_str(p, pend);
            m.proof.player_id = read_str(p, pend);
            m.proof.from.x = read_f32(p, pend);
            m.proof.from.y = read_f32(p, pend);
            m.proof.from.z = read_f32(p, pend);
            m.proof.to.x = read_f32(p, pend);
            m.proof.to.y = read_f32(p, pend);
            m.proof.to.z = read_f32(p, pend);
            m.proof.delta_t_ms = read_u32(p, pend);
            m.anchor.combined_hash = read_str(p, pend);
            out = std::move(m);
            break;
        }
        case MsgType::ChallengeResponse: {
            ChallengeResponseMsg m;
            m.response.challenge_id = read_str(p, pend);
            out = std::move(m);
            break;
        }
        case MsgType::Heartbeat: {
            HeartbeatMsg m;
            m.position.x = read_f32(p, pend);
            m.position.y = read_f32(p, pend);
            m.position.z = read_f32(p, pend);
            out = std::move(m);
            break;
        }
        default:
            throw std::runtime_error("wire: unknown client type");
    }
    consumed = static_cast<size_t>(pend - data);
    return out;
}

inline std::optional<ServerMessage> decode_server(const uint8_t* data, size_t len, size_t& consumed) {
    if (len < 10) return std::nullopt;
    const uint8_t* p = data;
    const uint8_t* end = data + len;
    uint32_t magic = read_u32(p, end);
    if (magic != kMagic) throw std::runtime_error("wire: bad magic");
    uint8_t ver = read_u8(p, end);
    if (ver != kVersion) throw std::runtime_error("wire: bad version");
    auto type = static_cast<MsgType>(read_u8(p, end));
    uint32_t plen = read_u32(p, end);
    if (static_cast<size_t>(end - p) < plen) return std::nullopt;
    const uint8_t* pend = p + plen;

    ServerMessage out;
    switch (type) {
        case MsgType::Welcome: {
            WelcomeMsg m;
            m.session_id = read_str(p, pend);
            out = std::move(m);
            break;
        }
        case MsgType::Challenge: {
            ChallengeMsg m;
            m.challenge.challenge_id = read_str(p, pend);
            m.challenge.proof_id = read_str(p, pend);
            m.challenge.reason = read_str(p, pend);
            out = std::move(m);
            break;
        }
        case MsgType::Ack: {
            AckMsg m;
            m.proof_id = read_str(p, pend);
            m.accepted = read_u8(p, pend) != 0;
            auto reason = read_str(p, pend);
            if (!reason.empty()) m.reason = reason;
            out = std::move(m);
            break;
        }
        case MsgType::Kick: {
            KickMsg m;
            m.reason = read_str(p, pend);
            out = std::move(m);
            break;
        }
        default:
            throw std::runtime_error("wire: unknown server type");
    }
    consumed = static_cast<size_t>(pend - data);
    return out;
}

} // namespace wire
} // namespace ironwall
