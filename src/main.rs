mod thin_client;
mod tee;
mod zk;
mod anchors;
mod config;

use anyhow::Result;
use tracing::{info, Level};
use tracing_subscriber::FmtSubscriber;

use crate::thin_client::ThinClient;
use crate::tee::TeeAttestation;
use crate::zk::ZkMovementValidator;
use crate::anchors::{HcsAnchor, XrplAnchor, DualAnchor};
use crate::config::IronwallConfig;

#[tokio::main]
async fn main() -> Result<()> {
    let subscriber = FmtSubscriber::builder()
        .with_max_level(Level::INFO)
        .finish();
    tracing::subscriber::set_global_default(subscriber)?;

    info!("Ironwall Thin Client starting...");

    let cfg = IronwallConfig::default();
    info!("Config loaded: player={}, tick={}Hz", cfg.player_id, cfg.tick_rate_hz);

    let tee = TeeAttestation::new();
    let attestation = tee.generate_attestation().await?;
    info!("TEE attestation generated: {}", attestation.quote_hash);

    let zk = ZkMovementValidator::new(cfg.max_speed_units_per_sec);
    let hcs = HcsAnchor::new(&cfg.hcs_topic_id);
    let xrpl = XrplAnchor::new(&cfg.xrpl_account);
    let dual = DualAnchor::new(hcs, xrpl);

    let mut client = ThinClient::new(cfg, attestation, zk, dual);
    client.run().await?;

    Ok(())
}
