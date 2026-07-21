#include "ironwall/hmac.hpp"
#include "util.hpp"
#include <cstring>

namespace ironwall {
namespace crypto {

Bytes hmac_sha256(const Bytes& key, const Bytes& msg) {
    constexpr size_t BS = 64;
    Bytes k(BS, 0);
    if (key.size() > BS) {
        util::Sha256 h;
        h.update(key);
        auto d = h.digest();
        std::copy(d.begin(), d.end(), k.begin());
    } else {
        std::copy(key.begin(), key.end(), k.begin());
    }

    Bytes ipad(BS), opad(BS);
    for (size_t i = 0; i < BS; ++i) {
        ipad[i] = k[i] ^ 0x36;
        opad[i] = k[i] ^ 0x5c;
    }

    util::Sha256 inner;
    inner.update(ipad);
    inner.update(msg);
    auto idig = inner.digest();

    util::Sha256 outer;
    outer.update(opad);
    outer.update(idig);
    return outer.digest();
}

std::string hmac_sha256_hex(const std::string& key, const Bytes& msg) {
    Bytes k(key.begin(), key.end());
    return util::to_hex(hmac_sha256(k, msg));
}

bool secure_eq(const Bytes& a, const Bytes& b) {
    if (a.size() != b.size()) return false;
    unsigned char d = 0;
    for (size_t i = 0; i < a.size(); ++i) d |= a[i] ^ b[i];
    return d == 0;
}

} // namespace crypto
} // namespace ironwall
