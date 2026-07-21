#include "ironwall/wire.hpp"
#include "ironwall/wire_auth.hpp"
#include "ironwall/protocol.hpp"
#include <iostream>
#include <cassert>
#include <cstring>

int main() {
    using namespace ironwall;
    const std::string secret = "ironwall-dev-secret";

    HelloMsg hello;
    hello.player_id = "p1";
    hello.client_version = "0.1.0";
    hello.attestation.quote_hash = "abc123";

    auto signed_frame = wire::encode_client_signed(hello, secret);
    assert(signed_frame.size() >= 10 + 32);

    auto verified = wire::verify_frame(signed_frame.data(), signed_frame.size(), secret);
    assert(verified.has_value());

    // tamper
    auto bad = signed_frame;
    bad[12] ^= 0xff;
    auto rejected = wire::verify_frame(bad.data(), bad.size(), secret);
    assert(!rejected.has_value());

    // wrong secret
    auto wrong = wire::verify_frame(signed_frame.data(), signed_frame.size(), "wrong");
    assert(!wrong.has_value());

    size_t consumed = 0;
    auto decoded = wire::decode_client(verified->data(), verified->size(), consumed);
    assert(decoded.has_value());
    auto* h = std::get_if<HelloMsg>(&*decoded);
    assert(h && h->player_id == "p1");

    std::cout << "wire_auth_test OK (sign/verify/tamper/wrong-secret)\n";
    return 0;
}
