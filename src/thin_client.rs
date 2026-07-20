use anyhow::Result;
use tracing::info;
use crate::tee::TeeAttestationResult;
use crate::zk::ZkMovementValidator;
use crate::anchors::DualAnchor;

pub struct ThinClient {
    pub attestation: TeeAttestationResult,
    pub zk: ZkMovementValidator,
    pub anchors: DualAnchor,
}

impl ThinClient {
    pub fn new(
        attestation: TeeAttestationResult,
        zk: ZkMovementValidator,
        anchors: DualAnchor,
    ) -> Self {
        Self {
            attestation,
            zk,
            anchors,
        }
    }

    pub async fn run(&mut self) -> Result<()> {
        info!("Thin client main loop started (placeholder)");
        info!("Attestation quote: {}", self.attestation.quote_hash);

        // Touch zk + anchors so the compiler knows they are used
        let _ = &self.zk;
        let _ = &self.anchors;

        Ok(())
    }
}
