mod thin_client;
mod tee;
mod zk;
mod anchors;

use anyhow::Result;
use tracing::{info, Level};
use tracing_subscriber::FmtSubscriber;

use crate::thin_client::ThinClient;
use crate::tee::TeeAttestation;
use crate::zk::ZkMovementValidator;
use crate::anchors::{HcsAnchor, XrplAnchor, DualAnchor};

#[tokio::main]
async fn main() -> Result<()> {
    let subscriber = FmtSubscriber::builder()
        .with_max_level(Level::INFO)
        .finish();
    tracing::subscriber::set_global_default(subscriber)?;

    info!("Ironwall Thin Client starting...");

    let tee = TeeAttestation::new();
    let attestation = tee.generate_attestation().await?;
    info!("TEE attestation generated: {}", attestation.quote_hash);

    let zk = ZkMovementValidator::new();
    let movement_proof = zk.prove_valid_movement(
        "player_001",
        (0.0, 0.0, 0.0),
        (1.5, 0.0, 2.3),
        16,
    ).await?;
    info!("ZK movement proof generated: {}", movement_proof.proof_id);

    let hcs = HcsAnchor::new("0.0.123456");
    let xrpl = XrplAnchor::new("rIronwallAnchorXXXXXXXXXXXXXXXXXX");
    let dual = DualAnchor::new(hcs, xrpl);

    let anchor_receipt = dual.anchor_proof(&attestation, &movement_proof).await?;
    info!("Dual-anchored to HCS + XRPL: {:?}", anchor_receipt);

    let mut client = ThinClient::new(attestation, zk, dual);
    client.run().await?;

    Ok(())
}
