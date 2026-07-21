#include "ironwall/zk.hpp"
#include <iostream>
#include <cassert>

int main() {
    using namespace ironwall;
    ZkMovementValidator zk(10.0f);

    auto p = zk.prove("p1", {0,0,0}, {0.1f,0,0}, 50);
    assert(p.speed < 10.0f);
    std::cout << "valid_slow_movement_passes OK\n";

    bool rejected = false;
    try {
        zk.prove("p1", {0,0,0}, {100.f,0,0}, 16);
    } catch (const InvalidMovement&) {
        rejected = true;
    }
    assert(rejected);
    std::cout << "speedhack_is_rejected OK\n";
    std::cout << "All tests passed\n";
    return 0;
}
