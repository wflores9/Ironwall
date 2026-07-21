#include "ironwall/anchors.hpp"
#include "util.hpp"

namespace ironwall {

HcsAnchor::HcsAnchor(std::string topic_id) : topic_id_(std::move(topic_id)) {}

HcsReceipt HcsAnchor::submit(const Bytes& payload) const {
    HcsReceipt r;
    r.topic_id = topic_id_;
    r.message_id = util::uuid4();
    r.sequence_number = 0;
    r.consensus_timestamp = util::now();
    util::Sha256 h;
    h.update(payload);
    r.payload_hash = h.hexdigest();
    return r;
}

XrplAnchor::XrplAnchor(std::string account) : account_(std::move(account)) {}

XrplReceipt XrplAnchor::submit(const Bytes& payload) const {
    XrplReceipt r;
    r.account = account_;
    r.ledger_index = 0;
    r.timestamp = util::now();
    util::Sha256 h;
    h.update("xrpl-ironwall-anchor");
    h.update(payload);
    r.tx_hash = h.hexdigest();
    return r;
}

DualAnchor::DualAnchor(HcsAnchor hcs, XrplAnchor xrpl)
    : hcs_(std::move(hcs)), xrpl_(std::move(xrpl)) {}

DualAnchorReceipt DualAnchor::anchor(const TeeAttestationResult& att,
                                     const ZkMovementProof& proof) const {
    Bytes payload;
    payload.insert(payload.end(), att.quote_hash.begin(), att.quote_hash.end());
    payload.insert(payload.end(), proof.public_inputs_hash.begin(), proof.public_inputs_hash.end());
    payload.insert(payload.end(), proof.proof_id.begin(), proof.proof_id.end());

    DualAnchorReceipt r;
    r.hcs  = hcs_.submit(payload);
    r.xrpl = xrpl_.submit(payload);

    util::Sha256 h;
    h.update(r.hcs.payload_hash);
    h.update(r.xrpl.tx_hash);
    r.combined_hash = h.hexdigest();
    return r;
}

} // namespace ironwall
