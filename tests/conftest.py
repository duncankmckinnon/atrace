from pathlib import Path

import pytest

from thirdeye.config import Config
from thirdeye.store import Store


@pytest.fixture
def tmp_store(tmp_path: Path) -> Store:
    return Store(Config(root=tmp_path))


@pytest.fixture
def populated_store(tmp_store: Store) -> Store:
    """Two sessions: one for `claude`, one for `cursor`."""
    with tmp_store.open_session("01J9G7XK4P", platform="claude", cwd="/proj/a") as w:
        w.append("user_message", "hi from claude")
        w.append("assistant_message", "hello user")
    with tmp_store.open_session("02ABCDEF12", platform="cursor", cwd="/proj/b") as w:
        w.append("user_message", "hi from cursor")
    return tmp_store
