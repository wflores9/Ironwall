#pragma once
#include "zk.hpp"
#include "anchors.hpp"
#include "tee.hpp"
#include <string>
#include <unordered_map>
#include <mutex>

namespace ironwall {

struct StoredProof {
    ZkMovementProof   proof;
    DualAnchorReceipt anchor;
    std::string       attestation_quote;
};

class ProofStore {
public:
    void insert(ZkMovementProof proof, DualAnchorReceipt anchor, const TeeAttestationResult& att);
    std::optional<StoredProof> get(const std::string& proof_id) const;
    size_t size() const;
private:
    mutable std::mutex mtx_;
    std::unordered_map<std::string, StoredProof> data_;
};

} // namespace ironwall
