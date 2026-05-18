//! DLL / shared-library scanner.
//!
//! Recursively walks a game directory, finds all .dll (Windows) or .so (Linux)
//! files, hashes each with SHA3-256, and returns a ModuleManifest ready to
//! submit to the TEE attestation broker.
//!
//! Performance: files are hashed concurrently via Tokio's blocking thread pool.
//! A 10 GB game directory with ~200 DLLs typically scans in < 2 seconds on
//! an NVMe drive.
//!
//! This is the core of issue #89 — the Rust rewrite for sub-1ms per-file
//! hashing latency.

use crate::crypto::sha3_256_file;
use crate::error::LauncherError;
use crate::manifest::ModuleEntry;
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};
use tokio::task::JoinSet;
use tracing::{debug, info, warn};
use walkdir::WalkDir;

/// Extensions treated as signable modules.
const MODULE_EXTENSIONS: &[&str] = &[
    "dll",  // Windows
    "so",   // Linux
    "dylib", // macOS
];

/// Scanner configuration.
#[derive(Debug, Clone)]
pub struct ScanConfig {
    /// Root directory to scan.
    pub game_dir: PathBuf,

    /// Maximum file size to hash (bytes). Files larger than this are flagged
    /// but not hashed — prevents DoS on corrupted/huge files.
    /// Default: 500 MB.
    pub max_file_size: u64,

    /// If true, recurse into subdirectories. Default: true.
    pub recursive: bool,

    /// Filenames to skip (e.g. known-clean system DLLs that aren't game code).
    /// These are still recorded in the manifest but marked as skip=true.
    pub skip_list: Vec<String>,

    /// Known signature records from the ModuleSigner.
    /// Map: filename → expected SHA3-256 hash.
    /// Used to set ModuleEntry.has_signature.
    pub known_hashes: std::collections::HashMap<String, String>,
}

impl ScanConfig {
    pub fn new(game_dir: impl Into<PathBuf>) -> Self {
        Self {
            game_dir: game_dir.into(),
            max_file_size: 500 * 1024 * 1024, // 500 MB
            recursive: true,
            skip_list: Vec::new(),
            known_hashes: std::collections::HashMap::new(),
        }
    }

    pub fn with_known_hashes(
        mut self,
        hashes: std::collections::HashMap<String, String>,
    ) -> Self {
        self.known_hashes = hashes;
        self
    }

    pub fn with_skip_list(mut self, skip: Vec<String>) -> Self {
        self.skip_list = skip;
        self
    }
}

/// Scans a game directory and produces a list of ModuleEntry records.
pub struct DllScanner {
    config: ScanConfig,
}

impl DllScanner {
    pub fn new(config: ScanConfig) -> Self {
        Self { config }
    }

    /// Collect all module paths from the game directory.
    pub fn collect_paths(&self) -> Result<Vec<PathBuf>, LauncherError> {
        let walker = if self.config.recursive {
            WalkDir::new(&self.config.game_dir)
        } else {
            WalkDir::new(&self.config.game_dir).max_depth(1)
        };

        let paths: Vec<PathBuf> = walker
            .into_iter()
            .filter_map(|entry| entry.ok())
            .filter(|entry| entry.file_type().is_file())
            .filter(|entry| {
                entry
                    .path()
                    .extension()
                    .and_then(|e| e.to_str())
                    .map(|ext| MODULE_EXTENSIONS.contains(&ext.to_lowercase().as_str()))
                    .unwrap_or(false)
            })
            .map(|e| e.path().to_path_buf())
            .collect();

        info!(
            "Found {} module files in {}",
            paths.len(),
            self.config.game_dir.display()
        );
        Ok(paths)
    }

    /// Hash a single module file synchronously (for use in blocking context).
    fn hash_module(
        path: &Path,
        max_size: u64,
        known_hashes: &std::collections::HashMap<String, String>,
        skip_list: &[String],
    ) -> Result<ModuleEntry, LauncherError> {
        let filename = path
            .file_name()
            .and_then(|n| n.to_str())
            .unwrap_or("unknown")
            .to_string();

        let meta = std::fs::metadata(path)?;
        let size_bytes = meta.len();
        let mtime = meta
            .modified()
            .unwrap_or(SystemTime::UNIX_EPOCH)
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs();

        // Check skip list
        if skip_list.contains(&filename) {
            debug!("Skipping {} (on skip list)", filename);
            return Ok(ModuleEntry {
                path: path.to_string_lossy().to_string(),
                filename,
                size_bytes,
                sha3_256: "SKIPPED".to_string(),
                mtime,
                has_signature: false,
            });
        }

        // Size guard
        if size_bytes > max_size {
            warn!(
                "Module {} exceeds max size ({} > {}), skipping hash",
                filename, size_bytes, max_size
            );
            return Ok(ModuleEntry {
                path: path.to_string_lossy().to_string(),
                filename,
                size_bytes,
                sha3_256: "TOO_LARGE".to_string(),
                mtime,
                has_signature: false,
            });
        }

        // SHA3-256 hash
        let sha3_256 = sha3_256_file(path)?;
        debug!("Hashed {} → {}…", filename, &sha3_256[..16]);

        // Check against known signature records
        let has_signature = known_hashes
            .get(&filename)
            .map(|expected| expected == &sha3_256)
            .unwrap_or(false);

        if !has_signature && known_hashes.contains_key(&filename) {
            warn!(
                "Hash mismatch for {}: expected {}…, got {}…",
                filename,
                &known_hashes[&filename][..16],
                &sha3_256[..16]
            );
        }

        Ok(ModuleEntry {
            path: path.to_string_lossy().to_string(),
            filename,
            size_bytes,
            sha3_256,
            mtime,
            has_signature,
        })
    }

