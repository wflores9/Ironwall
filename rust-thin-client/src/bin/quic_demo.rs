use ironwall::quic_iwal::quic_handshake_demo;
use ironwall::quic_net::quic_echo_demo;
use tracing::{info, Level};
use tracing_subscriber::FmtSubscriber;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let subscriber = FmtSubscriber::builder().with_max_level(Level::INFO).finish();
    tracing::subscriber::set_global_default(subscriber)?;

    info!("Ironwall QUIC demo starting...");
    let bind = "127.0.0.1:0".parse()?;
    let resp = quic_echo_demo(bind, b"ironwall-quic-v1").await?;
    info!("echo: {}", String::from_utf8_lossy(&resp));

    let sid = quic_handshake_demo(b"ironwall-dev-secret").await?;
    info!("IWAL handshake session_id={sid}");
    info!("Ironwall QUIC demo OK");
    Ok(())
}
