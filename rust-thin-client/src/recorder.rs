//! Append-only match/session recorder (TSV) — parity with C++ MatchRecorder

use chrono::Utc;
use std::fs::{File, OpenOptions};
use std::io::{BufRead, BufReader, Write};
use std::path::{Path, PathBuf};
use std::sync::Mutex;
use tracing::info;

#[derive(Debug, Clone)]
pub struct RecordedEvent {
    pub event_type: String,
    pub session_id: String,
    pub player_id: String,
    pub proof_id: String,
    pub quote_hash: String,
    pub combined_hash: String,
    pub from: (f32, f32, f32),
    pub to: (f32, f32, f32),
    pub speed: f32,
    pub delta_t_ms: u32,
    pub unix_ts: i64,
}

pub struct MatchRecorder {
    path: PathBuf,
    file: Mutex<File>,
    count: Mutex<u64>,
}

impl MatchRecorder {
    pub fn new<P: AsRef<Path>>(path: P) -> std::io::Result<Self> {
        let path = path.as_ref().to_path_buf();
        let file = OpenOptions::new().create(true).append(true).open(&path)?;
        info!("Recorder writing to {}", path.display());
        Ok(Self {
            path,
            file: Mutex::new(file),
            count: Mutex::new(0),
        })
    }

    fn write(&self, e: &RecordedEvent) {
        let line = format!(
            "{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\n",
            e.event_type,
            e.session_id,
            e.player_id,
            e.proof_id,
            e.quote_hash,
            e.combined_hash,
            e.from.0,
            e.from.1,
            e.from.2,
            e.to.0,
            e.to.1,
            e.to.2,
            e.speed,
            e.delta_t_ms,
            e.unix_ts
        );
        if let Ok(mut f) = self.file.lock() {
            let _ = f.write_all(line.as_bytes());
            let _ = f.flush();
        }
        if let Ok(mut c) = self.count.lock() {
            *c += 1;
        }
    }

    pub fn record_attest(&self, session_id: &str, player_id: &str, quote_hash: &str) {
        self.write(&RecordedEvent {
            event_type: "attest".into(),
            session_id: session_id.into(),
            player_id: player_id.into(),
            proof_id: String::new(),
            quote_hash: quote_hash.into(),
            combined_hash: String::new(),
            from: (0., 0., 0.),
            to: (0., 0., 0.),
            speed: 0.,
            delta_t_ms: 0,
            unix_ts: Utc::now().timestamp(),
        });
    }

    pub fn record_proof(
        &self,
        session_id: &str,
        player_id: &str,
        proof_id: &str,
        from: (f32, f32, f32),
        to: (f32, f32, f32),
        speed: f32,
        delta_t_ms: u32,
        combined_hash: &str,
    ) {
        self.write(&RecordedEvent {
            event_type: "proof".into(),
            session_id: session_id.into(),
            player_id: player_id.into(),
            proof_id: proof_id.into(),
            quote_hash: String::new(),
            combined_hash: combined_hash.into(),
            from,
            to,
            speed,
            delta_t_ms,
            unix_ts: Utc::now().timestamp(),
        });
    }

    pub fn record_challenge(&self, session_id: &str, challenge_id: &str) {
        self.write(&RecordedEvent {
            event_type: "challenge".into(),
            session_id: session_id.into(),
            player_id: String::new(),
            proof_id: challenge_id.into(),
            quote_hash: String::new(),
            combined_hash: String::new(),
            from: (0., 0., 0.),
            to: (0., 0., 0.),
            speed: 0.,
            delta_t_ms: 0,
            unix_ts: Utc::now().timestamp(),
        });
    }

    pub fn record_heartbeat(&self, session_id: &str, pos: (f32, f32, f32)) {
        self.write(&RecordedEvent {
            event_type: "heartbeat".into(),
            session_id: session_id.into(),
            player_id: String::new(),
            proof_id: String::new(),
            quote_hash: String::new(),
            combined_hash: String::new(),
            from: (0., 0., 0.),
            to: pos,
            speed: 0.,
            delta_t_ms: 0,
            unix_ts: Utc::now().timestamp(),
        });
    }

    pub fn count(&self) -> u64 {
        *self.count.lock().unwrap()
    }

    pub fn path(&self) -> &Path {
        &self.path
    }

    pub fn load<P: AsRef<Path>>(path: P) -> std::io::Result<Vec<RecordedEvent>> {
        let f = File::open(path)?;
        let reader = BufReader::new(f);
        let mut out = Vec::new();
        for line in reader.lines() {
            let line = line?;
            if line.is_empty() {
                continue;
            }
            let p: Vec<&str> = line.split('\t').collect();
            if p.len() < 15 {
                continue;
            }
            out.push(RecordedEvent {
                event_type: p[0].into(),
                session_id: p[1].into(),
                player_id: p[2].into(),
                proof_id: p[3].into(),
                quote_hash: p[4].into(),
                combined_hash: p[5].into(),
                from: (
                    p[6].parse().unwrap_or(0.),
                    p[7].parse().unwrap_or(0.),
                    p[8].parse().unwrap_or(0.),
                ),
                to: (
                    p[9].parse().unwrap_or(0.),
                    p[10].parse().unwrap_or(0.),
                    p[11].parse().unwrap_or(0.),
                ),
                speed: p[12].parse().unwrap_or(0.),
                delta_t_ms: p[13].parse().unwrap_or(0),
                unix_ts: p[14].parse().unwrap_or(0),
            });
        }
        Ok(out)
    }
}
