#include "ironwall/chain_submit.hpp"
#include "ironwall/tee.hpp"
#include "ironwall/zk.hpp"
#include <iostream>
#include <cstdlib>

int main() {
    using namespace ironwall;
    std::cout << "Ironwall chain smoke test\n";

    ChainConfig cfg;
    // Optional: load from env
    if (const char* v = std::getenv("HEDERA_OPERATOR_ID")) cfg.hedera_operator_id = v;
    if (const char* v = std::getenv("HCS_TOPIC_ID")) cfg.hcs_topic_id = v;
    if (const char* v = std::getenv("XRPL_SEED")) cfg.xrpl_seed = v;
    if (const char* v = std::getenv("XRPL_ACCOUNT")) cfg.xrpl_account = v;

    ChainSubmitter sub(cfg);
    std::cout << "live_mode=" << (sub.live_mode() ? "yes" : "no (sim)") << "\n";

    TeeAttestation tee;
    auto att = tee.generate();
    ZkMovementValidator zk(10.f);
    auto proof = zk.prove("smoke_player", {0,0,0}, {0.1f,0,0}, 50);

    Bytes payload;
    payload.insert(payload.end(), att.quote_hash.begin(), att.quote_hash.end());
    payload.insert(payload.end(), proof.public_inputs_hash.begin(), proof.public_inputs_hash.end());
    payload.insert(payload.end(), proof.proof_id.begin(), proof.proof_id.end());

    auto rec = sub.submit_dual(payload);
    std::cout << "combined_hash=" << rec.combined_hash << "\n";
    std::cout << "hcs_msg=" << rec.hcs.message_id << "\n";
    std::cout << "xrpl_tx=" << rec.xrpl.tx_hash << "\n";
    std::cout << "OK\n";
    return 0;
}
