//! ironwall-launcher — CLI entrypoint
//!
//! Usage:
//!   ironwall-launcher --game-dir "C:\cod25" --game-exe "C:\cod25\cod.exe" --player-id "0.0.1234"
//!
//! What it does:
//!   1. Scans all DLLs in --game-dir with SHA3-256
//!   2. Submits manifest to TEE attestation broker
//!   3. Receives signed JWT session token
//!   4. Boots --game-exe with token injected as env var + CLI arg
//!   5. Game's thin client uses token on first WebSocket connect

use anyhow::Result;
use clap::Parser;
use ironwall_launcher::{
    broker::{AttestationBroker, BrokerConfig},
    launcher::{GameLauncher, LaunchConfig},
    manifest::ModuleManifest,
    scanner::{DllScanner, ScanConfig},
};
use std::collections::HashMap;
use std::path::PathBuf;
use tracing::{error, info, warn};
use tracing_subscriber::EnvFilter;

#[derive(Parser, Debug)]
#[command(
    name = "ironwall-launcher",
    version,
    about = "Ironwall native launcher — scans game DLLs, attests with TEE, boots game",
    long_about = None
)]
struct Args {
    /// Game installation directory to scan for modules
    #[arg(long, short = 'd')]
    game_dir: PathBuf,

    /// Game executable to launch after successful attestation
    #[arg(long, short = 'e')]
    game_exe: PathBuf,

    /// Player identifier (XRPL/Hedera account ID or UUID)
    #[arg(long, short = 'p')]
    player_id: String,

    /// Game identifier (e.g. "cod25", "ironwall-demo")
    #[arg(long, short = 'g', default_value = "unknown")]
    game_id: String,

    /// Ironwall TEE broker URL
    #[arg(long, default_value = "http://127.0.0.1:8766")]
    broker_url: String,

    /// Path to JSON file containing known module hashes (from ModuleSigner)
    /// Format: {"filename.dll": ["sha3_256_hex", ...], ...}
    #[arg(long)]
    known_hashes: Option<PathBuf>,

    /// SGX quote (hex) for hardware attestation mode. Omit for SIM mode.
    #[arg(long)]
    sgx_quote: Option<String>,

    /// Session UUID (auto-generated if not provided)
    #[arg(long)]
    session_id: Option<String>,

    /// Wait for the game process to exit before returning
    #[arg(long, default_value_t = false)]
    wait: bool,

    /// Additional arguments passed through to the game executable
    #[arg(last = true)]
    game_args: Vec<String>,
}

#[tokio::main]
async fn main() -> Result<()> {
    // Initialise structured logging
    tracing_subscriber::fmt()
        .with_env_filter(
            EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| EnvFilter::new("ironwall_launcher=info")),
        )
        .with_target(false)
        .init();

    let args = Args::parse();

    info!("╔══════════════════════════════════════╗");
    info!("║      IRONWALL LAUNCHER v{}         ║", env!("CARGO_PKG_VERSION"));
    info!("╚══════════════════════════════════════╝");
    info!("Game dir:  {}", args.game_dir.display());
    info!("Game exe:  {}", args.game_exe.display());
    info!("Player ID: {}", args.player_id);
    info!("Broker:    {}", args.broker_url);

    // ── Step 1: Load known hashes (if provided) ───────────────────────
    // Accepts both flat {"file.dll": "hash"} and multi-hash {"file.dll": ["h1","h2"]} formats.
    let known_hashes: HashMap<String, Vec<String>> = if let Some(ref path) = args.known_hashes {
        let json = std::fs::read_to_string(path)?;
        let raw: HashMap<String, serde_json::Value> = serde_json::from_str(&json)?;
        raw.into_iter()
            .map(|(k, v)| {
                let hashes = match v {
                    serde_json::Value::String(s) => vec![s],
                    serde_json::Value::Array(a) => a
                        .into_iter()
                        .filter_map(|x| x.as_str().map(String::from))
                        .collect(),
                    _ => vec![],
                };
                (k, hashes)
            })
            .collect()
    } else {
        warn!("No --known-hashes provided — all modules will be flagged as unsigned");
        HashMap::new()
    };

    // ── Step 2: Scan game directory ───────────────────────────────────
    info!("Scanning {}...", args.game_dir.display());
    let scan_config = ScanConfig::new(&args.game_dir).with_known_hashes(known_hashes);
    let scanner = DllScanner::new(scan_config);
    let modules = scanner.scan().await?;

    let unsigned: Vec<_> = modules.iter().filter(|m| !m.has_signature).collect();
    if !unsigned.is_empty() {
        warn!(
            "{} unsigned modules found — broker may deny session",
            unsigned.len()
        );
        for m in &unsigned {
            warn!("  unsigned: {}", m.filename);
        }
    }

    // ── Step 3: Build manifest ────────────────────────────────────────
    let session_id = args.session_id.unwrap_or_else(|| {
        format!("{:x}", std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default()
            .as_nanos())
    });

    let manifest = ModuleManifest::new(
        session_id,
        args.player_id.clone(),
        args.game_id,
        modules,
    );

    info!(
        "Manifest: {} modules, {:.1} MB, hash={}…",
        manifest.module_count(),
        manifest.total_bytes() as f64 / 1_048_576.0,
        &manifest.manifest_hash[..16],
    );

    // ── Step 4: Submit to TEE broker ──────────────────────────────────
    let broker_config = BrokerConfig::new(&args.broker_url);
    let broker = AttestationBroker::new(broker_config)?;

    // Health check first
    if !broker.health_check().await {
        warn!("Broker health check failed — proceeding anyway");
    }

    let token = match broker.attest(manifest, args.sgx_quote).await {
        Ok(t) => {
            info!("✓ Attestation successful — session token issued");
            t
        }
        Err(e) => {
            error!("✗ Attestation FAILED: {}", e);
            error!("Game will not launch without a valid attestation.");
            std::process::exit(1);
        }
    };

    // ── Step 5: Boot the game ─────────────────────────────────────────
    info!("Launching game...");
    let launch_config = LaunchConfig::new(&args.game_exe)
        .with_args(args.game_args)
        .with_wait();  // always wait so we can report exit code

    let launcher = GameLauncher::new(launch_config);
    match launcher.boot(&token) {
        Ok(code) => {
            info!("Game exited with code {}", code);
            std::process::exit(code);
        }
        Err(e) => {
            error!("Game launch failed: {}", e);
            std::process::exit(1);
        }
    }
}
