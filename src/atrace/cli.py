from __future__ import annotations

import click

from atrace import __version__
from atrace.commands.ingest import ingest


@click.group(name="atrace", help="Trace agentic CLIs to a unified local store.")
@click.version_option(__version__, prog_name="atrace")
def main() -> None:
    pass


main.add_command(ingest)
