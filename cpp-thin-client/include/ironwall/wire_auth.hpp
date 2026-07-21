#pragma once
#include "wire.hpp"
#include "hmac.hpp"
#include <string>

namespace ironwall {
namespace wire {

// Append 32-byte HMAC-SHA256 over (version|type|payload) using shared secret.
// Frame becomes: [magic][ver][type][len][payload][hmac32]
inline std::vector<uint8_t> sign_frame(std::vector<uint8_t> frame, const std::string& secret) {
    if (frame.size() < 10) return frame;
    // message = ver || type || payload
    Bytes msg;
    msg.push_back(frame[4]); // ver
    msg.push_back(frame[5]); // type
    msg.insert(msg.end(), frame.begin() + 10, frame.end());
    auto mac = crypto::hmac_sha256(Bytes(secret.begin(), secret.end()), msg);
    frame.insert(frame.end(), mac.begin(), mac.end());
    return frame;
}

// Verify and strip HMAC. Returns nullopt if bad.
inline std::optional<std::vector<uint8_t>> verify_frame(const uint8_t* data, size_t len,
                                                         const std::string& secret) {
    if (len < 10 + 32) return std::nullopt;
    size_t body_len = len - 32;
    Bytes msg;
    msg.push_back(data[4]);
    msg.push_back(data[5]);
    // payload starts at 10, length at 6..9
    uint32_t plen = data[6] | (data[7]<<8) | (data[8]<<16) | (data[9]<<24);
    if (10 + plen + 32 != len) return std::nullopt;
    msg.insert(msg.end(), data + 10, data + 10 + plen);
    Bytes expected(data + body_len, data + len);
    auto actual = crypto::hmac_sha256(Bytes(secret.begin(), secret.end()), msg);
    if (!crypto::secure_eq(expected, actual)) return std::nullopt;
    return std::vector<uint8_t>(data, data + body_len);
}

inline std::vector<uint8_t> encode_client_signed(const ClientMessage& msg, const std::string& secret) {
    return sign_frame(encode_client(msg), secret);
}

inline std::vector<uint8_t> encode_server_signed(const ServerMessage& msg, const std::string& secret) {
    return sign_frame(encode_server(msg), secret);
}

} // namespace wire
} // namespace ironwall
