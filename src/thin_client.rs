use anyhow::Result;
use tracing::info;
use tokio::time::{sleep, Duration};

use crate::tee::TeeAttestationResult;
use crate::zk::ZkMovementValidator;
use crate::anchors::DualAnchor;
use crate::config::IronwallConfig;

pub struct ThinClient {
    pub cfg: IronwallConfig,
    pub attestation: TeeAttestationResult,
    pub zk: ZkMovementValidator,
    pub anchors: DualAnchor,
    position: (f32, f32, f32),
}

impl ThinClient {
    pub fn new(
        cfg: IronwallConfig,
        attestation: TeeAttestationResult,
        zk: ZkMovementValidator,
        anchors: DualAnchor,
    ) -> Self {
        Self {
            cfg,
            attestation,
            zk,
            anchors,
            position: (0.0, 0.0, 0.0),
        }
    }

    pub async fn run(&mut self) -> Result<()> {
        info!("Thin client main loop started");
        info!("Attestation quote: {}", self.attestation.quote_hash);

        let tick_ms = 1000 / self.cfg.tick_rate_hz.max(1);
        let mut tick: u64 = 0;

        while tick < 5 {
            let from = self.position;

            let to = (
                from.0 + 0.12,
                from.1,
                from.2 + 0.08,
            );

            let proof = self.zk.prove_valid_movement(
                &self.cfg.player_id,
                from,
                to,
                tick_ms,
            ).await?;

            info!(
                "tick={} pos=({:.2},{:.2},{:.2}) speed={:.2} proof={}",
                tick, to.0, to.1, to.2, proof.speed, proof.proof_id
            );

            let receipt = self.anchors.anchor_proof(&self.attestation, &proof).await?;
            info!("anchored combined_hash={}", receipt.combined_hash);

            self.position = to;
            tick += 1;

            sleep(Duration::from_millis(tick_ms as u64)).await;
        }

        info!("Demo loop finished");
        Ok(())
    }
}
