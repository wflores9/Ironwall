//! Ironwall verifier stub (separate binary).
//! Future: validates TEE quotes, ZK proofs, dual anchors, issues challenges.

use anyhow::Result;
use tracing::{info, Level};
use tracing_subscriber::FmtSubscriber;

use ironwall::{ ModerationEngine, RateLimitConfig, BanStore, TeeAttestation, ZkMovementValidator, HcsAnchor, XrplAnchor, DualAnchor, ChallengeEngine, IronwallConfig, Lobby, LobbyConfig };

#[tokio::main]
async fn main() -> Result<()> {
    let subscriber = FmtSubscriber::builder()
        .with_max_level(Level::INFO)
        .finish();
    tracing::subscriber::set_global_default(subscriber)?;

    info!("Ironwall Verifier starting...");

    let cfg = IronwallConfig::default();
    let tee = TeeAttestation::new();
    let att = tee.generate_attestation().await?;
    info!("Verifier TEE quote: {}", att.quote_hash);

    let zk = ZkMovementValidator::new(cfg.max_speed_units_per_sec);

    // Accept a clean proof
    let ok = zk.prove_valid_movement("player_001", (0.0, 0.0, 0.0), (0.1, 0.0, 0.0), 50).await;
    info!("Clean proof accepted: {}", ok.is_ok());

    // Reject speedhack
    let bad = zk.prove_valid_movement("player_001", (0.0, 0.0, 0.0), (50.0, 0.0, 0.0), 16).await;
    info!("Speedhack rejected: {}", bad.is_err());

    let hcs = HcsAnchor::new(&cfg.hcs_topic_id);
    let xrpl = XrplAnchor::new(&cfg.xrpl_account);
    let dual = DualAnchor::new(hcs, xrpl);

    if let Ok(proof) = ok {
        let receipt = dual.anchor_proof(&att, &proof).await?;
        info!("Verifier dual-anchored: {}", receipt.combined_hash);
    }

    let engine = ChallengeEngine::new();
    let ch = engine.issue_challenge("some-proof", "anomaly detected");
    info!("Verifier issued challenge: {}", ch.challenge_id);

    
    // Moderation demo
    let bans = BanStore::new("ironwall_bans.jsonl");
    let mut mod_eng = ModerationEngine::new(RateLimitConfig {
        max_events: 5,
        window: std::time::Duration::from_secs(2),
        ban_after_violations: 2,
        ban_duration: std::time::Duration::from_secs(60),
    });
    bans.load_into(&mut mod_eng);
    let mut allowed = 0;
    let mut denied = 0;
    for _ in 0..12 {
        if mod_eng.allow("speedy_joe", "proof") { allowed += 1; } else { denied += 1; }
    }
    if mod_eng.is_banned("speedy_joe") {
        bans.save_ban("speedy_joe", "rate_limit", 60);
    }
    info!("Moderation demo: allowed={allowed} denied={denied} banned={} strikes={}",
        mod_eng.is_banned("speedy_joe"), mod_eng.strike_count("speedy_joe"));
    info!("Ban store: {}", bans.path().display());

    let mut lobby = Lobby::new(LobbyConfig::default());
    let ticket = lobby.issue_ticket("player_001", "demo-quote");
    let sid = lobby.open_session(&ticket).unwrap_or_default();
    info!("Lobby session={sid} active={} ticket_ok={}", lobby.active_count(), lobby.validate_ticket(&ticket));
    lobby.close_session(&sid);
    info!("Ironwall Verifier shut down");
    Ok(())
}

// moderation demo at end of main — append before final Ok
