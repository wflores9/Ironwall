#include "ironwall/ironwall.hpp"
#include "ironwall/config_file.hpp"
#include "ironwall/recorder.hpp"
#include <iostream>
#include <string>
#include <cstring>

int main(int argc, char** argv) {
    using namespace ironwall;

    std::string config_path = "ironwall.conf";
    for (int i = 1; i < argc; ++i) {
        if ((std::strcmp(argv[i], "--config") == 0 || std::strcmp(argv[i], "-c") == 0) && i + 1 < argc) {
            config_path = argv[++i];
        } else if (std::strcmp(argv[i], "--help") == 0 || std::strcmp(argv[i], "-h") == 0) {
            std::cout << "Usage: ironwall_thin_client [--config path] [--help]\n";
            return 0;
        }
    }

    ironwall::print_banner();
    std::cout << "Ironwall C++ Thin Client starting...\n";
    Config cfg = load_config(config_path);
    std::cout << "Config: player=" << cfg.player_id
              << " ticks=" << cfg.demo_ticks
              << " tick=" << cfg.tick_rate_hz << "Hz"
              << " max_speed=" << cfg.max_speed << "\n";

    ProofStore store;
    MatchRecorder recorder("ironwall_match.tsv");
    NetLoopback net;

    TeeAttestation tee;
    auto att = tee.generate();
    std::cout << "TEE attestation generated: " << att.quote_hash << "\n";

    auto session = Session::create(cfg, att);
    std::cout << "Session created: " << session.session_id << "\n";
    recorder.record_attest(session.session_id, cfg.player_id, att);

    net.client_send(HelloMsg{cfg.player_id, "0.1.0", att});
    net.run_server_once();
    if (auto msg = net.client_recv()) {
        if (auto* w = std::get_if<WelcomeMsg>(&*msg)) {
            std::cout << "Received Welcome, session_id=" << w->session_id << "\n";
        }
    }

    ZkMovementValidator zk(cfg.max_speed);
    DualAnchor dual(HcsAnchor(cfg.hcs_topic_id), XrplAnchor(cfg.xrpl_account));

    ThinClient client(cfg, att, zk, dual);
    client.run();

    auto last = client.zk().prove(cfg.player_id, {0.48f,0,0.32f}, {0.60f,0,0.40f}, 16);
    auto anchor = client.anchors().anchor(att, last);
    store.insert(last, anchor, att);
    recorder.record_proof(session.session_id, last, anchor);

    net.client_send(MovementProofMsg{last, anchor});
    net.run_server_once();
    if (auto msg = net.client_recv()) {
        if (auto* a = std::get_if<AckMsg>(&*msg)) {
            std::cout << "Ack for proof " << a->proof_id << ": accepted=" << a->accepted << "\n";
            session.record_proof();
        }
    }

    ChallengeEngine engine;
    auto ch = engine.issue(last.proof_id, "suspicious velocity spike");
    session.record_challenge();
    recorder.record_challenge(session.session_id, ch.challenge_id);

    auto fresh_att = tee.generate();
    auto fresh_proof = client.zk().prove(cfg.player_id, {0,0,0}, {0.05f,0,0}, 50);
    auto resp = engine.respond(ch, fresh_att, fresh_proof);
    net.client_send(ChallengeResponseMsg{resp});
    net.run_server_once();
    if (auto msg = net.client_recv()) {
        if (auto* a = std::get_if<AckMsg>(&*msg)) {
            std::cout << "Challenge Ack: accepted=" << a->accepted
                      << " reason=" << (a->reason ? *a->reason : "") << "\n";
        }
    }

    auto hb = session.heartbeat({0.60f, 0, 0.40f});
    recorder.record_heartbeat(session.session_id, {0.60f,0,0.40f});
    net.client_send(hb);
    net.run_server_once();

    std::cout << "Session final: proofs=" << session.proofs_submitted
              << " challenges=" << session.challenges_received
              << " store_len=" << store.size() << "\n";
    std::cout << "Recorder events=" << recorder.count() << " file=" << recorder.path() << "\n";
    std::cout << "Ironwall C++ Thin Client shut down cleanly\n";
    return 0;
}
