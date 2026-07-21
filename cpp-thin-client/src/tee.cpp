#include "ironwall/tee.hpp"
#include "util.hpp"
#include <cstring>

namespace ironwall {

TeeAttestationResult TeeAttestation::generate() const {
    TeeAttestationResult r;
    r.quote_id = util::uuid4();
    r.report_data.assign(reinterpret_cast<const uint8_t*>("ironwall-tee-report-data-v1"),
                         reinterpret_cast<const uint8_t*>("ironwall-tee-report-data-v1") + 26);
    r.timestamp = util::now();
    r.mr_enclave = std::string(64, '0');
    r.mr_signer  = std::string(64, '0');

    util::Sha256 h;
    h.update(r.quote_id);
    h.update(r.report_data);
    auto ts = std::chrono::system_clock::to_time_t(r.timestamp);
    h.update(reinterpret_cast<const uint8_t*>(&ts), sizeof(ts));
    r.quote_hash = h.hexdigest();
    return r;
}

} // namespace ironwall
