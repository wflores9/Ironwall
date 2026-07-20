//! Session management for an active Ironwall anti-cheat session.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

use crate::config::IronwallConfig;
use crate::tee::TeeAttestationResult;
use crate::protocol::{ClientMessage, ServerMessage};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Session {
    pub session_id: String,
    pub player_id: String,
    pub started_at: DateTime<Utc>,
    pub last_heartbeat: DateTime<Utc>,
    pub attestation: TeeAttestationResult,
    pub proofs_submitted: u64,
    pub challenges_received: u64,
    pub position: (f32, f32, f32),
}

impl Session {
    pub fn new(cfg: &IronwallConfig, attestation: TeeAttestationResult) -> Self {
        let now = Utc::now();
        Self {
            session_id: Uuid::new_v4().to_string(),
            player_id: cfg.player_id.clone(),
            started_at: now,
            last_heartbeat: now,
            attestation,
            proofs_submitted: 0,
            challenges_received: 0,
            position: (0.0, 0.0, 0.0),
        }
    }

    pub fn heartbeat(&mut self, pos: (f32, f32, f32)) -> ClientMessage {
        self.last_heartbeat = Utc::now();
        self.position = pos;
        ClientMessage::Heartbeat {
            ts: self.last_heartbeat,
            position: pos,
        }
    }

    pub fn record_proof(&mut self) {
        self.proofs_submitted += 1;
    }

    pub fn record_challenge(&mut self) {
        self.challenges_received += 1;
    }

    pub fn welcome_msg(&self) -> ServerMessage {
        ServerMessage::Welcome {
            session_id: self.session_id.clone(),
            server_time: Utc::now(),
        }
    }
}
