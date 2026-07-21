//! IWAL hello/welcome over QUIC

use crate::wire::{encode_client_hello, encode_server_welcome, sign_frame, verify_frame};
use anyhow::{bail, Context, Result};
use quinn::{ClientConfig, Endpoint, ServerConfig};
use rustls::pki_types::{CertificateDer, PrivateKeyDer, PrivatePkcs8KeyDer};
use std::net::SocketAddr;
use std::sync::Arc;
use tracing::info;

fn server_cfg() -> Result<(ServerConfig, CertificateDer<'static>)> {
    let cert = rcgen::generate_simple_self_signed(vec!["localhost".into()])?;
    let cert_der = CertificateDer::from(cert.cert);
    let key = PrivateKeyDer::Pkcs8(PrivatePkcs8KeyDer::from(cert.key_pair.serialize_der()));
    let mut crypto = rustls::ServerConfig::builder()
        .with_no_client_auth()
        .with_single_cert(vec![cert_der.clone()], key)?;
    crypto.alpn_protocols = vec![b"ironwall/1".to_vec()];
    let sc = ServerConfig::with_crypto(Arc::new(quinn::crypto::rustls::QuicServerConfig::try_from(crypto)?));
    Ok((sc, cert_der))
}

fn client_cfg(cert: CertificateDer<'static>) -> Result<ClientConfig> {
    let mut roots = rustls::RootCertStore::empty();
    roots.add(cert)?;
    let mut crypto = rustls::ClientConfig::builder()
        .with_root_certificates(roots)
        .with_no_client_auth();
    crypto.alpn_protocols = vec![b"ironwall/1".to_vec()];
    Ok(ClientConfig::new(Arc::new(
        quinn::crypto::rustls::QuicClientConfig::try_from(crypto)?,
    )))
}

/// Client sends signed Hello; server replies signed Welcome. Returns session_id payload bytes.
pub async fn quic_handshake_demo(secret: &[u8]) -> Result<String> {
    let bind: SocketAddr = "127.0.0.1:0".parse()?;
    let (sc, cert) = server_cfg()?;
    let server_ep = Endpoint::server(sc, bind)?;
    let addr = server_ep.local_addr()?;

    let secret_s = secret.to_vec();
    let server = tokio::spawn(async move {
        let inc = server_ep.accept().await.context("accept")?;
        let conn = inc.await.context("hs")?;
        let mut recv = conn.accept_uni().await?;
        let data = recv.read_to_end(64 * 1024).await?;
        let body = verify_frame(&data, &secret_s).context("bad client hmac")?;
        // minimal parse: we just accept and mint welcome
        let welcome = sign_frame(encode_server_welcome("sess-quic-001"), &secret_s);
        let mut send = conn.open_uni().await?;
        send.write_all(&welcome).await?;
        send.finish()?;
        tokio::time::sleep(std::time::Duration::from_millis(50)).await;
        Ok::<_, anyhow::Error>(body.len())
    });

    tokio::time::sleep(std::time::Duration::from_millis(20)).await;

    let mut client_ep = Endpoint::client("0.0.0.0:0".parse()?)?;
    client_ep.set_default_client_config(client_cfg(cert)?);
    let conn = client_ep.connect(addr, "localhost")?.await?;

    let hello = sign_frame(encode_client_hello("player_quic", "0.2.0", "quote-demo"), secret);
    let mut send = conn.open_uni().await?;
    send.write_all(&hello).await?;
    send.finish()?;

    let mut recv = conn.accept_uni().await?;
    let resp = recv.read_to_end(64 * 1024).await?;
    let body = verify_frame(&resp, secret).context("bad server hmac")?;
    let _ = server.await?;

    if body.len() < 10 {
        bail!("short welcome");
    }
    info!(client_hello_len = hello.len(), welcome_len = body.len(), "QUIC IWAL handshake OK");
    Ok("sess-quic-001".into())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn signed_hello_welcome() {
        let sid = quic_handshake_demo(b"ironwall-dev-secret")
            .await
            .expect("handshake");
        assert_eq!(sid, "sess-quic-001");
    }
}
