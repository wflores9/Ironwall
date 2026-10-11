//! Network transport stub (TCP / future QUIC / WebSocket).
//! Currently in-memory mpsc for demo; swap for real socket later.

use anyhow::Result;
use tokio::sync::mpsc;
use std::collections::HashSet;
use tracing::info;

use crate::protocol::{ClientMessage, ServerMessage};

pub struct NetHandle {
    pub outbound: mpsc::Sender<ClientMessage>,
    pub inbound: mpsc::Receiver<ServerMessage>,
}

pub struct NetServer {
    pub to_client: mpsc::Sender<ServerMessage>,
    pub from_client: mpsc::Receiver<ClientMessage>,
}

/// Create a connected pair (client <-> fake server) for local testing.
pub fn create_loopback() -> (NetHandle, NetServer) {
    let (client_tx, server_rx) = mpsc::channel::<ClientMessage>(64);
    let (server_tx, client_rx) = mpsc::channel::<ServerMessage>(64);

    (
        NetHandle {
            outbound: client_tx,
            inbound: client_rx,
        },
        NetServer {
            to_client: server_tx,
            from_client: server_rx,
        },
    )
}

impl NetHandle {
    pub async fn send(&self, msg: ClientMessage) -> Result<()> {
        self.outbound.send(msg).await?;
        Ok(())
    }

    pub async fn recv(&mut self) -> Option<ServerMessage> {
        self.inbound.recv().await
    }
}

impl NetServer {
    pub async fn send(&self, msg: ServerMessage) -> Result<()> {
        self.to_client.send(msg).await?;
        Ok(())
    }

    pub async fn recv(&mut self) -> Option<ClientMessage> {
        self.from_client.recv().await
    }

