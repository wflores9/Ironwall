#pragma once
#include "config.hpp"
#include "tee.hpp"
#include "zk.hpp"
#include "anchors.hpp"
#include "types.hpp"

namespace ironwall {

class ThinClient {
public:
    ThinClient(Config cfg, TeeAttestationResult att, ZkMovementValidator zk, DualAnchor anchors);
    void run();
    const Config& config() const { return cfg_; }
    ZkMovementValidator& zk() { return zk_; }
    DualAnchor& anchors() { return anchors_; }
private:
    Config               cfg_;
    TeeAttestationResult att_;
    ZkMovementValidator  zk_;
    DualAnchor           anchors_;
    Vec3                 position_{};
};

} // namespace ironwall
