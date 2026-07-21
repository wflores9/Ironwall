//! Matchmaker — enqueue tickets, form matches (parity with C++)

use crate::lobby::{Lobby, LobbyConfig, SessionTicket};
use crate::moderation::{ModerationEngine, RateLimitConfig};
use crate::ban_store::BanStore;
use std::collections::{HashMap, VecDeque};
use tracing::info;
use uuid::Uuid;
use chrono::Utc;

#[derive(Debug, Clone)]
pub struct Match {
    pub match_id: String,
    pub players: Vec<String>,
    pub created_unix: i64,
}

#[derive(Debug, Clone)]
pub struct MatchmakerConfig {
    pub players_per_match: usize,
    pub lobby: LobbyConfig,
    pub rate: RateLimitConfig,
    pub ban_path: String,
}

impl Default for MatchmakerConfig {
    fn default() -> Self {
        Self {
            players_per_match: 2,
            lobby: LobbyConfig::default(),
            rate: RateLimitConfig::default(),
            ban_path: "ironwall_bans.jsonl".into(),
        }
    }
}

pub struct Matchmaker {
    cfg: MatchmakerConfig,
    lobby: Lobby,
    mod_eng: ModerationEngine,
    bans: BanStore,
    queue: VecDeque<String>,
    matches: HashMap<String, Match>,
}

impl Matchmaker {
    pub fn new(cfg: MatchmakerConfig) -> Self {
        let mut mod_eng = ModerationEngine::new(cfg.rate.clone());
        let bans = BanStore::new(&cfg.ban_path);
        bans.load_into(&mut mod_eng);
        Self {
            lobby: Lobby::new(cfg.lobby.clone()),
            mod_eng,
            bans,
            queue: VecDeque::new(),
            matches: HashMap::new(),
            cfg,
        }
    }

    pub fn lobby_mut(&mut self) -> &mut Lobby {
        &mut self.lobby
    }

    pub fn enqueue(&mut self, ticket: &SessionTicket) -> Option<String> {
        if !self.lobby.validate_ticket(ticket) {
            return None;
        }
        if !self.mod_eng.allow(&ticket.player_id, "enqueue") {
            return None;
        }
        let sid = self.lobby.open_session(ticket)?;
        self.queue.push_back(sid.clone());
        info!(session=%sid, queue=self.queue.len(), "mm enqueued");
        Some(sid)
    }

    pub fn tick(&mut self) -> Vec<Match> {
        let mut created = Vec::new();
        while self.queue.len() >= self.cfg.players_per_match {
            let mut players = Vec::new();
            for _ in 0..self.cfg.players_per_match {
                if let Some(s) = self.queue.pop_front() {
                    players.push(s);
                }
            }
            let m = Match {
                match_id: Uuid::new_v4().to_string(),
                players,
                created_unix: Utc::now().timestamp(),
            };
            info!(match_id=%m.match_id, n=m.players.len(), "mm match formed");
            self.matches.insert(m.match_id.clone(), m.clone());
            created.push(m);
        }
        created
    }

    pub fn queue_size(&self) -> usize {
        self.queue.len()
    }

    pub fn active_matches(&self) -> usize {
        self.matches.len()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn pairs_two_players() {
        let mut mm = Matchmaker::new(MatchmakerConfig::default());
        let t1 = mm.lobby_mut().issue_ticket("a", "q");
        let t2 = mm.lobby_mut().issue_ticket("b", "q");
        assert!(mm.enqueue(&t1).is_some());
        assert!(mm.tick().is_empty());
        assert!(mm.enqueue(&t2).is_some());
        let m = mm.tick();
        assert_eq!(m.len(), 1);
        assert_eq!(m[0].players.len(), 2);
    }
}