    /// Scan all modules concurrently and return their entries.
    /// Uses Tokio's blocking thread pool — safe to call from async context.
    pub async fn scan(&self) -> Result<Vec<ModuleEntry>, LauncherError> {
        let paths = self.collect_paths()?;
        let total = paths.len();
        let max_size = self.config.max_file_size;
        let known_hashes = self.config.known_hashes.clone();
        let skip_list = self.config.skip_list.clone();

        let mut join_set = JoinSet::new();

        for path in paths {
            let kh = known_hashes.clone();
            let sl = skip_list.clone();
            join_set.spawn_blocking(move || {
                Self::hash_module(&path, max_size, &kh, &sl)
            });
        }

        let mut entries = Vec::with_capacity(total);
        while let Some(result) = join_set.join_next().await {
            match result {
                Ok(Ok(entry)) => entries.push(entry),
                Ok(Err(e)) => return Err(e),
                Err(e) => {
                    return Err(LauncherError::Scan(format!("Task panicked: {e}")))
                }
            }
        }

        // Sort by path for deterministic manifest hash
        entries.sort_by(|a, b| a.path.cmp(&b.path));

        info!(
            "Scan complete: {} modules, {:.1} MB total",
            entries.len(),
            entries.iter().map(|e| e.size_bytes).sum::<u64>() as f64 / 1_048_576.0
        );

        Ok(entries)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;
    use std::io::Write;

    fn make_fake_dll(dir: &Path, name: &str, content: &[u8]) -> PathBuf {
        let path = dir.join(name);
        let mut f = std::fs::File::create(&path).unwrap();
        f.write_all(content).unwrap();
        path
    }

    #[tokio::test]
    async fn scan_finds_dlls() {
        let tmp = TempDir::new().unwrap();
        make_fake_dll(tmp.path(), "test.dll", b"fake dll content");
        make_fake_dll(tmp.path(), "other.exe", b"not a dll");

        let config = ScanConfig::new(tmp.path());
        let scanner = DllScanner::new(config);
        let entries = scanner.scan().await.unwrap();

        assert_eq!(entries.len(), 1);
        assert_eq!(entries[0].filename, "test.dll");
    }

    #[tokio::test]
    async fn hash_matches_known_vector() {
        let tmp = TempDir::new().unwrap();
        let path = make_fake_dll(tmp.path(), "module.dll", b"ironwall test");

        let config = ScanConfig::new(tmp.path());
        let scanner = DllScanner::new(config);
        let entries = scanner.scan().await.unwrap();

        // Verify hash matches our crypto module
        let expected = crate::crypto::sha3_256_hex(b"ironwall test");
        assert_eq!(entries[0].sha3_256, expected);
    }

    #[tokio::test]
    async fn known_hash_sets_has_signature() {
        let tmp = TempDir::new().unwrap();
        make_fake_dll(tmp.path(), "signed.dll", b"signed content");

        let expected_hash = crate::crypto::sha3_256_hex(b"signed content");
        let mut hashes = std::collections::HashMap::new();
        hashes.insert("signed.dll".to_string(), expected_hash);

        let config = ScanConfig::new(tmp.path()).with_known_hashes(hashes);
        let scanner = DllScanner::new(config);
        let entries = scanner.scan().await.unwrap();

        assert!(entries[0].has_signature);
    }

    #[tokio::test]
    async fn tampered_dll_has_signature_false() {
        let tmp = TempDir::new().unwrap();
        make_fake_dll(tmp.path(), "tampered.dll", b"tampered content");

        let mut hashes = std::collections::HashMap::new();
        hashes.insert("tampered.dll".to_string(), "a".repeat(64)); // wrong hash

        let config = ScanConfig::new(tmp.path()).with_known_hashes(hashes);
        let scanner = DllScanner::new(config);
        let entries = scanner.scan().await.unwrap();

        assert!(!entries[0].has_signature);
    }
}
