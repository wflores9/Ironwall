use ironwall::{print_banner, CircuitKeys, prove_movement, verify_movement};
mod thin_client;
mod tee;
mod zk;
mod anchors;
mod config;
mod error;
mod challenge;
mod protocol;
mod session;
mod net;
mod store;

use anyhow::Result;
use tracing::{info, Level};
use tracing_subscriber::FmtSubscriber;
use tokio::task;

use crate::thin_client::ThinClient;
use crate::tee::TeeAttestation;
use crate::zk::ZkMovementValidator;
use crate::anchors::{HcsAnchor, XrplAnchor, DualAnchor};
use crate::config::IronwallConfig;
use crate::challenge::ChallengeEngine;
use crate::protocol::{ClientMessage, ServerMessage};
use crate::session::Session;
use crate::net::create_loopback;
use crate::store::ProofStore;

#[tokio::main]
async fn main() -> Result<()> {
    let subscriber = FmtSubscriber::builder()
        .with_max_level(Level::INFO)
        .finish();
    tracing::subscriber::set_global_default(subscriber)?;

    print_banner();
    info!("Ironwall Thin Client starting...");

    let cfg = IronwallConfig::default();
    info!(
        "Config loaded: player={}, tick={}Hz, max_speed={}",
        cfg.player_id, cfg.tick_rate_hz, cfg.max_speed_units_per_sec
    );

    let store = ProofStore::new();

    let (mut net, server) = create_loopback();
    let server_handle = task::spawn(async move {
        server.run_demo().await;
    });

    let tee = TeeAttestation::new();
    let attestation = tee.generate_attestation().await?;
    info!("TEE attestation generated: {}", attestation.quote_hash);

    let mut session = Session::new(&cfg, attestation.clone());
    info!("Session created: {}", session.session_id);

    let hello = ClientMessage::Hello {
        player_id: cfg.player_id.clone(),
        client_version: env!("CARGO_PKG_VERSION").to_string(),
        attestation: attestation.clone(),
    };
    net.send(hello).await?;
    if let Some(ServerMessage::Welcome { session_id, .. }) = net.recv().await {
        info!("Received Welcome, session_id={}", session_id);
    }

    let zk = ZkMovementValidator::new(cfg.max_speed_units_per_sec);
    let hcs = HcsAnchor::new(&cfg.hcs_topic_id);
    let xrpl = XrplAnchor::new(&cfg.xrpl_account);
    let dual = DualAnchor::new(hcs, xrpl);

    let mut client = ThinClient::new(cfg.clone(), attestation.clone(), zk, dual);
    client.run().await?;

    let last_proof = client.zk.prove_valid_movement(
        &cfg.player_id,
        (0.48, 0.0, 0.32),
        (0.60, 0.0, 0.40),
        16,
    ).await?;
    let anchor = client.anchors.anchor_proof(&attestation, &last_proof).await?;
    store.insert(last_proof.clone(), anchor.clone(), &attestation).await;

    net.send(ClientMessage::MovementProof {
        proof: last_proof.clone(),
        anchor,
    }).await?;
    if let Some(ServerMessage::Ack { proof_id, accepted, .. }) = net.recv().await {
        info!("Ack for proof {}: accepted={}", proof_id, accepted);
        session.record_proof();
    }

    let engine = ChallengeEngine::new();
    let ch = engine.issue_challenge(&last_proof.proof_id, "suspicious velocity spike");
    session.record_challenge();

    let fresh_attestation = tee.generate_attestation().await?;
    let fresh_proof = client.zk.prove_valid_movement(
        &cfg.player_id,
        (0.0, 0.0, 0.0),
        (0.05, 0.0, 0.0),
        50,
    ).await?;
    let response = engine.respond(&ch, fresh_attestation, fresh_proof).await?;
    net.send(ClientMessage::ChallengeResponse { response }).await?;
    if let Some(ServerMessage::Ack { accepted, reason, .. }) = net.recv().await {
        info!("Challenge Ack: accepted={} reason={:?}", accepted, reason);
    }

    let hb = session.heartbeat((0.60, 0.0, 0.40));
    net.send(hb).await?;

    info!(
        "Session final: proofs={} challenges={} pos={:?} store_len={}",
        session.proofs_submitted,
        session.challenges_received,
        session.position,
        store.len().await
    );

    drop(net);
    let _ = server_handle.await;

    // Optional Groth16 proof on final segment
    info!("Groth16 setup (one-time)...");
    if let Ok(keys) = CircuitKeys::setup() {
        match prove_movement(&keys, (0.48, 0.0, 0.32), (0.60, 0.0, 0.40), 16, 10.0) {
            Ok(gp) => {
                let v = verify_movement(&keys, &gp).unwrap_or(false);
                info!("Groth16 movement proof verified={v} speed={:.2} bytes={}", gp.speed, gp.proof_hex.len()/2);
            }
            Err(e) => info!("Groth16 skipped: {e}"),
        }
    }
    info!("Ironwall Thin Client shut down cleanly");
    Ok(())
}
