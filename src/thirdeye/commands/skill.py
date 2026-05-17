from __future__ import annotations

import shutil
from importlib import resources
from pathlib import Path

import click


@click.group(name="skill", help="Manage the bundled thirdeye agent skills.")
def skill_group() -> None:
    pass


# Backwards-compat alias for any external importers.
skill = skill_group

DEFAULT_TARGET = Path(".agents/skills")


def _bundled_skills_root() -> Path:
    """Return the absolute path to the bundled skills package directory."""
    return Path(str(resources.files("thirdeye").joinpath("skills")))


def _list_bundled_skills() -> list[str]:
    """Return the names of bundled skills (subdirs of skills/ containing SKILL.md)."""
    root = _bundled_skills_root()
    if not root.is_dir():
        return []
    return sorted(p.name for p in root.iterdir() if p.is_dir() and (p / "SKILL.md").is_file())


def _bundled_skill_root(name: str = "use-thirdeye") -> Path:
    """Return the absolute path to a named bundled skill directory."""
    path = _bundled_skills_root() / name
    if not path.is_dir():
        raise click.ClickException(f"bundled skill not found at {path} — reinstall thirdeye")
    return path.resolve()


def _install_one(name: str, dest: Path, *, force: bool) -> str:
    """Symlink the named bundled skill at `dest`. Returns a status message."""
    source = _bundled_skill_root(name).resolve()
    dest = dest.expanduser().absolute()
    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.is_symlink() and dest.resolve() == source:
        return f"{name} skill already installed at {dest}"

    if dest.exists() or dest.is_symlink():
        if not force:
            raise click.ClickException(f"'{dest}' already exists — pass --force to replace")
        if dest.is_symlink() or dest.is_file():
            dest.unlink()
        else:
            shutil.rmtree(dest)

    dest.symlink_to(source, target_is_directory=True)
    return f"Installed {name} skill at {dest}"


@skill_group.command(name="install")
@click.argument(
    "target",
    type=click.Path(path_type=Path),
    required=False,
    default=None,
)
@click.option(
    "--target",
    "target_opt",
    type=click.Path(path_type=Path),
    default=None,
    help="Alias for the positional TARGET argument.",
)
@click.option(
    "--only",
    "only",
    multiple=True,
    help="Install only the named skill (repeatable). Defaults to all bundled skills.",
)
@click.option("--force", is_flag=True, help="Replace an existing entry at the destination.")
def install(
    target: Path | None,
    target_opt: Path | None,
    only: tuple[str, ...],
    force: bool,
) -> None:
    """Symlink bundled thirdeye skills into TARGET.

    By default, installs every bundled skill under TARGET (e.g.
    `<TARGET>/use-thirdeye`). With a single `--only NAME`, TARGET may also be
    a full destination path whose basename matches NAME. Defaults TARGET to
    `.agents/skills`.
    """
    if target is not None and target_opt is not None:
        raise click.ClickException(
            "Pass TARGET as a positional argument or via --target, not both."
        )
    chosen = target if target is not None else target_opt
    if chosen is None:
        chosen = DEFAULT_TARGET

    bundled = _list_bundled_skills()
    if only:
        unknown = [n for n in only if n not in bundled]
        if unknown:
            raise click.ClickException(
                f"unknown skill(s): {', '.join(unknown)}; "
                f"available: {', '.join(bundled) if bundled else '(none)'}"
            )
        # Preserve user-given order but de-dupe.
        names = list(dict.fromkeys(only))
    elif chosen.name in bundled:
        # Backwards-compat: TARGET basename matches a bundled skill name →
        # treat as a single-skill install at the full path.
        names = [chosen.name]
    else:
        names = bundled

    if not names:
        raise click.ClickException("no bundled skills found")

    # Basename-match shortcut: only honored for a single-skill install.
    if len(names) == 1 and chosen.name == names[0]:
        destinations = [(names[0], chosen)]
    else:
        destinations = [(n, chosen / n) for n in names]

    for skill_name, dest in destinations:
        msg = _install_one(skill_name, dest, force=force)
        click.echo(msg)


@skill_group.command(name="list", help="List the names of bundled thirdeye skills.")
def list_cmd() -> None:
    for name in _list_bundled_skills():
        click.echo(name)
