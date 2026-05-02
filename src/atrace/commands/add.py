from __future__ import annotations

import click

from atrace.platforms.base import Platform
from atrace.platforms.claude.install import ClaudePlatform

PLATFORMS: dict[str, type[Platform]] = {
    "claude": ClaudePlatform,
}


@click.command(help="Install (or remove) tracing hooks for an agentic platform.")
@click.option("--claude", "platform_flag", flag_value="claude", help="Claude Code.")
@click.option("--remove", is_flag=True, help="Uninstall instead of install.")
def add(platform_flag: str | None, remove: bool) -> None:
    if not platform_flag:
        raise click.UsageError("Pick a platform: --claude")
    platform = ClaudePlatform()
    if remove:
        platform.uninstall()
        click.echo(f"Removed tracing for {platform.display_name}")
    else:
        platform.install()
        click.echo(f"Installed tracing for {platform.display_name}")
