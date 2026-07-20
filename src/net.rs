//! Network transport stub (TCP / future QUIC / WebSocket).
//! Currently in-memory mpsc for demo; swap for real socket later.

use anyhow::Result;
use tokio::sync::mpsc;
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
        while let Some(msg) = self.recv().await {
            match msg {
                ClientMessage::Hello { player_id, .. } => {
                    info!("server got Hello from {}", player_id);
                    let _ = self
                        .send(ServerMessage::Welcome {
                            session_id: uuid::Uuid::new_v4().to_string(),
                            server_time: chrono::Utc::now(),
                        })
                        .await;
                }
                ClientMessage::MovementProof { proof, .. } => {
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
                    info!("server got ChallengeResponse {}", response.challenge_id);
                    let _ = self
                        .send(ServerMessage::Ack {
                            proof_id: response.challenge_id,
                            accepted: true,
                            reason: Some("challenge cleared".into()),
                        })
                        .await;
                }
                ClientMessage::Heartbeat { position, .. } => {
                    info!("server got Heartbeat pos={:?}", position);
                }
            }
        }
        info!("NetServer demo loop ended");
    }
}
