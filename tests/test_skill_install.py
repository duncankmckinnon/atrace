from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from thirdeye.commands.skill import install


@pytest.fixture
def fake_skill(tmp_path: Path) -> Path:
    skill_dir = tmp_path / "bundle" / "use-thirdeye"
    (skill_dir / "references").mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("---\nname: use-thirdeye\n---\n")
    return skill_dir


def _run(fake_skill: Path, args: list[str], cwd: Path) -> object:
    runner = CliRunner()
    with patch("thirdeye.commands.skill._bundled_skill_root", return_value=fake_skill):
        return runner.invoke(install, args, catch_exceptions=False)


def test_install_creates_symlink_at_default(
    fake_skill: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    result = _run(fake_skill, [], tmp_path)
    assert result.exit_code == 0
    dest = tmp_path / ".agents" / "skills" / "use-thirdeye"
    assert dest.is_symlink()
    assert dest.resolve() == fake_skill.resolve()


def test_install_idempotent(
    fake_skill: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _run(fake_skill, [], tmp_path)
    result = _run(fake_skill, [], tmp_path)
    assert result.exit_code == 0
    assert "already installed" in result.output


def test_install_rejects_existing_without_force(
    fake_skill: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    dest = tmp_path / ".agents" / "skills" / "use-thirdeye"
    dest.parent.mkdir(parents=True)
    dest.write_text("not a symlink")
    result = _run(fake_skill, [], tmp_path)
    assert result.exit_code != 0
    assert "already exists" in result.output


def test_install_force_replaces(
    fake_skill: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    dest = tmp_path / ".agents" / "skills" / "use-thirdeye"
    dest.parent.mkdir(parents=True)
    dest.write_text("not a symlink")
    result = _run(fake_skill, ["--force"], tmp_path)
    assert result.exit_code == 0
    assert dest.is_symlink()


def test_install_custom_target_full_path(fake_skill: Path, tmp_path: Path) -> None:
    custom = tmp_path / ".claude" / "commands" / "use-thirdeye"
    result = _run(fake_skill, ["--target", str(custom)], tmp_path)
    assert result.exit_code == 0
    assert custom.is_symlink()
    assert custom.resolve() == fake_skill.resolve()


def test_install_expands_user(
    fake_skill: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    result = _run(fake_skill, ["--target", "~/.claude/skills/use-thirdeye"], tmp_path)
    assert result.exit_code == 0
    assert (tmp_path / ".claude" / "skills" / "use-thirdeye").is_symlink()
