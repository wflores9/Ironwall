use anyhow::Result;
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use uuid::Uuid;

use crate::tee::TeeAttestationResult;
use crate::zk::ZkMovementProof;

#[derive(Debug, Clone)]
pub struct HcsAnchor {
    pub topic_id: String,
}

impl HcsAnchor {
    pub fn new(topic_id: impl Into<String>) -> Self {
        Self {
            topic_id: topic_id.into(),
        }
    }

    pub async fn submit(&self, payload: &[u8]) -> Result<HcsReceipt> {
        let message_id = Uuid::new_v4().to_string();
        let mut hasher = Sha256::new();
        hasher.update(payload);
        let payload_hash = hex::encode(hasher.finalize());

        Ok(HcsReceipt {
            topic_id: self.topic_id.clone(),
            message_id,
            sequence_number: 0,
            payload_hash,
            consensus_timestamp: Utc::now(),
        })
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HcsReceipt {
    pub topic_id: String,
    pub message_id: String,
    pub sequence_number: u64,
    pub payload_hash: String,
    pub consensus_timestamp: DateTime<Utc>,
}

#[derive(Debug, Clone)]
pub struct XrplAnchor {
    pub account: String,
}

impl XrplAnchor {
    pub fn new(account: impl Into<String>) -> Self {
        Self {
            account: account.into(),
        }
    }

    pub async fn submit(&self, payload: &[u8]) -> Result<XrplReceipt> {
        let tx_hash = {
            let mut h = Sha256::new();
            h.update(b"xrpl-ironwall-anchor");
            h.update(payload);
            hex::encode(h.finalize())
        };

        Ok(XrplReceipt {
            account: self.account.clone(),
            tx_hash,
            ledger_index: 0,
            timestamp: Utc::now(),
        })
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct XrplReceipt {
    pub account: String,
    pub tx_hash: String,
    pub ledger_index: u32,
    pub timestamp: DateTime<Utc>,
}

#[derive(Debug, Clone)]
pub struct DualAnchor {
    pub hcs: HcsAnchor,
    pub xrpl: XrplAnchor,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DualAnchorReceipt {
    pub hcs: HcsReceipt,
    pub xrpl: XrplReceipt,
    pub combined_hash: String,
}

impl DualAnchor {
    pub fn new(hcs: HcsAnchor, xrpl: XrplAnchor) -> Self {
        Self { hcs, xrpl }
    }

    pub async fn anchor_proof(
        &self,
        attestation: &TeeAttestationResult,
        proof: &ZkMovementProof,
    ) -> Result<DualAnchorReceipt> {
        let mut payload = Vec::new();
        payload.extend_from_slice(attestation.quote_hash.as_bytes());
        payload.extend_from_slice(proof.public_inputs_hash.as_bytes());
        payload.extend_from_slice(proof.proof_id.as_bytes());

        let hcs_receipt = self.hcs.submit(&payload).await?;
        let xrpl_receipt = self.xrpl.submit(&payload).await?;

        let mut hasher = Sha256::new();
        hasher.update(hcs_receipt.payload_hash.as_bytes());
        hasher.update(xrpl_receipt.tx_hash.as_bytes());
        let combined_hash = hex::encode(hasher.finalize());

        Ok(DualAnchorReceipt {
            hcs: hcs_receipt,
            xrpl: xrpl_receipt,
            combined_hash,
        })
    }
}
