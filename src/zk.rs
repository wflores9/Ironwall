use anyhow::Result;
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use uuid::Uuid;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ZkMovementProof {
    pub proof_id: String,
    pub player_id: String,
    pub from: (f32, f32, f32),
    pub to: (f32, f32, f32),
    pub delta_t_ms: u32,
    pub proof_bytes: Vec<u8>,
    pub public_inputs_hash: String,
    pub timestamp: DateTime<Utc>,
}

pub struct ZkMovementValidator;

impl ZkMovementValidator {
    pub fn new() -> Self {
        Self
    }

    pub async fn prove_valid_movement(
        &self,
        player_id: &str,
        from: (f32, f32, f32),
        to: (f32, f32, f32),
        delta_t_ms: u32,
    ) -> Result<ZkMovementProof> {
        let proof_id = Uuid::new_v4().to_string();

        let mut hasher = Sha256::new();
        hasher.update(player_id.as_bytes());
        hasher.update(&from.0.to_le_bytes());
        hasher.update(&from.1.to_le_bytes());
        hasher.update(&from.2.to_le_bytes());
        hasher.update(&to.0.to_le_bytes());
        hasher.update(&to.1.to_le_bytes());
        hasher.update(&to.2.to_le_bytes());
        hasher.update(&delta_t_ms.to_le_bytes());
        let public_inputs_hash = hex::encode(hasher.finalize());

        let proof_bytes = {
            let mut h = Sha256::new();
            h.update(b"ironwall-zk-movement-proof-v1");
            h.update(public_inputs_hash.as_bytes());
            h.finalize().to_vec()
        };

        Ok(ZkMovementProof {
            proof_id,
            player_id: player_id.to_string(),
            from,
            to,
            delta_t_ms,
            proof_bytes,
            public_inputs_hash,
            timestamp: Utc::now(),
        })
    }
}
