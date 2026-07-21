#include "ironwall/udp_net.hpp"
#include <cassert>
#include <iostream>
#include <vector>
#include <string>

int main() {
    using namespace ironwall;
    std::vector<uint8_t> payload(std::begin({'I','W','A','L'}), std::end({'I','W','A','L'}));
    // fix init
    payload = {'I','W','A','L','-','U','D','P'};
    std::vector<uint8_t> resp;
    assert(udp_echo_demo(payload, resp));
    assert(resp.size() > payload.size());
    std::cout << "udp_test OK resp_len=" << resp.size() << "\n";
    return 0;
}
