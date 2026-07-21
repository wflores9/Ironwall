use ironwall::{Matchmaker, MatchmakerConfig, TeeAttestation};
use tracing::{info, Level};
use tracing_subscriber::FmtSubscriber;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let subscriber = FmtSubscriber::builder().with_max_level(Level::INFO).finish();
    tracing::subscriber::set_global_default(subscriber)?;

    info!("Ironwall Matchmaker starting...");
    let mut mm = Matchmaker::new(MatchmakerConfig {
        players_per_match: 2,
        ..Default::default()
    });

    let tee = TeeAttestation::new();
    for i in 0..5 {
        let att = tee.generate_attestation().await?;
        let pid = format!("player_{i}");
        let ticket = mm.lobby_mut().issue_ticket(&pid, &att.quote_hash);
        let sid = mm.enqueue(&ticket);
        info!("join {pid} session={}", sid.as_deref().unwrap_or("REJECT"));
        for m in mm.tick() {
            info!("MATCH {} -> {:?}", m.match_id, m.players.iter().map(|s| &s[..8.min(s.len())]).collect::<Vec<_>>());
        }
    }
    info!(
        "queue_remaining={} active_matches={}",
        mm.queue_size(),
        mm.active_matches()
    );
    info!("Ironwall Matchmaker shut down");
    Ok(())
}
