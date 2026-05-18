//! HTTP client for the Ironwall TEE attestation broker (Python Layer 3).
//!
//! Submits the ModuleManifest to the broker's `/attest` endpoint and
//! receives a signed JWT session token (60s TTL) on success.
//!
//! The broker runs the full SGX/SEV verification chain:
//!   1. Verifies each module's SHA3-256 hash against ModuleSigner records
//!   2. Checks CT log anchors
//!   3. Generates SGX attestation receipt
//!   4. Issues signed JWT session token
//!   5. Commits any violations to Hedera HCS
//!
//! If the broker returns status="BANNED", the launcher refuses to boot
//! the game and logs the reason. This is a hard denial — no fallback.

use crate::error::LauncherError;
use crate::manifest::{AttestationResponse, ModuleManifest};
use reqwest::Client;
use serde::{Deserialize, Serialize};
use std::time::Duration;
use tracing::{error, info, warn};

/// A validated session token from the TEE broker.
#[derive(Debug, Clone)]
pub struct SessionToken {
    /// Raw JWT string — passed to the game server on connect.
    pub raw: String,

    /// Player ID this token was issued for.
    pub player_id: String,

    /// Unix timestamp when the token expires (60s from issuance).
    pub expires_at: u64,
}

impl SessionToken {
    pub fn is_expired(&self) -> bool {
        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs();
        now >= self.expires_at
    }
}

/// Request body sent to the broker's /attest endpoint.
#[derive(Debug, Serialize)]
struct AttestRequest {
    manifest: ModuleManifest,
    /// Optional: pre-computed SGX quote from local hardware (HW mode only).
    sgx_quote: Option<String>,
}

/// Configuration for the attestation broker client.
#[derive(Debug, Clone)]
pub struct BrokerConfig {
    /// Base URL of the Python TEE broker (e.g. "http://localhost:8766").
    pub base_url: String,

    /// Request timeout. Default: 10 seconds.
    pub timeout: Duration,

    /// Number of retry attempts on transient failures. Default: 3.
    pub retries: u32,
}

impl BrokerConfig {
    pub fn new(base_url: impl Into<String>) -> Self {
        Self {
            base_url: base_url.into(),
            timeout: Duration::from_secs(10),
            retries: 3,
        }
    }

    pub fn localhost() -> Self {
        Self::new("http://127.0.0.1:8766")
    }
}

impl Default for BrokerConfig {
    fn default() -> Self {
        Self::localhost()
    }
}

/// Client for the Ironwall TEE attestation broker.
pub struct AttestationBroker {
    config: BrokerConfig,
    client: Client,
}

impl AttestationBroker {
    pub fn new(config: BrokerConfig) -> Result<Self, LauncherError> {
        let client = Client::builder()
            .timeout(config.timeout)
            .build()?;
        Ok(Self { config, client })
    }

    /// Submit a module manifest for attestation.
    ///
    /// Returns a SessionToken on success.
    /// Returns LauncherError::AttestationFailed or ModuleBanned on failure.
    /// This is a hard gate — the game will not boot without a valid token.
    pub async fn attest(
        &self,
        manifest: ModuleManifest,
        sgx_quote: Option<String>,
    ) -> Result<SessionToken, LauncherError> {
        let player_id = manifest.player_id.clone();
        let url = format!("{}/attest", self.config.base_url);

        let body = AttestRequest { manifest, sgx_quote };

        info!(
            "Submitting manifest ({} modules) to broker at {}",
            body.manifest_module_count(),
            url
        );

        let mut last_err = None;

        for attempt in 1..=self.config.retries {
            match self.client.post(&url).json(&body).send().await {
                Ok(resp) => {
                    let status = resp.status();
                    let attest_resp: AttestationResponse = resp.json().await?;

                    match attest_resp.status.as_str() {
                        "ATTESTED" => {
                            let token = attest_resp.session_token.ok_or_else(|| {
                                LauncherError::AttestationFailed {
                                    reason: "Broker returned ATTESTED but no token".into(),
                                }
                            })?;

                            let expires_at = std::time::SystemTime::now()
                                .duration_since(std::time::UNIX_EPOCH)
                                .unwrap_or_default()
                                .as_secs()
                                + 60;

                            info!("Attestation successful for player {}", player_id);
                            return Ok(SessionToken { raw: token, player_id, expires_at });
                        }

                        "BANNED" => {
                            let reason = attest_resp.reason.unwrap_or_else(|| "unknown".into());
                            let modules = attest_resp.banned_modules.unwrap_or_default();
                            error!(
                                "Module ban: reason={} modules={:?}",
                                reason, modules
                            );
                            return Err(LauncherError::AttestationFailed { reason });
                        }

                        other => {
                            warn!("Unexpected broker status: {} (HTTP {})", other, status);
                            last_err = Some(LauncherError::AttestationFailed {
                                reason: format!("Unexpected status: {other}"),
                            });
                        }
                    }
                }
                Err(e) => {
                    warn!("Broker request failed (attempt {}/{}): {}", attempt, self.config.retries, e);
                    last_err = Some(LauncherError::BrokerUnreachable {
                        url: url.clone(),
                        source: e,
                    });
                    tokio::time::sleep(Duration::from_millis(500 * attempt as u64)).await;
                }
            }
        }

        Err(last_err.unwrap_or(LauncherError::AttestationFailed {
            reason: "Max retries exceeded".into(),
        }))
    }

    /// Ping the broker to verify it's reachable before scanning.
    pub async fn health_check(&self) -> bool {
        let url = format!("{}/health", self.config.base_url);
        self.client.get(&url).send().await.map(|r| r.status().is_success()).unwrap_or(false)
    }
}

// Helper — AttestRequest doesn't have direct access to manifest fields
// without ownership so we use a wrapper method
impl AttestRequest {
    fn manifest_module_count(&self) -> usize {
        self.manifest.modules.len()
    }
}
