from __future__ import annotations

import os
import struct
from pathlib import Path

import zstandard as zstd

_ENTRY_FMT = "<Q"
_ENTRY_SIZE = 8


class IndexWriter:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self._fp = open(path, "ab")

    def append(self, offset: int) -> None:
        self._fp.write(struct.pack(_ENTRY_FMT, offset))
        self._fp.flush()
        os.fsync(self._fp.fileno())

    def close(self) -> None:
        self._fp.close()

    def __enter__(self) -> IndexWriter:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


class IndexReader:
    def __init__(self, path: Path) -> None:
        self.path = path

    def count(self) -> int:
        if not self.path.exists():
            return 0
        return self.path.stat().st_size // _ENTRY_SIZE

    def get(self, seq: int) -> int:
        if seq < 0 or seq >= self.count():
            raise IndexError(f"seq {seq} out of range (count={self.count()})")
        with open(self.path, "rb") as fp:
            fp.seek(seq * _ENTRY_SIZE)
            return struct.unpack(_ENTRY_FMT, fp.read(_ENTRY_SIZE))[0]

    def all_offsets(self) -> list[int]:
        if not self.path.exists():
            return []
        with open(self.path, "rb") as fp:
            data = fp.read()
        return [
            struct.unpack(_ENTRY_FMT, data[i : i + _ENTRY_SIZE])[0]
            for i in range(0, len(data), _ENTRY_SIZE)
        ]


def rebuild_index(events_log: Path, idx_path: Path) -> int:
    """Walk events.alog frame-by-frame; rewrite idx_path. Returns event count."""
    if idx_path.exists():
        idx_path.unlink()
    if not events_log.exists() or events_log.stat().st_size == 0:
        idx_path.touch()
        return 0

    data = events_log.read_bytes()
    offsets: list[int] = []
    pos = 0
    while pos < len(data):
        offsets.append(pos)
        dobj = zstd.ZstdDecompressor().decompressobj()
        try:
            dobj.decompress(data[pos:])
        except zstd.ZstdError:
            offsets.pop()
            break
        remaining = len(dobj.unused_data)
        pos = len(data) - remaining

    with IndexWriter(idx_path) as w:
        for off in offsets:
            w.append(off)
    return len(offsets)
