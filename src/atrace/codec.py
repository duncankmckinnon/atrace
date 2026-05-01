from __future__ import annotations

from typing import Any

import msgpack
import zstandard as zstd

_compressor = zstd.ZstdCompressor()
_decompressor = zstd.ZstdDecompressor()


def encode_event(event: dict[str, Any]) -> bytes:
    packed = msgpack.packb(event, use_bin_type=True)
    return _compressor.compress(packed)


def decode_event(frame: bytes) -> dict[str, Any]:
    packed = _decompressor.decompress(frame)
    return msgpack.unpackb(packed, raw=False)
