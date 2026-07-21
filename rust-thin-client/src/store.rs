//! Local proof / attestation store (in-memory for now, file/DB later).

use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;
use tracing::info;

use crate::zk::ZkMovementProof;
use crate::tee::TeeAttestationResult;
use crate::anchors::DualAnchorReceipt;

#[derive(Debug, Clone)]
#[allow(dead_code)]
pub struct StoredProof {
    pub proof: ZkMovementProof,
    pub anchor: DualAnchorReceipt,
    pub attestation_quote: String,
}

#[derive(Debug, Default)]
pub struct ProofStore {
    inner: Arc<RwLock<HashMap<String, StoredProof>>>,
}

impl ProofStore {
    pub fn new() -> Self {
        Self {
            inner: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    pub async fn insert(
        &self,
        proof: ZkMovementProof,
        anchor: DualAnchorReceipt,
        attestation: &TeeAttestationResult,
    ) {
        let id = proof.proof_id.clone();
        let entry = StoredProof {
            proof,
            anchor,
            attestation_quote: attestation.quote_hash.clone(),
        };
        self.inner.write().await.insert(id.clone(), entry);
        info!("ProofStore: stored proof {}", id);
    }

    #[allow(dead_code)]
    pub async fn get(&self, proof_id: &str) -> Option<StoredProof> {
        self.inner.read().await.get(proof_id).cloned()
    }

    pub async fn len(&self) -> usize {
        self.inner.read().await.len()
    }

    #[allow(dead_code)]
    pub async fn list_ids(&self) -> Vec<String> {
        self.inner.read().await.keys().cloned().collect()
    }
}
