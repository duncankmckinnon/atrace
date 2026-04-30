import click

from atrace import __version__
from atrace.commands.add import add
from atrace.commands.list import list_sessions
from atrace.commands.search import search
from atrace.commands.show import show


@click.group(help="Trace agentic CLIs to a unified local store.")
@click.version_option(__version__, prog_name="atrace")
def main() -> None:
    pass


main.add_command(add)
main.add_command(list_sessions, name="list")
main.add_command(show)
main.add_command(search)
