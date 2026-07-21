//! Lobby handshake — HMAC session tickets (parity with C++)

use crate::wire::{encode_client_hello, encode_server_welcome, sign_frame};
use chrono::Utc;
use hmac::{Hmac, Mac};
use sha2::Sha256;
use std::collections::HashMap;
use tracing::info;
use uuid::Uuid;

type HmacSha256 = Hmac<Sha256>;

#[derive(Debug, Clone)]
pub struct SessionTicket {
    pub ticket_id: String,
    pub player_id: String,
    pub quote_hash: String,
    pub issued_unix: i64,
    pub expires_unix: i64,
    pub hmac_hex: String,
}

#[derive(Debug, Clone)]
pub struct LobbyConfig {
    pub shared_secret: String,
    pub ticket_ttl_sec: i64,
}

impl Default for LobbyConfig {
    fn default() -> Self {
        Self {
            shared_secret: "ironwall-lobby-dev-secret".into(),
            ticket_ttl_sec: 300,
        }
    }
}

pub struct Lobby {
    cfg: LobbyConfig,
    sessions: HashMap<String, SessionTicket>,
}

impl Lobby {
    pub fn new(cfg: LobbyConfig) -> Self {
        Self {
            cfg,
            sessions: HashMap::new(),
        }
    }

    fn mac_hex(&self, msg: &str) -> String {
        let mut mac = HmacSha256::new_from_slice(self.cfg.shared_secret.as_bytes()).expect("hmac");
        mac.update(msg.as_bytes());
        hex::encode(mac.finalize().into_bytes())
    }

    pub fn issue_ticket(&self, player_id: &str, quote_hash: &str) -> SessionTicket {
        let issued = Utc::now().timestamp();
        let mut t = SessionTicket {
            ticket_id: Uuid::new_v4().to_string(),
            player_id: player_id.into(),
            quote_hash: quote_hash.into(),
            issued_unix: issued,
            expires_unix: issued + self.cfg.ticket_ttl_sec,
            hmac_hex: String::new(),
        };
        let msg = format!(
            "{}|{}|{}|{}|{}",
            t.ticket_id, t.player_id, t.quote_hash, t.issued_unix, t.expires_unix
        );
        t.hmac_hex = self.mac_hex(&msg);
        t
    }

    pub fn validate_ticket(&self, t: &SessionTicket) -> bool {
        if Utc::now().timestamp() > t.expires_unix {
            return false;
        }
        let msg = format!(
            "{}|{}|{}|{}|{}",
            t.ticket_id, t.player_id, t.quote_hash, t.issued_unix, t.expires_unix
        );
        self.mac_hex(&msg) == t.hmac_hex
    }

    pub fn open_session(&mut self, t: &SessionTicket) -> Option<String> {
        if !self.validate_ticket(t) {
            return None;
        }
        let sid = Uuid::new_v4().to_string();
        self.sessions.insert(sid.clone(), t.clone());
        info!(session=%sid, player=%t.player_id, "lobby session opened");
        Some(sid)
    }

    pub fn close_session(&mut self, session_id: &str) {
        self.sessions.remove(session_id);
        info!(session=%session_id, "lobby session closed");
    }

    pub fn session_active(&self, session_id: &str) -> bool {
        self.sessions.contains_key(session_id)
    }

    pub fn active_count(&self) -> usize {
        self.sessions.len()
    }

    pub fn make_hello_frame(&self, player_id: &str, version: &str, quote_hash: &str) -> Vec<u8> {
        let frame = encode_client_hello(player_id, version, quote_hash);
        sign_frame(frame, self.cfg.shared_secret.as_bytes())
    }

    pub fn make_welcome_frame(&self, session_id: &str) -> Vec<u8> {
        let frame = encode_server_welcome(session_id);
        sign_frame(frame, self.cfg.shared_secret.as_bytes())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn ticket_and_session() {
        let mut lobby = Lobby::new(LobbyConfig::default());
        let t = lobby.issue_ticket("p1", "quote");
        assert!(lobby.validate_ticket(&t));
        let mut bad = t.clone();
        bad.player_id = "x".into();
        assert!(!lobby.validate_ticket(&bad));
        let sid = lobby.open_session(&t).unwrap();
        assert!(lobby.session_active(&sid));
        assert_eq!(lobby.active_count(), 1);
        lobby.close_session(&sid);
        assert!(!lobby.session_active(&sid));
        let hello = lobby.make_hello_frame("p1", "0.1.0", "quote");
        assert!(hello.len() > 42);
    }
}