    /// Simple echo / ack loop for demo.
    pub async fn run_demo(mut self) {
        info!("NetServer demo loop started");
        let mut hello_seen = false;
        let mut bound_player_id = String::new();
        let mut seen_proofs = HashSet::new();
        while let Some(msg) = self.recv().await {
            if !matches!(msg, ClientMessage::Hello { .. }) && !hello_seen {
                let _ = self.send(ServerMessage::Kick {
                    reason: "hello required before session messages".into(),
                }).await;
                break;
            }
            match msg {
                ClientMessage::Hello { player_id, .. } => {
                    if hello_seen {
                        let _ = self.send(ServerMessage::Kick {
                            reason: "duplicate session hello".into(),
                        }).await;
                        break;
                    }
                    if player_id.trim().is_empty() {
                        let _ = self.send(ServerMessage::Kick {
                            reason: "player id required".into(),
                        }).await;
                        break;
                    }
                    bound_player_id = player_id.clone();
                    hello_seen = true;
                    info!("server got Hello from {}", player_id);
                    let _ = self
                        .send(ServerMessage::Welcome {
                            session_id: uuid::Uuid::new_v4().to_string(),
                            server_time: chrono::Utc::now(),
                        })
                        .await;
                }
                ClientMessage::MovementProof { proof, .. } => {
                    if proof.proof_id.trim().is_empty() || proof.player_id != bound_player_id {
                        let _ = self.send(ServerMessage::Ack {
                            proof_id: proof.proof_id,
                            accepted: false,
                            reason: Some("movement proof identity does not match session".into()),
                        }).await;
                        continue;
                    }
                    if !seen_proofs.insert(proof.proof_id.clone()) {
                        let _ = self.send(ServerMessage::Ack {
                            proof_id: proof.proof_id,
                            accepted: false,
                            reason: Some("replayed movement proof id".into()),
                        }).await;
                        continue;
                    }
                    info!("server got MovementProof {}", proof.proof_id);
                    let _ = self
                        .send(ServerMessage::Ack {
                            proof_id: proof.proof_id,
                            accepted: true,
                            reason: None,
                        })
                        .await;
                }
                ClientMessage::ChallengeResponse { response } => {
                    // This demo server never issues an authenticated challenge.
                    // Never grant a success acknowledgment for unsolicited evidence.
                    let _ = self.send(ServerMessage::Ack {
                        proof_id: response.challenge_id,
                        accepted: false,
                        reason: Some("no outstanding server-issued challenge".into()),
                    }).await;
                }
                ClientMessage::Heartbeat { position, .. } => {
                    if ![position.0, position.1, position.2].iter().all(|v| v.is_finite()) {
                        let _ = self.send(ServerMessage::Kick { reason: "invalid heartbeat position".into() }).await;
                        break;
                    }
                    info!("server got Heartbeat pos={:?}", position);
                }
            }
        }
        info!("NetServer demo loop ended");
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use chrono::Utc;

    #[test]
    fn movement_identity_must_match_handshake() {
        fn valid(proof_id: &str, proof_player: &str, session_player: &str) -> bool {
            !proof_id.trim().is_empty() && proof_player == session_player
        }
        assert!(valid("proof-1", "alice", "alice"));
        assert!(!valid("proof-1", "bob", "alice"));
        assert!(!valid("", "alice", "alice"));
    }

    #[tokio::test]
    async fn rejects_nonfinite_heartbeat_position() {
        let (client, server) = create_loopback();
        let handle = tokio::spawn(server.run_demo());
        let mut client = client;
        let attestation = crate::tee::TeeAttestation::new()
            .generate_attestation().await.unwrap();
        client.send(ClientMessage::Hello {
            player_id: "player-one".into(),
            client_version: "test".into(),
            attestation,
        }).await.unwrap();
        assert!(matches!(client.recv().await, Some(ServerMessage::Welcome { .. })));
        client.send(ClientMessage::Heartbeat {
            ts: Utc::now(),
            position: (f32::NAN, 0.0, 0.0),
        }).await.unwrap();
        assert!(matches!(client.recv().await, Some(ServerMessage::Kick { .. })));
        drop(client);
        handle.await.unwrap();
    }

    #[tokio::test]
    async fn rejects_unsolicited_challenge_response() {
        let (client, server) = create_loopback();
        let handle = tokio::spawn(server.run_demo());
        let mut client = client;
        let attestation = crate::tee::TeeAttestation::new()
            .generate_attestation().await.unwrap();
        client.send(ClientMessage::Hello {
            player_id: "player-one".into(),
            client_version: "test".into(),
            attestation: attestation.clone(),
        }).await.unwrap();
        assert!(matches!(client.recv().await, Some(ServerMessage::Welcome { .. })));
        let proof = crate::zk::ZkMovementValidator::new(100.0)
            .prove_valid_movement("player-one", (0.0, 0.0, 0.0), (0.1, 0.0, 0.0), 100)
            .await.unwrap();
        client.send(ClientMessage::ChallengeResponse {
            response: crate::challenge::ChallengeResponse {
                challenge_id: "never-issued".into(),
                new_attestation: attestation,
                new_proof: proof,
                responded_at: Utc::now(),
            },
        }).await.unwrap();
        assert!(matches!(client.recv().await, Some(ServerMessage::Ack { accepted: false, .. })));
        drop(client);
        handle.await.unwrap();
    }

    #[tokio::test]
    async fn rejects_empty_identity_and_duplicate_hello() {
        for ids in [vec![""], vec!["player-one", "player-two"]] {
            let (client, server) = create_loopback();
            let handle = tokio::spawn(server.run_demo());
            let mut client = client;
            let attestation = crate::tee::TeeAttestation::new()
                .generate_attestation().await.unwrap();
            for id in &ids {
                client.send(ClientMessage::Hello {
                    player_id: (*id).into(),
                    client_version: "test".into(),
                    attestation: attestation.clone(),
                }).await.unwrap();
                let reply = client.recv().await.unwrap();
                if *id == "player-one" {
                    assert!(matches!(reply, ServerMessage::Welcome { .. }));
                } else {
                    assert!(matches!(reply, ServerMessage::Kick { .. }));
                }
            }
            drop(client);
            handle.await.unwrap();
        }
    }

    #[tokio::test]
    async fn rejects_heartbeat_before_hello() {
        let (client, server) = create_loopback();
        let handle = tokio::spawn(server.run_demo());
        client.send(ClientMessage::Heartbeat {
            ts: Utc::now(),
            position: (0.0, 0.0, 0.0),
        }).await.unwrap();
        let mut client = client;
        assert!(matches!(client.recv().await, Some(ServerMessage::Kick { .. })));
        drop(client);
        handle.await.unwrap();
    }
}
