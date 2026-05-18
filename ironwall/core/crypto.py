"""
ironwall.core.crypto
────────────────────
Shared cryptographic primitives used across all layers.

IMPORTANT:
  - SHA3-256 (Keccak) is used throughout — NOT SHA-256.
  - SHA3-256 is structurally distinct from SHA-2 and immune to length-extension attacks.
  - Do NOT substitute SHA-256 without a security-review PR.
"""

import hashlib
import hmac as _hmac
from typing import Union


def sha3_256_hex(data: Union[bytes, str]) -> str:
    """Return the SHA3-256 hex digest of *data*."""
    if isinstance(data, str):
        data = data.encode()
    return hashlib.sha3_256(data).hexdigest()


def hmac_sign(payload: bytes, key: bytes) -> bytes:
    """
    Produce an HMAC-SHA3-256 tag for *payload* under *key*.

    Used by:
      - ThinClient to authenticate each InputPacket
      - InputMerkleTree to bind leaves to the authenticated session
    """
    return _hmac.new(key, payload, hashlib.sha3_256).digest()


def hmac_verify(payload: bytes, tag: bytes, key: bytes) -> bool:
    """Constant-time HMAC-SHA3-256 verification. Returns False on mismatch."""
    expected = hmac_sign(payload, key)
    return _hmac.compare_digest(expected, tag)


def sha3_256_of_file(path: str) -> str:
    """Stream-hash a file with SHA3-256; suitable for large module binaries."""
    h = hashlib.sha3_256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()
