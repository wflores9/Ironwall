mod thin_client;
mod tee;
mod zk;
mod anchors;
mod config;
mod error;
mod challenge;

use anyhow::Result;
use tracing::{info, Level};
use tracing_subscriber::FmtSubscriber;

use crate::thin_client::ThinClient;
use crate::tee::TeeAttestation;
use crate::zk::ZkMovementValidator;
use crate::anchors::{HcsAnchor, XrplAnchor, DualAnchor};
use crate::config::IronwallConfig;
use crate::challenge::ChallengeEngine;

#[tokio::main]
async fn main() -> Result<()> {
    let subscriber = FmtSubscriber::builder()
        .with_max_level(Level::INFO)
        .finish();
    tracing::subscriber::set_global_default(subscriber)?;

    info!("Ironwall Thin Client starting...");

    let cfg = IronwallConfig::default();
    info!(
        "Config loaded: player={}, tick={}Hz, max_speed={}",
        cfg.player_id, cfg.tick_rate_hz, cfg.max_speed_units_per_sec
    );

    let tee = TeeAttestation::new();
    let attestation = tee.generate_attestation().await?;
    info!("TEE attestation generated: {}", attestation.quote_hash);

    let zk = ZkMovementValidator::new(cfg.max_speed_units_per_sec);
    let hcs = HcsAnchor::new(&cfg.hcs_topic_id);
    let xrpl = XrplAnchor::new(&cfg.xrpl_account);
    let dual = DualAnchor::new(hcs, xrpl);

    let mut client = ThinClient::new(cfg, attestation.clone(), zk, dual);
    client.run().await?;

    // Demo challenge-response
    let engine = ChallengeEngine::new();
    let ch = engine.issue_challenge("demo-proof-id", "suspicious velocity spike");
    info!("Challenge issued: {} reason={}", ch.challenge_id, ch.reason);

    let fresh_attestation = tee.generate_attestation().await?;
    let fresh_proof = client.zk.prove_valid_movement(
        &client.cfg.player_id,
        (0.0, 0.0, 0.0),
        (0.05, 0.0, 0.0),
        50,
    ).await?;

    let response = engine.respond(&ch, fresh_attestation, fresh_proof).await?;
    info!(
        "Challenge response submitted: challenge={} responded_at={}",
        response.challenge_id, response.responded_at
    );

    Ok(())
}
