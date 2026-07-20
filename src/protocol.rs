//! Wire protocol messages for Ironwall thin client <-> verifier / game server.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

use crate::tee::TeeAttestationResult;
use crate::zk::ZkMovementProof;
use crate::anchors::DualAnchorReceipt;
use crate::challenge::{Challenge, ChallengeResponse};

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", content = "payload")]
pub enum ClientMessage {
    Hello {
        player_id: String,
        client_version: String,
        attestation: TeeAttestationResult,
    },
    MovementProof {
        proof: ZkMovementProof,
        anchor: DualAnchorReceipt,
    },
    ChallengeResponse {
        response: ChallengeResponse,
    },
    Heartbeat {
        ts: DateTime<Utc>,
        position: (f32, f32, f32),
    },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", content = "payload")]
pub enum ServerMessage {
    Welcome {
        session_id: String,
        server_time: DateTime<Utc>,
    },
    Challenge {
        challenge: Challenge,
    },
    Ack {
        proof_id: String,
        accepted: bool,
        reason: Option<String>,
    },
    Kick {
        reason: String,
    },
}

impl ClientMessage {
    #[allow(dead_code)]
    pub fn to_json(&self) -> Result<String, serde_json::Error> {
        serde_json::to_string(self)
    }

    #[allow(dead_code)]
    pub fn from_json(s: &str) -> Result<Self, serde_json::Error> {
        serde_json::from_str(s)
    }
}

impl ServerMessage {
    #[allow(dead_code)]
    pub fn to_json(&self) -> Result<String, serde_json::Error> {
        serde_json::to_string(self)
    }

    #[allow(dead_code)]
    pub fn from_json(s: &str) -> Result<Self, serde_json::Error> {
        serde_json::from_str(s)
    }
}
