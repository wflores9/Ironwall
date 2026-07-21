#pragma once
#include "types.hpp"
#include "tee.hpp"
#include "zk.hpp"
#include <string>

namespace ironwall {

struct HcsReceipt {
    std::string topic_id;
    std::string message_id;
    uint64_t    sequence_number = 0;
    std::string payload_hash;
    TimePoint   consensus_timestamp;
};

struct XrplReceipt {
    std::string account;
    std::string tx_hash;
    uint32_t    ledger_index = 0;
    TimePoint   timestamp;
};

struct DualAnchorReceipt {
    HcsReceipt  hcs;
    XrplReceipt xrpl;
    std::string combined_hash;
};

class HcsAnchor {
public:
    explicit HcsAnchor(std::string topic_id);
    HcsReceipt submit(const Bytes& payload) const;
private:
    std::string topic_id_;
};

class XrplAnchor {
public:
    explicit XrplAnchor(std::string account);
    XrplReceipt submit(const Bytes& payload) const;
private:
    std::string account_;
};

class DualAnchor {
public:
    DualAnchor(HcsAnchor hcs, XrplAnchor xrpl);
    DualAnchorReceipt anchor(const TeeAttestationResult& att,
                             const ZkMovementProof& proof) const;
private:
    HcsAnchor  hcs_;
    XrplAnchor xrpl_;
};

} // namespace ironwall
