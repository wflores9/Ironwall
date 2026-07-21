//! Challenge-response dispute protocol stub.
//! Future: verifier can challenge a proof; client must re-attest + re-prove.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

use crate::error::{IronwallError, IronwallResult};
use crate::tee::TeeAttestationResult;
use crate::zk::ZkMovementProof;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Challenge {
    pub challenge_id: String,
    pub proof_id: String,
    pub reason: String,
    pub issued_at: DateTime<Utc>,
    pub deadline: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChallengeResponse {
    pub challenge_id: String,
    pub new_attestation: TeeAttestationResult,
    pub new_proof: ZkMovementProof,
    pub responded_at: DateTime<Utc>,
}

pub struct ChallengeEngine;

impl ChallengeEngine {
    pub fn new() -> Self {
        Self
    }

    pub fn issue_challenge(&self, proof_id: &str, reason: &str) -> Challenge {
        let now = Utc::now();
        Challenge {
            challenge_id: Uuid::new_v4().to_string(),
            proof_id: proof_id.to_string(),
            reason: reason.to_string(),
            issued_at: now,
            deadline: now + chrono::Duration::seconds(30),
        }
    }

    pub async fn respond(
        &self,
        challenge: &Challenge,
        attestation: TeeAttestationResult,
        proof: ZkMovementProof,
    ) -> IronwallResult<ChallengeResponse> {
        if Utc::now() > challenge.deadline {
            return Err(IronwallError::Anchor("challenge deadline exceeded".into()));
        }

        Ok(ChallengeResponse {
            challenge_id: challenge.challenge_id.clone(),
            new_attestation: attestation,
            new_proof: proof,
            responded_at: Utc::now(),
        })
    }
}

impl Default for ChallengeEngine {
    fn default() -> Self {
        Self::new()
    }
}
