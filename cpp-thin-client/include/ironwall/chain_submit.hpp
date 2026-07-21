#pragma once
#include "anchors.hpp"
#include "types.hpp"
#include <string>
#include <optional>
#include <functional>

namespace ironwall {

struct ChainConfig {
    // Hedera
    std::string hedera_network = "testnet";           // testnet | mainnet
    std::string hedera_operator_id;                   // 0.0.xxxxx
    std::string hedera_operator_key_pem;              // path or PEM contents
    std::string hcs_topic_id = "0.0.123456";
    std::string hedera_mirror = "https://testnet.mirrornode.hedera.com";

    // XRPL
    std::string xrpl_network = "testnet";             // testnet | mainnet
    std::string xrpl_rpc = "https://s.altnet.rippletest.net:51234";
    std::string xrpl_seed;                            // sXXX... (keep secret)
    std::string xrpl_account;
};

// Result of a live (or simulated) submission
struct LiveSubmitResult {
    bool ok = false;
    std::string provider;          // "hcs" | "xrpl"
    std::string tx_id;             // hedera tx id or xrpl hash
    std::string explorer_url;
    std::string error;
};

class ChainSubmitter {
public:
    explicit ChainSubmitter(ChainConfig cfg);

    // Submit opaque payload bytes to both chains (or simulate if no keys)
    DualAnchorReceipt submit_dual(const Bytes& payload);

    // Individual
    LiveSubmitResult submit_hcs(const Bytes& payload);
    LiveSubmitResult submit_xrpl(const Bytes& payload);

    bool live_mode() const { return live_; }

private:
    ChainConfig cfg_;
    bool live_ = false;  // true when keys present

    // HTTP POST helper (uses curl if available, else simulates)
    std::optional<std::string> http_post_json(const std::string& url, const std::string& body);
};

// Build explorer links
std::string hedera_explorer_tx(const std::string& network, const std::string& tx_id);
std::string xrpl_explorer_tx(const std::string& network, const std::string& hash);

} // namespace ironwall
