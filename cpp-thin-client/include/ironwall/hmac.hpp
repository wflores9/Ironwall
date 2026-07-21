#pragma once
#include "types.hpp"
#include <string>
#include <vector>
#include <cstdint>

namespace ironwall {
namespace crypto {

// HMAC-SHA256 (compact, no external dep)
Bytes hmac_sha256(const Bytes& key, const Bytes& msg);
std::string hmac_sha256_hex(const std::string& key, const Bytes& msg);

// Constant-time compare
bool secure_eq(const Bytes& a, const Bytes& b);

} // namespace crypto
} // namespace ironwall
