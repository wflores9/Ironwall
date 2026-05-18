//! Module manifest — the signed inventory of DLLs sent to the TEE broker.

use serde::{Deserialize, Serialize};
use std::path::PathBuf;

/// A single scanned module entry.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModuleEntry {
    /// Absolute path to the module on disk.
    pub path: String,

    /// Filename only (e.g. "amd_fidelityfx_dx12.dll").
    pub filename: String,

    /// File size in bytes.
    pub size_bytes: u64,

    /// SHA3-256 hex digest of the file contents.
    /// Must match the mod_hash in the ModuleSigner record from Layer 2.
    pub sha3_256: String,

    /// Unix timestamp (seconds) of the file's last modification.
    pub mtime: u64,

    /// True if this module has a corresponding signature record.
    /// Modules with no signature record cause the broker to deny the session.
    pub has_signature: bool,
}

/// The full manifest submitted to the TEE attestation broker.
#[derive(Debug, Serialize, Deserialize)]
pub struct ModuleManifest {
    /// Unique session identifier (UUID generated per launch).
    pub session_id: String,

    /// Player / device identifier.
    pub player_id: String,

    /// Game identifier (e.g. "cod25", "ironwall-demo").
    pub game_id: String,

    /// Launcher version.
    pub launcher_version: String,

    /// All scanned module entries.
    pub modules: Vec<ModuleEntry>,

    /// SHA3-256 of the serialised modules array — manifest integrity check.
    pub manifest_hash: String,

    /// Unix timestamp (seconds) of manifest creation.
    pub ts: u64,
}

impl ModuleManifest {
    /// Build a manifest from a list of entries, computing the manifest hash.
    pub fn new(
        session_id: String,
        player_id: String,
        game_id: String,
        modules: Vec<ModuleEntry>,
    ) -> Self {
        let ts = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs();

        // Hash the module list for integrity
        let modules_json = serde_json::to_string(&modules).unwrap_or_default();
        let manifest_hash = crate::crypto::sha3_256_hex(modules_json.as_bytes());

        Self {
            session_id,
            player_id,
            game_id,
            launcher_version: env!("CARGO_PKG_VERSION").to_string(),
            modules,
            manifest_hash,
            ts,
        }
    }

    /// Total number of modules scanned.
    pub fn module_count(&self) -> usize {
        self.modules.len()
    }

    /// Total bytes scanned across all modules.
    pub fn total_bytes(&self) -> u64 {
        self.modules.iter().map(|m| m.size_bytes).sum()
    }

    /// Modules missing a signature record — broker will deny if any exist.
    pub fn unsigned_modules(&self) -> Vec<&ModuleEntry> {
        self.modules.iter().filter(|m| !m.has_signature).collect()
    }
}

/// Response from the TEE attestation broker.
#[derive(Debug, Deserialize)]
pub struct AttestationResponse {
    /// "ATTESTED" | "BANNED" | "DENIED"
    pub status: String,

    /// JWT session token (60s TTL). Present only when status == "ATTESTED".
    pub session_token: Option<String>,

    /// SGX/SEV attestation receipt. Committed to Hedera HCS by the broker.
    pub tee_receipt: Option<serde_json::Value>,

    /// Denial reason. Present when status != "ATTESTED".
    pub reason: Option<String>,

    /// Specific modules that triggered a ban.
    pub banned_modules: Option<Vec<String>>,
}
