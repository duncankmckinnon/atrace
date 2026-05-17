from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from thirdeye.commands.skill import _list_bundled_skills, install, skill_group


@pytest.fixture
def fake_skill(tmp_path: Path) -> Path:
    skill_dir = tmp_path / "bundle" / "use-thirdeye"
    (skill_dir / "references").mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("---\nname: use-thirdeye\n---\n")
    return skill_dir


def _run(fake_skill: Path, args: list[str]) -> object:
    runner = CliRunner()
    with patch("thirdeye.commands.skill._bundled_skill_root", return_value=fake_skill):
        return runner.invoke(install, args, catch_exceptions=False)


def test_install_creates_symlink_at_default(
    fake_skill: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    result = _run(fake_skill, [])
    assert result.exit_code == 0
    dest = tmp_path / ".agents" / "skills" / "use-thirdeye"
    assert dest.is_symlink()
    assert dest.resolve() == fake_skill.resolve()


def test_install_idempotent(
    fake_skill: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _run(fake_skill, [])
    result = _run(fake_skill, [])
    assert result.exit_code == 0
    assert "already installed" in result.output


def test_install_rejects_existing_without_force(
    fake_skill: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    dest = tmp_path / ".agents" / "skills" / "use-thirdeye"
    dest.parent.mkdir(parents=True)
    dest.write_text("not a symlink")
    result = _run(fake_skill, [])
    assert result.exit_code != 0
    assert "already exists" in result.output


def test_install_force_replaces(
    fake_skill: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    dest = tmp_path / ".agents" / "skills" / "use-thirdeye"
    dest.parent.mkdir(parents=True)
    dest.write_text("not a symlink")
    result = _run(fake_skill, ["--force"])
    assert result.exit_code == 0
    assert dest.is_symlink()


def test_install_custom_target_full_path(fake_skill: Path, tmp_path: Path) -> None:
    custom = tmp_path / ".claude" / "commands" / "use-thirdeye"
    result = _run(fake_skill, ["--target", str(custom)])
    assert result.exit_code == 0
    assert custom.is_symlink()
    assert custom.resolve() == fake_skill.resolve()


def test_install_expands_user(
    fake_skill: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    result = _run(fake_skill, ["--target", "~/.claude/skills/use-thirdeye"])
    assert result.exit_code == 0
    assert (tmp_path / ".claude" / "skills" / "use-thirdeye").is_symlink()


def test_install_positional_argument(fake_skill: Path, tmp_path: Path) -> None:
    custom = tmp_path / ".claude" / "skills" / "use-thirdeye"
    result = _run(fake_skill, [str(custom)])
    assert result.exit_code == 0
    assert custom.is_symlink()


def test_install_appends_skill_name_when_missing(fake_skill: Path, tmp_path: Path) -> None:
    # Passing a parent dir auto-appends `use-thirdeye`.
    parent = tmp_path / ".claude" / "skills"
    result = _run(fake_skill, [str(parent)])
    assert result.exit_code == 0
    assert (parent / "use-thirdeye").is_symlink()


def test_install_rejects_both_positional_and_option(fake_skill: Path, tmp_path: Path) -> None:
    a = tmp_path / "a"
    b = tmp_path / "b"
    result = _run(fake_skill, [str(a), "--target", str(b)])
    assert result.exit_code != 0
    assert "not both" in result.output


def test_skill_list_command() -> None:
    result = CliRunner().invoke(skill_group, ["list"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "use-thirdeye" in result.output


def test_install_all_bundled_skills_by_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    dest_root = tmp_path / "skills"
    result = CliRunner().invoke(skill_group, ["install", str(dest_root)], catch_exceptions=False)
    assert result.exit_code == 0
    bundled = _list_bundled_skills()
    assert bundled, "expected at least one bundled skill"
    for name in bundled:
        entry = dest_root / name
        assert entry.is_symlink() or entry.is_dir()


def test_install_only_single_skill(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        skill_group,
        ["install", str(tmp_path / "skills"), "--only", "use-thirdeye"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert (tmp_path / "skills" / "use-thirdeye").exists()


def test_install_unknown_only_errors(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        skill_group,
        ["install", str(tmp_path / "skills"), "--only", "nonexistent-skill"],
    )
    assert result.exit_code != 0
    assert "unknown skill" in result.output


def test_install_basename_match_only_with_single_skill(tmp_path: Path) -> None:
    """When TARGET basename matches the single selected skill, use as full path."""
    dest = tmp_path / "use-thirdeye"
    result = CliRunner().invoke(
        skill_group,
        ["install", str(dest), "--only", "use-thirdeye"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert dest.exists()
