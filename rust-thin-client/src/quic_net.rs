//! QUIC transport demo for Ironwall (quinn + rustls, ephemeral self-signed cert).

use anyhow::{bail, Context, Result};
use quinn::{ClientConfig, Endpoint, ServerConfig};
use rustls::pki_types::{CertificateDer, PrivateKeyDer, PrivatePkcs8KeyDer};
use std::net::SocketAddr;
use std::sync::Arc;
use tracing::info;

fn make_server_config() -> Result<(ServerConfig, CertificateDer<'static>)> {
    let cert = rcgen::generate_simple_self_signed(vec!["localhost".into()])?;
    let cert_der = CertificateDer::from(cert.cert);
    let key_der = PrivatePkcs8KeyDer::from(cert.key_pair.serialize_der());
    let key = PrivateKeyDer::Pkcs8(key_der);

    let mut server_crypto = rustls::ServerConfig::builder()
        .with_no_client_auth()
        .with_single_cert(vec![cert_der.clone()], key)?;
    server_crypto.alpn_protocols = vec![b"ironwall/1".to_vec()];

    let server_config = ServerConfig::with_crypto(Arc::new(
        quinn::crypto::rustls::QuicServerConfig::try_from(server_crypto)?,
    ));
    Ok((server_config, cert_der))
}

fn make_client_config(server_cert: CertificateDer<'static>) -> Result<ClientConfig> {
    let mut roots = rustls::RootCertStore::empty();
    roots.add(server_cert)?;
    let mut client_crypto = rustls::ClientConfig::builder()
        .with_root_certificates(roots)
        .with_no_client_auth();
    client_crypto.alpn_protocols = vec![b"ironwall/1".to_vec()];
    // rustls 0.23 + quinn 0.11
    let client_config = ClientConfig::new(Arc::new(
        quinn::crypto::rustls::QuicClientConfig::try_from(client_crypto)?,
    ));
    Ok(client_config)
}

/// One-shot QUIC uni-stream echo: server binds on `bind` (port 0 ok), client sends payload, returns ACK||payload.
pub async fn quic_echo_demo(bind: SocketAddr, payload: &[u8]) -> Result<Vec<u8>> {
    let (server_config, cert) = make_server_config()?;
    let mut server_ep = Endpoint::server(server_config, bind).context("bind quic server")?;
    let addr = server_ep.local_addr()?;
    info!(%addr, "QUIC server listening");

    let server_task = tokio::spawn(async move {
        let incoming = server_ep.accept().await.context("accept incoming")?;
        let conn = incoming.await.context("server handshake")?;
        info!("QUIC server connected peer={}", conn.remote_address());

        let mut recv = conn.accept_uni().await.context("server accept_uni")?;
        let data = recv.read_to_end(64 * 1024).await.context("server read")?;

        let mut send = conn.open_uni().await.context("server open_uni")?;
        let mut out = b"IWAL-ACK:".to_vec();
        out.extend_from_slice(&data);
        send.write_all(&out).await?;
        send.finish()?;
        // keep conn alive briefly
        tokio::time::sleep(std::time::Duration::from_millis(100)).await;
        Ok::<_, anyhow::Error>(())
    });

    // Give server a moment to listen
    tokio::time::sleep(std::time::Duration::from_millis(20)).await;

    let client_cfg = make_client_config(cert)?;
    let mut client_ep = Endpoint::client("0.0.0.0:0".parse()?)?;
    client_ep.set_default_client_config(client_cfg);

    let connecting = client_ep.connect(addr, "localhost").context("start connect")?;
    let conn = tokio::time::timeout(std::time::Duration::from_secs(5), connecting)
        .await
        .context("client connect timeout")?
        .context("client handshake")?;
    info!("QUIC client connected");

    let mut send = conn.open_uni().await?;
    send.write_all(payload).await?;
    send.finish()?;

    let mut recv = tokio::time::timeout(std::time::Duration::from_secs(5), conn.accept_uni())
        .await
        .context("accept_uni timeout")?
        .context("accept_uni")?;
    let response = tokio::time::timeout(std::time::Duration::from_secs(5), recv.read_to_end(64 * 1024))
        .await
        .context("read timeout")?
        .context("read")?;

    let _ = tokio::time::timeout(std::time::Duration::from_secs(2), server_task).await;

    if !response.starts_with(b"IWAL-ACK:") {
        bail!("bad response prefix");
    }
    Ok(response)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn echo_roundtrip() {
        let bind: SocketAddr = "127.0.0.1:0".parse().unwrap();
        let resp = quic_echo_demo(bind, b"hello-ironwall")
            .await
            .expect("quic echo");
        assert!(resp.starts_with(b"IWAL-ACK:"));
        assert!(resp.ends_with(b"hello-ironwall"));
    }
}
