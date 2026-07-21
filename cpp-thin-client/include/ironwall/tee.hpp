#pragma once
#include "types.hpp"
#include <string>

namespace ironwall {

struct TeeAttestationResult {
    std::string quote_id;
    std::string quote_hash;
    Bytes       report_data;
    TimePoint   timestamp;
    std::string mr_enclave;
    std::string mr_signer;
};

class TeeAttestation {
public:
    TeeAttestation() = default;
    TeeAttestationResult generate() const;
};

} // namespace ironwall
