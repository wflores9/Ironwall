#include <cmath>
#pragma once
#include <string>
#include <vector>
#include <array>
#include <cstdint>
#include <chrono>

namespace ironwall {

using TimePoint = std::chrono::system_clock::time_point;
using Bytes = std::vector<uint8_t>;

struct Vec3 {
    float x = 0.f, y = 0.f, z = 0.f;
};

inline float distance(const Vec3& a, const Vec3& b) {
    float dx = b.x - a.x, dy = b.y - a.y, dz = b.z - a.z;
    return std::sqrt(dx*dx + dy*dy + dz*dz);
}

} // namespace ironwall
