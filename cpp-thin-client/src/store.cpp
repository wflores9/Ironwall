#include "ironwall/store.hpp"
#include <iostream>

namespace ironwall {

void ProofStore::insert(ZkMovementProof proof, DualAnchorReceipt anchor, const TeeAttestationResult& att) {
    std::lock_guard lock(mtx_);
    std::string id = proof.proof_id;
    data_[id] = StoredProof{std::move(proof), std::move(anchor), att.quote_hash};
    std::cout << "[store] stored proof " << id << "\n";
}

std::optional<StoredProof> ProofStore::get(const std::string& proof_id) const {
    std::lock_guard lock(mtx_);
    auto it = data_.find(proof_id);
    if (it == data_.end()) return std::nullopt;
    return it->second;
}

size_t ProofStore::size() const {
    std::lock_guard lock(mtx_);
    return data_.size();
}

} // namespace ironwall
