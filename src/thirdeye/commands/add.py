from __future__ import annotations

import click

from thirdeye.platforms.base import Platform
from thirdeye.platforms.claude.install import ClaudePlatform

PLATFORMS: dict[str, type[Platform]] = {
    "claude": ClaudePlatform,
}


def _platform_options(fn):
    fn = click.option("--claude", "platform_flag", flag_value="claude", help="Claude Code.")(fn)
    return fn


def _resolve_platform(platform_flag: str | None) -> Platform:
    if not platform_flag:
        raise click.UsageError("Pick a platform: --claude")
    return PLATFORMS[platform_flag]()


@click.command(help="Install tracing hooks for an agentic platform.")
@_platform_options
def add(platform_flag: str | None) -> None:
    platform = _resolve_platform(platform_flag)
    platform.install()
    click.echo(f"Installed tracing for {platform.display_name}")


@click.command(help="Remove tracing hooks for an agentic platform.")
@_platform_options
def remove(platform_flag: str | None) -> None:
    platform = _resolve_platform(platform_flag)
    platform.uninstall()
    click.echo(f"Removed tracing for {platform.display_name}")
