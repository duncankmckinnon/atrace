import json
import os
import subprocess
import sys
from pathlib import Path


def test_full_round_trip(tmp_path: Path):
    env = os.environ.copy()
    env["ATRACE_HOME"] = str(tmp_path)
    cmd_prefix = [sys.executable, "-m", "atrace"]

    subprocess.run(
        cmd_prefix + ["ingest", "--platform", "claude", "--session-id", "01J9G7XK4P", "--cwd", "/p"],
        input=(json.dumps({"t": "user_message", "data": "hello world"}) + "\n").encode(),
        env=env,
        check=True,
    )
    subprocess.run(
        cmd_prefix + ["ingest", "--platform", "cursor", "--session-id", "02ABCDEF12", "--cwd", "/q"],
        input=(json.dumps({"t": "user_message", "data": "different msg"}) + "\n").encode(),
        env=env,
        check=True,
    )

    out = subprocess.check_output(cmd_prefix + ["list"], env=env, text=True)
    assert "01J9G7XK4P" in out
    assert "02ABCDEF12" in out

    out = subprocess.check_output(cmd_prefix + ["events", "01J9"], env=env, text=True)
    assert "0 user_message hello world" in out

    out = subprocess.check_output(cmd_prefix + ["event", "01J9", "0"], env=env, text=True)
    assert "hello world" in out

    out = subprocess.check_output(cmd_prefix + ["search", "different"], env=env, text=True)
    assert "02ABCDEF12" in out

    out = subprocess.check_output(cmd_prefix + ["stats"], env=env, text=True)
    obj = json.loads(out.strip())
    assert obj["session_count"] == 2
    assert obj["event_count"] == 2
