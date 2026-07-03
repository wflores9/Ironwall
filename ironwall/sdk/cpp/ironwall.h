#pragma once
#include <string>
#include <functional>

namespace ironwall {

// Result returned from all SDK calls
struct Result {
    bool success;
    std::string error;
    std::string data; // JSON payload
};

// Session token returned after successful attestation
struct SessionToken {
    std::string token;
    std::string player_id;
    long long expires_at; // unix timestamp
};

// Match record submitted at game end
struct MatchRecord {
    std::string match_id;
    std::string merkle_root;
    std::string receipt_hash;
    long long end_time;
};

class IronwallClient {
public:
    // Initialize with broker endpoint and studio API key
    IronwallClient(const std::string& broker_url, const std::string& api_key);

    // Call at game launch — verifies binary integrity + TEE attestation
    // Returns session token if clean, error if tampered
    Result attest(const std::string& player_id, SessionToken& out_token);

    // Call every 60s during match — re-verifies session is still clean
    // Returns false = terminate session immediately
    bool validate(const SessionToken& token);

    // Call at match end — submits record for dual-chain anchoring
    // Returns XRPL tx hash + Hedera consensus timestamp
    Result commit_match(const MatchRecord& record, const SessionToken& token);

    // Verify a match record independently (no trust in Ironwall servers)
    // Can be called by anyone with the match_id
    static Result verify(const std::string& match_id, const std::string& network = "testnet");

private:
    std::string broker_url_;
    std::string api_key_;
};

} // namespace ironwall
