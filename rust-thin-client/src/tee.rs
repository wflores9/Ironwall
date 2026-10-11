use anyhow::Result;
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use uuid::Uuid;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TeeAttestationResult {
    pub quote_id: String,
    pub quote_hash: String,
    pub report_data: Vec<u8>,
    pub timestamp: DateTime<Utc>,
    pub mr_enclave: String,
    pub mr_signer: String,
    /// Explicitly distinguishes synthetic demo data from hardware-backed evidence.
    pub simulated: bool,
}

pub struct TeeAttestation;

impl TeeAttestation {
    pub fn new() -> Self {
        Self
    }

    pub async fn generate_attestation(&self) -> Result<TeeAttestationResult> {
        let quote_id = Uuid::new_v4().to_string();
        let report_data = b"ironwall-tee-report-data-v1".to_vec();

        let mut hasher = Sha256::new();
        hasher.update(&quote_id);
        hasher.update(&report_data);
        hasher.update(Utc::now().timestamp().to_le_bytes());
        let quote_hash = hex::encode(hasher.finalize());

        Ok(TeeAttestationResult {
            quote_id,
            quote_hash,
            report_data,
            timestamp: Utc::now(),
            mr_enclave: "0".repeat(64),
            mr_signer: "0".repeat(64),
            simulated: true,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn synthetic_attestation_is_never_hardware_qualified() {
        let result = TeeAttestation::new().generate_attestation().await.unwrap();
        assert!(result.simulated);
        assert_eq!(result.mr_enclave, "0".repeat(64));
        assert_eq!(result.mr_signer, "0".repeat(64));
        let serialized = serde_json::to_value(&result).unwrap();
        assert_eq!(serialized["simulated"], true);
    }
}
