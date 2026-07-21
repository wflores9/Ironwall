use thiserror::Error;

#[derive(Error, Debug)]
#[allow(dead_code)]
pub enum IronwallError {
    #[error("TEE attestation failed: {0}")]
    TeeAttestation(String),

    #[error("ZK proof generation failed: {0}")]
    ZkProof(String),

    #[error("Invalid movement: {0}")]
    InvalidMovement(String),

    #[error("Anchor submission failed: {0}")]
    Anchor(String),

    #[error("Config error: {0}")]
    Config(String),
}

pub type IronwallResult<T> = std::result::Result<T, IronwallError>;
