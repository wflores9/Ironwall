#include "ironwall/chain_submit.hpp"
#include "util.hpp"
#include <cstdio>
#include <array>
#include <memory>
#include <iostream>
#include <sstream>
#include <fstream>

namespace ironwall {

static std::string bytes_to_hex(const Bytes& b) {
    return util::to_hex(b);
}

std::string hedera_explorer_tx(const std::string& network, const std::string& tx_id) {
    if (network == "mainnet")
        return "https://hashscan.io/mainnet/transaction/" + tx_id;
    return "https://hashscan.io/testnet/transaction/" + tx_id;
}

std::string xrpl_explorer_tx(const std::string& network, const std::string& hash) {
    if (network == "mainnet")
        return "https://livenet.xrpl.org/transactions/" + hash;
    return "https://testnet.xrpl.org/transactions/" + hash;
}

ChainSubmitter::ChainSubmitter(ChainConfig cfg) : cfg_(std::move(cfg)) {
    live_ = !cfg_.hedera_operator_id.empty() || !cfg_.xrpl_seed.empty();
    if (!live_) {
        std::cerr << "[chain] no keys configured — running in SIMULATION mode\n";
    } else {
        std::cerr << "[chain] LIVE mode enabled\n";
    }
}

std::optional<std::string> ChainSubmitter::http_post_json(const std::string& url, const std::string& body) {
    // Prefer curl CLI so we don't drag libcurl as a hard dep yet
    std::string cmd = "curl -sS -X POST -H 'Content-Type: application/json' --max-time 15 "
                      "-d '" + body + "' '" + url + "' 2>/dev/null";
    std::array<char, 4096> buf{};
    std::string result;
    FILE* pipe = popen(cmd.c_str(), "r");
    if (!pipe) return std::nullopt;
    while (fgets(buf.data(), buf.size(), pipe)) result += buf.data();
    int rc = pclose(pipe);
    if (rc != 0 || result.empty()) return std::nullopt;
    return result;
}

LiveSubmitResult ChainSubmitter::submit_hcs(const Bytes& payload) {
    LiveSubmitResult r;
    r.provider = "hcs";

    if (cfg_.hedera_operator_id.empty()) {
        // Simulate
        util::Sha256 h;
        h.update("hcs-sim");
        h.update(payload);
        r.ok = true;
        r.tx_id = "0.0.sim@" + h.hexdigest().substr(0, 16);
        r.explorer_url = hedera_explorer_tx(cfg_.hedera_network, r.tx_id);
        std::cerr << "[hcs] SIM submit topic=" << cfg_.hcs_topic_id
                  << " payload=" << payload.size() << "B tx=" << r.tx_id << "\n";
        return r;
    }

    // Live path placeholder: real impl uses hedera-sdk-cpp or REST + sign
    // For now POST a mirror-node friendly stub and report
    std::ostringstream body;
    body << "{\"topicId\":\"" << cfg_.hcs_topic_id
         << "\",\"message\":\"" << bytes_to_hex(payload)
         << "\",\"operator\":\"" << cfg_.hedera_operator_id << "\"}";

    auto resp = http_post_json(cfg_.hedera_mirror + "/api/v1/topics/" + cfg_.hcs_topic_id + "/messages", body.str());
    if (!resp) {
        r.error = "hcs http failed (is mirror reachable? keys configured?)";
        // fall back to sim id so pipeline doesn't break
        util::Sha256 h;
        h.update(payload);
        r.tx_id = "0.0.pending@" + h.hexdigest().substr(0, 12);
        r.ok = false;
        r.explorer_url = hedera_explorer_tx(cfg_.hedera_network, r.tx_id);
        return r;
    }
    r.ok = true;
    r.tx_id = resp->substr(0, 64);
    r.explorer_url = hedera_explorer_tx(cfg_.hedera_network, r.tx_id);
    return r;
}

LiveSubmitResult ChainSubmitter::submit_xrpl(const Bytes& payload) {
    LiveSubmitResult r;
    r.provider = "xrpl";

    if (cfg_.xrpl_seed.empty()) {
        util::Sha256 h;
        h.update("xrpl-sim");
        h.update(payload);
        r.ok = true;
        r.tx_id = h.hexdigest();
        r.explorer_url = xrpl_explorer_tx(cfg_.xrpl_network, r.tx_id);
        std::cerr << "[xrpl] SIM submit account=" << cfg_.xrpl_account
                  << " payload=" << payload.size() << "B hash=" << r.tx_id.substr(0, 16) << "...\n";
        return r;
    }

    // Live XRPL JSON-RPC submit placeholder (Payment with Memo)
    std::string memo_hex = bytes_to_hex(payload);
    if (memo_hex.size() > 1024) memo_hex.resize(1024);
    std::ostringstream body;
    body << "{\"method\":\"submit\",\"params\":[{\"tx_json\":{"
         << "\"TransactionType\":\"Payment\","
         << "\"Account\":\"" << cfg_.xrpl_account << "\","
         << "\"Destination\":\"" << cfg_.xrpl_account << "\","
         << "\"Amount\":\"1\","
         << "\"Memos\":[{\"Memo\":{\"MemoData\":\"" << memo_hex << "\"}}]"
         << "},\"secret\":\"" << cfg_.xrpl_seed << "\"}]}";

    auto resp = http_post_json(cfg_.xrpl_rpc, body.str());
    if (!resp) {
        r.error = "xrpl rpc failed";
        util::Sha256 h;
        h.update(payload);
        r.tx_id = h.hexdigest();
        r.ok = false;
        r.explorer_url = xrpl_explorer_tx(cfg_.xrpl_network, r.tx_id);
        return r;
    }
    r.ok = true;
    // crude extract — real code parses JSON engine_result + tx hash
    r.tx_id = resp->substr(0, 64);
    r.explorer_url = xrpl_explorer_tx(cfg_.xrpl_network, r.tx_id);
    return r;
}

DualAnchorReceipt ChainSubmitter::submit_dual(const Bytes& payload) {
    auto hcs = submit_hcs(payload);
    auto xrpl = submit_xrpl(payload);

    DualAnchorReceipt rec;
    rec.hcs.topic_id = cfg_.hcs_topic_id;
    rec.hcs.message_id = hcs.tx_id;
    rec.hcs.payload_hash = util::to_hex(payload).substr(0, 64);
    rec.hcs.consensus_timestamp = util::now();

    rec.xrpl.account = cfg_.xrpl_account;
    rec.xrpl.tx_hash = xrpl.tx_id;
    rec.xrpl.timestamp = util::now();

    util::Sha256 h;
    h.update(rec.hcs.payload_hash);
    h.update(rec.xrpl.tx_hash);
    rec.combined_hash = h.hexdigest();

    std::cerr << "[chain] dual combined_hash=" << rec.combined_hash
              << " hcs_ok=" << hcs.ok << " xrpl_ok=" << xrpl.ok << "\n";
    if (!hcs.explorer_url.empty())
        std::cerr << "  hcs:  " << hcs.explorer_url << "\n";
    if (!xrpl.explorer_url.empty())
        std::cerr << "  xrpl: " << xrpl.explorer_url << "\n";
    return rec;
}

} // namespace ironwall
