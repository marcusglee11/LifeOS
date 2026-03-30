"""
Minimal ULID generator.

Generates 26-character Crockford base32 ULIDs:
  - 48-bit millisecond timestamp (10 chars)
  - 80-bit cryptographic random (16 chars)

Alphabet: 0123456789ABCDEFGHJKMNPQRSTVWXYZ (no I, L, O, U)
Pattern: ^[0-9A-HJKMNP-TV-Z]{26}$
"""

from __future__ import annotations

import os
import time

# Crockford base32 alphabet (no I, L, O, U)
_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_ENCODING = {i: c for i, c in enumerate(_ALPHABET)}


def _encode(n: int, length: int) -> str:
    """Encode integer n as Crockford base32 string of given length."""
    chars = []
    for _ in range(length):
        chars.append(_ENCODING[n & 0x1F])
        n >>= 5
    return "".join(reversed(chars))


def generate_ulid() -> str:
    """
    Generate a new ULID.

    Returns:
        26-character Crockford base32 string matching ^[0-9A-HJKMNP-TV-Z]{26}$
    """
    ts_ms = int(time.time() * 1000)
    rand_bytes = os.urandom(10)  # 80 bits
    rand_int = int.from_bytes(rand_bytes, "big")

    timestamp_part = _encode(ts_ms, 10)
    random_part = _encode(rand_int, 16)

    return timestamp_part + random_part
