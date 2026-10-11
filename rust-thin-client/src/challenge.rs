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
        if challenge.deadline <= challenge.issued_at || Utc::now() < challenge.issued_at || Utc::now() > challenge.deadline {
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

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn expired_challenge_rejected_before_response_is_created() {
        let engine = ChallengeEngine::new();
        let mut challenge = engine.issue_challenge("proof-1", "review");
        challenge.deadline = Utc::now() - chrono::Duration::seconds(1);
        let attestation = crate::tee::TeeAttestation::new().generate_attestation().await.unwrap();
        let proof = crate::zk::ZkMovementValidator::new(100.0)
            .prove_valid_movement("player-1", (0.0, 0.0, 0.0), (0.1, 0.0, 0.0), 100)
            .await.unwrap();
        assert!(engine.respond(&challenge, attestation, proof).await.is_err());
    }

    #[tokio::test]
    async fn future_dated_challenge_is_rejected() {
        let engine = ChallengeEngine::new();
        let mut challenge = engine.issue_challenge("proof-1", "review");
        challenge.issued_at = Utc::now() + chrono::Duration::minutes(5);
        challenge.deadline = challenge.issued_at + chrono::Duration::seconds(30);
        let attestation = crate::tee::TeeAttestation::new().generate_attestation().await.unwrap();
        let proof = crate::zk::ZkMovementValidator::new(100.0)
            .prove_valid_movement("player-1", (0.0, 0.0, 0.0), (0.1, 0.0, 0.0), 100)
            .await.unwrap();
        assert!(engine.respond(&challenge, attestation, proof).await.is_err());
    }

    #[tokio::test]
    async fn malformed_challenge_window_rejected() {
        let engine = ChallengeEngine::new();
        let mut challenge = engine.issue_challenge("proof-1", "review");
        challenge.deadline = challenge.issued_at;
        let attestation = crate::tee::TeeAttestation::new().generate_attestation().await.unwrap();
        let proof = crate::zk::ZkMovementValidator::new(100.0)
            .prove_valid_movement("player-1", (0.0, 0.0, 0.0), (0.1, 0.0, 0.0), 100)
            .await.unwrap();
        assert!(engine.respond(&challenge, attestation, proof).await.is_err());
    }
}
