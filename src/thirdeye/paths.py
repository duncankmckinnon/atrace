from pathlib import Path


def sessions_root(thirdeye_home: Path) -> Path:
    return thirdeye_home / "traces"


def platform_dir(thirdeye_home: Path, platform: str) -> Path:
    return sessions_root(thirdeye_home) / platform


def session_dir(thirdeye_home: Path, platform: str, session_id: str) -> Path:
    return platform_dir(thirdeye_home, platform) / session_id


def events_path(session_dir_: Path) -> Path:
    return session_dir_ / "events.alog"


def index_path(session_dir_: Path) -> Path:
    return session_dir_ / "events.idx"


def meta_path(session_dir_: Path) -> Path:
    return session_dir_ / "meta.yaml"


def tags_path(session_dir_: Path) -> Path:
    return session_dir_ / "tags.jsonl"


def usage_jsonl_path(session_dir_: Path) -> Path:
    return session_dir_ / "usage.jsonl"


def usage_state_path(session_dir_: Path) -> Path:
    return session_dir_ / "usage.state.json"


def usage_db_path(thirdeye_home: Path) -> Path:
    return thirdeye_home / "usage.db"


def usage_log_path(thirdeye_home: Path) -> Path:
    return thirdeye_home / "logs" / "usage-errors.jsonl"
