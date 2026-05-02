from __future__ import annotations

import click

from atrace import __version__
from atrace.commands.add import add
from atrace.commands.ingest import ingest
from atrace.commands.reads import event, events, list_sessions, search, show, stats, tail


@click.group(name="atrace", help="Trace agentic CLIs to a unified local store.")
@click.version_option(__version__, prog_name="atrace")
def main() -> None:
    pass


main.add_command(add)
main.add_command(ingest)
main.add_command(list_sessions)
main.add_command(show)
main.add_command(events)
main.add_command(tail)
main.add_command(event)
main.add_command(search)
main.add_command(stats)
