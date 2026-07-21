//! IWAL binary wire protocol (parity with C++ wire.hpp)

pub const MAGIC: u32 = 0x4C41_5749; // 'IWAL' LE
pub const VERSION: u8 = 1;

#[repr(u8)]
#[derive(Debug, Clone, Copy)]
pub enum MsgType {
    Hello = 1,
    MovementProof = 2,
    ChallengeResponse = 3,
    Heartbeat = 4,
    Welcome = 10,
    Challenge = 11,
    Ack = 12,
    Kick = 13,
}

fn append_u32(buf: &mut Vec<u8>, v: u32) {
    buf.extend_from_slice(&v.to_le_bytes());
}
fn append_str(buf: &mut Vec<u8>, s: &str) {
    append_u32(buf, s.len() as u32);
    buf.extend_from_slice(s.as_bytes());
}

pub fn encode_client_hello(player_id: &str, version: &str, quote_hash: &str) -> Vec<u8> {
    let mut payload = Vec::new();
    append_str(&mut payload, player_id);
    append_str(&mut payload, version);
    append_str(&mut payload, quote_hash);

    let mut frame = Vec::new();
    append_u32(&mut frame, MAGIC);
    frame.push(VERSION);
    frame.push(MsgType::Hello as u8);
    append_u32(&mut frame, payload.len() as u32);
    frame.extend_from_slice(&payload);
    frame
}

pub fn encode_server_welcome(session_id: &str) -> Vec<u8> {
    let mut payload = Vec::new();
    append_str(&mut payload, session_id);
    let mut frame = Vec::new();
    append_u32(&mut frame, MAGIC);
    frame.push(VERSION);
    frame.push(MsgType::Welcome as u8);
    append_u32(&mut frame, payload.len() as u32);
    frame.extend_from_slice(&payload);
    frame
}

/// HMAC-SHA256 over ver||type||payload, appended as 32 bytes
pub fn sign_frame(mut frame: Vec<u8>, secret: &[u8]) -> Vec<u8> {
    if frame.len() < 10 {
        return frame;
    }
    let mut msg = Vec::with_capacity(2 + frame.len());
    msg.push(frame[4]);
    msg.push(frame[5]);
    msg.extend_from_slice(&frame[10..]);
    use hmac::{Hmac, Mac};
    use sha2::Sha256;
    type HmacSha256 = Hmac<Sha256>;
    let mut mac = HmacSha256::new_from_slice(secret).expect("hmac key");
    mac.update(&msg);
    let result = mac.finalize().into_bytes();
    frame.extend_from_slice(&result);
    frame
}

pub fn verify_frame(data: &[u8], secret: &[u8]) -> Option<Vec<u8>> {
    if data.len() < 10 + 32 {
        return None;
    }
    let body_len = data.len() - 32;
    let plen = u32::from_le_bytes(data[6..10].try_into().ok()?) as usize;
    if 10 + plen + 32 != data.len() {
        return None;
    }
    let mut msg = Vec::new();
    msg.push(data[4]);
    msg.push(data[5]);
    msg.extend_from_slice(&data[10..10 + plen]);

    use hmac::{Hmac, Mac};
    use sha2::Sha256;
    type HmacSha256 = Hmac<Sha256>;
    let mut mac = HmacSha256::new_from_slice(secret).ok()?;
    mac.update(&msg);
    mac.verify_slice(&data[body_len..]).ok()?;
    Some(data[..body_len].to_vec())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sign_verify_roundtrip() {
        let frame = encode_client_hello("p1", "0.1.0", "abc");
        let signed = sign_frame(frame.clone(), b"secret");
        assert_eq!(signed.len(), frame.len() + 32);
        assert!(verify_frame(&signed, b"secret").is_some());
        assert!(verify_frame(&signed, b"wrong").is_none());
        let mut bad = signed.clone();
        bad[12] ^= 0xff;
        assert!(verify_frame(&bad, b"secret").is_none());
    }
}
