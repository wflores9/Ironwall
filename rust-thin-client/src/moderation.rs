//! Rate-limit + ban list (parity with C++ ModerationEngine)

use std::collections::{HashMap, VecDeque};
use std::time::{Duration, Instant};
use tracing::{info, warn};

#[derive(Debug, Clone)]
pub struct RateLimitConfig {
    pub max_events: usize,
    pub window: Duration,
    pub ban_after_violations: usize,
    pub ban_duration: Duration,
}

impl Default for RateLimitConfig {
    fn default() -> Self {
        Self {
            max_events: 30,
            window: Duration::from_secs(10),
            ban_after_violations: 3,
            ban_duration: Duration::from_secs(300),
        }
    }
}

pub struct ModerationEngine {
    cfg: RateLimitConfig,
    windows: HashMap<String, VecDeque<Instant>>,
    strikes: HashMap<String, usize>,
    bans: HashMap<String, Instant>, // until
    reasons: HashMap<String, String>,
}

impl ModerationEngine {
    pub fn new(cfg: RateLimitConfig) -> Self {
        Self {
            cfg,
            windows: HashMap::new(),
            strikes: HashMap::new(),
            bans: HashMap::new(),
            reasons: HashMap::new(),
        }
    }

    pub fn allow(&mut self, player_id: &str, event_type: &str) -> bool {
        let now = Instant::now();

        if let Some(until) = self.bans.get(player_id) {
            if now < *until {
                warn!(player=%player_id, reason=%self.reasons.get(player_id).map(|s| s.as_str()).unwrap_or(""), "DENY banned");
                return false;
            }
            self.bans.remove(player_id);
            self.reasons.remove(player_id);
        }

        let q = self.windows.entry(player_id.to_string()).or_default();
        while q.front().map(|t| now.duration_since(*t) > self.cfg.window).unwrap_or(false) {
            q.pop_front();
        }
        q.push_back(now);

        if q.len() > self.cfg.max_events {
            let s = self.strikes.entry(player_id.to_string()).or_insert(0);
            *s += 1;
            warn!(player=%player_id, event=%event_type, count=q.len(), strike=*s, "RATE LIMIT");
            if *s >= self.cfg.ban_after_violations {
                self.bans.insert(player_id.to_string(), now + self.cfg.ban_duration);
                self.reasons.insert(player_id.to_string(), "rate_limit".into());
                warn!(player=%player_id, secs=self.cfg.ban_duration.as_secs(), "BAN");
            }
            return false;
        }
        true
    }

    pub fn ban(&mut self, player_id: &str, reason: &str) {
        self.bans.insert(player_id.to_string(), Instant::now() + self.cfg.ban_duration);
        self.reasons.insert(player_id.to_string(), reason.into());
        info!(player=%player_id, reason=%reason, "MANUAL BAN");
    }

    pub fn unban(&mut self, player_id: &str) {
        self.bans.remove(player_id);
        self.reasons.remove(player_id);
        self.strikes.remove(player_id);
        self.windows.remove(player_id);
    }

    pub fn is_banned(&self, player_id: &str) -> bool {
        self.bans.get(player_id).map(|u| Instant::now() < *u).unwrap_or(false)
    }

    pub fn strike_count(&self, player_id: &str) -> usize {
        self.strikes.get(player_id).copied().unwrap_or(0)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rate_limit_and_ban() {
        let cfg = RateLimitConfig {
            max_events: 3,
            window: Duration::from_secs(60),
            ban_after_violations: 2,
            ban_duration: Duration::from_secs(60),
        };
        let mut m = ModerationEngine::new(cfg);
        assert!(m.allow("a", "p"));
        assert!(m.allow("a", "p"));
        assert!(m.allow("a", "p"));
        assert!(!m.allow("a", "p"));
        assert!(!m.allow("a", "p"));
        assert!(m.is_banned("a"));
        m.unban("a");
        assert!(!m.is_banned("a"));
        assert!(m.allow("a", "p"));
    }
}
