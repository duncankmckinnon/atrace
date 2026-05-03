from __future__ import annotations

import os
import time

# Crockford base32 (excludes I, L, O, U)
_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def new_ulid() -> str:
    """26-char Crockford-base32 ULID: 48 bits ms timestamp + 80 bits randomness."""
    ts_ms = int(time.time() * 1000) & ((1 << 48) - 1)
    rand = int.from_bytes(os.urandom(10), "big")
    val = (ts_ms << 80) | rand
    out = []
    for _ in range(26):
        out.append(_ALPHABET[val & 0x1F])
        val >>= 5
    return "".join(reversed(out))


def resolve_prefix(prefix: str, candidates: list[str]) -> str:
    """Return the unique candidate starting with `prefix`. Raise ValueError if 0 or >1 match."""
    matches = [c for c in candidates if c.startswith(prefix)]
    if not matches:
        raise ValueError(f"no session matching prefix {prefix!r}")
    if len(matches) > 1:
        raise ValueError(f"prefix {prefix!r} ambiguous: {matches!r}")
    return matches[0]
