from pathlib import Path


def sessions_root(atrace_home: Path) -> Path:
    return atrace_home / "traces"


def platform_dir(atrace_home: Path, platform: str) -> Path:
    return sessions_root(atrace_home) / platform


def session_dir(atrace_home: Path, platform: str, session_id: str) -> Path:
    return platform_dir(atrace_home, platform) / session_id


def events_path(session_dir_: Path) -> Path:
    return session_dir_ / "events.alog"


def index_path(session_dir_: Path) -> Path:
    return session_dir_ / "events.idx"


def meta_path(session_dir_: Path) -> Path:
    return session_dir_ / "meta.yaml"
