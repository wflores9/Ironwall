//! GameLauncher — boots the game executable after successful attestation.
//!
//! The session token is injected as an environment variable and command-line
//! argument so the game's thin client can use it immediately on first
//! WebSocket connect without re-negotiating.
//!
//! Boot sequence:
//!   1. Verify token is not expired (should never be, but belt-and-suspenders)
//!   2. Set IRONWALL_SESSION_TOKEN env var
//!   3. Spawn game process with --ironwall-token <jwt> argument
//!   4. Monitor process — if it exits abnormally, report to broker
//!
//! On Windows: uses CreateProcess with STARTUPINFO for proper inheritance.
//! On Linux:   uses std::process::Command.

use crate::error::LauncherError;
use crate::broker::SessionToken;
use std::path::{Path, PathBuf};
use std::process::Command;
use tracing::{error, info};

/// Configuration for game process launch.
#[derive(Debug, Clone)]
pub struct LaunchConfig {
    /// Path to the game executable.
    pub game_exe: PathBuf,

    /// Additional arguments passed to the game (after the Ironwall args).
    pub extra_args: Vec<String>,

    /// Working directory for the game process. Defaults to game_exe parent.
    pub working_dir: Option<PathBuf>,

    /// If true, wait for the game process to exit before returning.
    /// If false, detach and return immediately.
    pub wait: bool,
}

impl LaunchConfig {
    pub fn new(game_exe: impl Into<PathBuf>) -> Self {
        Self {
            game_exe: game_exe.into(),
            extra_args: Vec::new(),
            working_dir: None,
            wait: false,
        }
    }

    pub fn with_args(mut self, args: Vec<String>) -> Self {
        self.extra_args = args;
        self
    }

    pub fn with_wait(mut self) -> Self {
        self.wait = true;
        self
    }
}

/// Launches the game process after attestation.
pub struct GameLauncher {
    config: LaunchConfig,
}

impl GameLauncher {
    pub fn new(config: LaunchConfig) -> Self {
        Self { config }
    }

    /// Boot the game with the attested session token.
    ///
    /// Injects the token via:
    ///   - Environment variable: IRONWALL_SESSION_TOKEN=<jwt>
    ///   - CLI argument:         --ironwall-token <jwt>
    ///
    /// Returns the process exit code if wait=true, or 0 immediately if detached.
    pub fn boot(&self, token: &SessionToken) -> Result<i32, LauncherError> {
        // Verify game executable exists
        if !self.config.game_exe.exists() {
            return Err(LauncherError::GameNotFound {
                path: self.config.game_exe.to_string_lossy().to_string(),
            });
        }

        // Verify token hasn't expired
        if token.is_expired() {
            return Err(LauncherError::InvalidSessionToken);
        }

        let working_dir = self.config.working_dir.clone().unwrap_or_else(|| {
            self.config.game_exe
                .parent()
                .unwrap_or(Path::new("."))
                .to_path_buf()
        });

        info!(
            "Launching {} with Ironwall session token (player={})",
            self.config.game_exe.display(),
            token.player_id
        );

        let mut cmd = Command::new(&self.config.game_exe);
        cmd.current_dir(&working_dir)
            .env("IRONWALL_SESSION_TOKEN", &token.raw)
            .env("IRONWALL_PLAYER_ID", &token.player_id)
            .arg("--ironwall-token")
            .arg(&token.raw)
            .arg("--ironwall-player")
            .arg(&token.player_id)
            .args(&self.config.extra_args);

        let mut child = cmd.spawn().map_err(|e| {
            LauncherError::GameLaunchFailed(format!(
                "Failed to spawn {}: {e}",
                self.config.game_exe.display()
            ))
        })?;

        info!("Game process started (PID {})", child.id());

        if self.config.wait {
            let status = child.wait().map_err(|e| {
                LauncherError::GameLaunchFailed(format!("Wait failed: {e}"))
            })?;

            let code = status.code().unwrap_or(-1);
            if code != 0 {
                error!("Game exited with code {}", code);
            } else {
                info!("Game exited cleanly");
            }
            Ok(code)
        } else {
            Ok(0)
        }
    }
}
