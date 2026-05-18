//! ironwall-launcher — core library
//!
//! Scans a game directory for signed modules (DLLs / SOs), hashes each one
//! with SHA3-256, submits the manifest to the Ironwall TEE attestation broker,
//! and boots the game executable only after receiving a valid session token.
//!
//! Architecture:
//!
//!   [Game Dir] ──scan──▶ [DllScanner]
//!                              │
//!                         sha3_256 each
//!                              │
//!                    [ModuleManifest] ──HTTP──▶ [TEE Broker (Python)]
//!                                                      │
//!                                               verify signatures
//!                                               SGX/SEV attestation
//!                                                      │
//!                                            [SessionToken (JWT, 60s)]
//!                                                      │
//!                                        [GameLauncher::boot(token)] ──▶ game.exe
//!
//! This is the Rust rewrite of capture_input() + launcher referenced in
//! issue #89 (bounty: 500 HBAR).

pub mod scanner;
pub mod manifest;
pub mod broker;
pub mod launcher;
pub mod crypto;
pub mod error;

pub use error::LauncherError;
pub use manifest::{ModuleEntry, ModuleManifest};
pub use scanner::DllScanner;
pub use broker::{AttestationBroker, SessionToken};
pub use launcher::GameLauncher;
