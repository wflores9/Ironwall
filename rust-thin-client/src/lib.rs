//! Ironwall thin client library
//!
//! Open-source anti-cheat protocol stack:
//! - TEE attestation
//! - ZK-SNARK movement validation
//! - Hedera HCS + XRPL dual anchoring
//! - Challenge-response disputes
//! - Wire protocol messages
//! - Session management
//! - Network transport stub
//! - Local proof store

pub mod thin_client;
pub mod tee;
pub mod zk;
pub mod anchors;
pub mod config;
pub mod error;
pub mod challenge;
pub mod protocol;
pub mod session;
pub mod net;
pub mod store;
pub mod wire;

pub use thin_client::ThinClient;
pub use tee::{TeeAttestation, TeeAttestationResult};
pub use zk::{ZkMovementValidator, ZkMovementProof};
pub use anchors::{HcsAnchor, XrplAnchor, DualAnchor, DualAnchorReceipt};
pub use config::IronwallConfig;
pub use error::{IronwallError, IronwallResult};
pub use challenge::{Challenge, ChallengeResponse, ChallengeEngine};
pub use protocol::{ClientMessage, ServerMessage};
pub use session::Session;
pub use net::{NetHandle, NetServer, create_loopback};
pub use store::{ProofStore, StoredProof};
