use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use uuid::Uuid;

use crate::error::{IronwallError, IronwallResult};

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
    pub speed: f32,
}

pub struct ZkMovementValidator {
    max_speed: f32,
}

impl ZkMovementValidator {
    pub fn new(max_speed: f32) -> Self {
        Self { max_speed }
    }

    pub async fn prove_valid_movement(
        &self,
        player_id: &str,
        from: (f32, f32, f32),
        to: (f32, f32, f32),
        delta_t_ms: u32,
    ) -> IronwallResult<ZkMovementProof> {
        if delta_t_ms == 0 {
            return Err(IronwallError::InvalidMovement(
                "delta_t_ms cannot be zero".into(),
            ));
        }

        let dx = to.0 - from.0;
        let dy = to.1 - from.1;
        let dz = to.2 - from.2;
        let dist = (dx * dx + dy * dy + dz * dz).sqrt();
        let dt_sec = delta_t_ms as f32 / 1000.0;
        let speed = dist / dt_sec;

        if speed > self.max_speed {
            return Err(IronwallError::InvalidMovement(format!(
                "movement speed {:.2} exceeds max {:.2} (possible speedhack)",
                speed, self.max_speed
            )));
        }

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
        hasher.update(&speed.to_le_bytes());
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
            speed,
        })
    }
}
