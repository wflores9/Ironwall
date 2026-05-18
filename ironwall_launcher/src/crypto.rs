//! Cryptographic primitives — must match ironwall/core/crypto.py exactly.
//!
//! CRITICAL: SHA3-256 (Keccak) throughout — NOT SHA-256.
//! The Python layer uses hashlib.sha3_256 and hmac with sha3_256.
//! Any mismatch here will cause TEE verification to fail.

use sha3::{Digest, Sha3_256};
use hmac::{Hmac, Mac};
use std::io::Read;

type HmacSha3_256 = Hmac<Sha3_256>;

/// SHA3-256 hash of arbitrary bytes. Returns lowercase hex string.
/// Matches: `hashlib.sha3_256(data).hexdigest()` in Python.
pub fn sha3_256_hex(data: &[u8]) -> String {
    let mut hasher = Sha3_256::new();
    hasher.update(data);
    hex::encode(hasher.finalize())
}

/// Stream-hash a file with SHA3-256. Handles large DLLs without loading
/// the entire file into memory. Returns lowercase hex string.
///
/// Matches: `sha3_256_of_file()` in ironwall/core/crypto.py
pub fn sha3_256_file(path: &std::path::Path) -> Result<String, std::io::Error> {
    let mut file = std::fs::File::open(path)?;
    let mut hasher = Sha3_256::new();
    let mut buf = vec![0u8; 65_536]; // 64 KiB chunks

    loop {
        let n = file.read(&mut buf)?;
        if n == 0 {
            break;
        }
        hasher.update(&buf[..n]);
    }

    Ok(hex::encode(hasher.finalize()))
}

/// HMAC-SHA3-256 tag over payload under key.
/// Matches: `hmac_sign(payload, key)` in ironwall/core/crypto.py
pub fn hmac_sign(payload: &[u8], key: &[u8]) -> Vec<u8> {
    let mut mac = HmacSha3_256::new_from_slice(key)
        .expect("HMAC accepts any key length");
    mac.update(payload);
    mac.finalize().into_bytes().to_vec()
}

/// Constant-time HMAC-SHA3-256 verification.
/// Matches: `hmac_verify(payload, tag, key)` in ironwall/core/crypto.py
pub fn hmac_verify(payload: &[u8], tag: &[u8], key: &[u8]) -> bool {
    let mut mac = HmacSha3_256::new_from_slice(key)
        .expect("HMAC accepts any key length");
    mac.update(payload);
    mac.verify_slice(tag).is_ok()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sha3_256_known_vector() {
        // Vector generated from Python: hashlib.sha3_256(b"").hexdigest()
        let empty = sha3_256_hex(b"");
        assert_eq!(
            empty,
            "a7ffc6f8bf1ed76651c14756a061d662f580ff4de43b49fa82d80a4b80f8434a"
        );
    }

    #[test]
    fn sha3_256_not_sha2() {
        // SHA3-256("") != SHA-256("")
        let sha3 = sha3_256_hex(b"");
        let sha2 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855";
        assert_ne!(sha3, sha2);
    }

    #[test]
    fn hmac_roundtrip() {
        let key = b"testsessionkey32bytesexactly!!!!";
        let payload = b"player input bytes";
        let tag = hmac_sign(payload, key);
        assert!(hmac_verify(payload, &tag, key));
        assert!(!hmac_verify(b"tampered", &tag, key));
    }

    #[test]
    fn hmac_tag_is_32_bytes() {
        let tag = hmac_sign(b"x", b"key");
        assert_eq!(tag.len(), 32);
    }
}
