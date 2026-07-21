//! Persistent ban list (JSONL) — parity with C++ BanStore

use crate::moderation::ModerationEngine;
use chrono::Utc;
use std::fs::{File, OpenOptions};
use std::io::{BufRead, BufReader, Write};
use std::path::{Path, PathBuf};
use tracing::info;

pub struct BanStore {
    path: PathBuf,
}

impl BanStore {
    pub fn new<P: AsRef<Path>>(path: P) -> Self {
        Self {
            path: path.as_ref().to_path_buf(),
        }
    }

    pub fn path(&self) -> &Path {
        &self.path
    }

    fn append(&self, line: &str) {
        if let Ok(mut f) = OpenOptions::new().create(true).append(true).open(&self.path) {
            let _ = writeln!(f, "{line}");
        }
    }

    pub fn save_ban(&self, player: &str, reason: &str, duration_secs: i64) {
        let until = Utc::now().timestamp() + duration_secs;
        self.append(&format!(
            r#"{{"op":"ban","player":"{player}","reason":"{reason}","until_unix":{until}}}"#
        ));
    }

    pub fn save_unban(&self, player: &str) {
        self.append(&format!(r#"{{"op":"unban","player":"{player}"}}"#));
    }

    pub fn load_into(&self, mod_eng: &mut ModerationEngine) {
        let f = match File::open(&self.path) {
            Ok(f) => f,
            Err(_) => {
                info!("ban_store: no file {} (empty)", self.path.display());
                return;
            }
        };
        let mut loaded = 0u32;
        for line in BufReader::new(f).lines().flatten() {
            if line.contains(r#""op":"ban""#) {
                let player = extract(&line, r#""player":""#).unwrap_or_default();
                let reason = extract(&line, r#""reason":""#).unwrap_or_else(|| "persisted".into());
                let until: i64 = line
                    .split(r#""until_unix":"#)
                    .nth(1)
                    .and_then(|s| s.split(|c: char| !c.is_ascii_digit() && c != '-').next())
                    .and_then(|s| s.parse().ok())
                    .unwrap_or(0);
                if until > Utc::now().timestamp() && !player.is_empty() {
                    mod_eng.ban(&player, &format!("{reason} (persisted)"));
                    loaded += 1;
                }
            } else if line.contains(r#""op":"unban""#) {
                if let Some(player) = extract(&line, r#""player":""#) {
                    mod_eng.unban(&player);
                }
            }
        }
        info!("ban_store: loaded {loaded} active bans from {}", self.path.display());
    }
}

fn extract(line: &str, key: &str) -> Option<String> {
    let i = line.find(key)? + key.len();
    let rest = &line[i..];
    let end = rest.find('"')?;
    Some(rest[..end].to_string())
}
