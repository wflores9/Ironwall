//! Ironwall thin client library
//!
//! Open-source anti-cheat protocol stack:
//! - TEE attestation
//! - ZK-SNARK movement validation
//! - Hedera HCS + XRPL dual anchoring
//! - Challenge-response disputes

pub mod thin_client;
pub mod tee;
pub mod zk;
pub mod anchors;
pub mod config;
pub mod error;
pub mod challenge;

pub use thin_client::ThinClient;
pub use tee::{TeeAttestation, TeeAttestationResult};
pub use zk::{ZkMovementValidator, ZkMovementProof};
pub use anchors::{HcsAnchor, XrplAnchor, DualAnchor, DualAnchorReceipt};
pub use config::IronwallConfig;
pub use error::{IronwallError, IronwallResult};
pub use challenge::{Challenge, ChallengeResponse, ChallengeEngine};
