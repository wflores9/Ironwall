use ironwall::quic_net::quic_echo_demo;
use tracing::{info, Level};
use tracing_subscriber::FmtSubscriber;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let subscriber = FmtSubscriber::builder().with_max_level(Level::INFO).finish();
    tracing::subscriber::set_global_default(subscriber)?;

    info!("Ironwall QUIC demo starting...");
    let bind = "127.0.0.1:0".parse()?;
    let payload = b"ironwall-quic-v1";
    let resp = quic_echo_demo(bind, payload).await?;
    info!("response: {}", String::from_utf8_lossy(&resp));
    info!("Ironwall QUIC demo OK");
    Ok(())
}
