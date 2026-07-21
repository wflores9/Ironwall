#pragma once
#include "ironwall/types.hpp"
#include <string>
#include <sstream>
#include <iomanip>
#include <random>
#include <chrono>
#include <cstring>
#include <vector>
#include <cstdint>

namespace ironwall {
namespace util {

inline std::string uuid4() {
    static thread_local std::mt19937_64 rng{std::random_device{}()};
    std::uniform_int_distribution<uint64_t> dist;
    uint64_t a = dist(rng), b = dist(rng);
    std::ostringstream oss;
    oss << std::hex << std::setfill('0')
        << std::setw(8) << ((a >> 32) & 0xffffffff) << "-"
        << std::setw(4) << ((a >> 16) & 0xffff) << "-"
        << std::setw(4) << (a & 0xffff) << "-"
        << std::setw(4) << ((b >> 48) & 0xffff) << "-"
        << std::setw(12) << (b & 0xffffffffffffULL);
    return oss.str();
}

class Sha256 {
public:
    Sha256() { reset(); }
    void update(const uint8_t* data, size_t len);
    void update(const std::string& s) { update(reinterpret_cast<const uint8_t*>(s.data()), s.size()); }
    void update(const std::vector<uint8_t>& v) { update(v.data(), v.size()); }
    std::vector<uint8_t> digest();
    std::string hexdigest();
private:
    void reset();
    void transform(const uint8_t* chunk);
    uint32_t state_[8];
    uint64_t bitlen_;
    uint8_t buffer_[64];
    size_t buf_len_;
};

inline std::string to_hex(const std::vector<uint8_t>& bytes) {
    std::ostringstream oss;
    oss << std::hex << std::setfill('0');
    for (auto b : bytes) oss << std::setw(2) << static_cast<int>(b);
    return oss.str();
}

inline TimePoint now() { return std::chrono::system_clock::now(); }

} // namespace util
} // namespace ironwall
