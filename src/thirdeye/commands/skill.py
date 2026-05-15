from __future__ import annotations

import shutil
from importlib import resources
from pathlib import Path

import click


@click.group(name="skill", help="Manage the bundled `use-thirdeye` agent skill.")
def skill() -> None:
    pass


@skill.command(name="install")
@click.option(
    "--target",
    type=click.Path(path_type=Path),
    default=Path(".agents/skills/use-thirdeye"),
    show_default=True,
    help="Full destination path for the skill symlink (e.g. .claude/commands/use-thirdeye).",
)
@click.option("--force", is_flag=True, help="Replace an existing entry at the destination.")
def install(target: Path, force: bool) -> None:
    """Symlink the bundled `use-thirdeye` skill into TARGET."""
    source = _bundled_skill_root().resolve()
    # `absolute()` (not `resolve()`) keeps `dest` pointing at the symlink itself
    # rather than following it to its target on subsequent runs.
    dest = target.expanduser().absolute()
    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.is_symlink() and dest.resolve() == source:
        click.echo(f"use-thirdeye skill already installed at {dest}")
        return

    if dest.exists() or dest.is_symlink():
        if not force:
            raise click.ClickException(f"'{dest}' already exists — pass --force to replace")
        if dest.is_symlink() or dest.is_file():
            dest.unlink()
        else:
            shutil.rmtree(dest)

    dest.symlink_to(source, target_is_directory=True)
    click.echo(f"Installed use-thirdeye skill at {dest}")


def _bundled_skill_root() -> Path:
    """Return the absolute path to the bundled use-thirdeye skill directory."""
    root = resources.files("thirdeye").joinpath("skills/use-thirdeye")
    path = Path(str(root))
    if not path.is_dir():
        raise click.ClickException(
            f"bundled skill not found at {path} — reinstall thirdeye"
        )
    return path.resolve()
