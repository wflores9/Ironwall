use thiserror::Error;

#[derive(Debug, Error)]
pub enum LauncherError {
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),

    #[error("Hash mismatch for module '{path}': expected {expected}, got {actual}")]
    HashMismatch {
        path: String,
        expected: String,
        actual: String,
    },

    #[error("TEE attestation failed: {reason}")]
    AttestationFailed { reason: String },

    #[error("Session token invalid or expired")]
    InvalidSessionToken,

    #[error("Broker unreachable at {url}: {source}")]
    BrokerUnreachable {
        url: String,
        #[source]
        source: reqwest::Error,
    },

    #[error("Module banned by TEE: {path} — reason: {reason}")]
    ModuleBanned { path: String, reason: String },

    #[error("Game executable not found at '{path}'")]
    GameNotFound { path: String },

    #[error("Game process failed to start: {0}")]
    GameLaunchFailed(String),

    #[error("Serialisation error: {0}")]
    Serialisation(#[from] serde_json::Error),

    #[error("HTTP error: {0}")]
    Http(#[from] reqwest::Error),

    #[error("Scan error: {0}")]
    Scan(String),
}
