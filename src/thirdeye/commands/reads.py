from __future__ import annotations

import json
from dataclasses import asdict

import click

from thirdeye.config import Config
from thirdeye.render import render_event_jsonl, render_event_terse, render_event_tree
from thirdeye.search import search as search_fn
from thirdeye.store import Store


def _store() -> Store:
    return Store(Config.load())


def _emit_events(events, *, json_mode: bool, tree_mode: bool, width: int) -> None:
    for event in events:
        if json_mode:
            click.echo(render_event_jsonl(event))
        elif tree_mode:
            click.echo(render_event_tree(event))
        else:
            click.echo(render_event_terse(event, width=width))


@click.command("list", help="List recorded sessions.")
@click.option("--platform", default=None)
@click.option("--cwd", default=None)
@click.option("--status", default=None)
@click.option("--tree", is_flag=True, help="Human-readable tree output.")
def list_sessions(platform, cwd, status, tree):
    store = _store()
    for meta in store.list_sessions(platform=platform, cwd=cwd, status=status):
        if tree:
            click.echo(
                f"{meta.session_id}  [{meta.platform}]  {meta.cwd}  "
                f"{meta.status}  events={meta.event_count}"
            )
        else:
            click.echo(json.dumps(asdict(meta), default=str, separators=(",", ":")))


@click.command(help="Print events for a session.")
@click.argument("session_prefix")
@click.option("--type", "types", multiple=True, help="Filter by event type (repeatable).")
@click.option("--json", "json_mode", is_flag=True)
@click.option("--tree", "tree_mode", is_flag=True)
@click.option("--width", default=120, type=int, help="Line width (0 = unlimited).")
def events(session_prefix, types, json_mode, tree_mode, width):
    reader = _store().reader(session_prefix)
    iter_ = reader.iter_events(types=set(types) if types else None)
    _emit_events(iter_, json_mode=json_mode, tree_mode=tree_mode, width=width)


@click.command(help="Show all events for a session (alias of `events`).")
@click.argument("session_prefix")
@click.option("--json", "json_mode", is_flag=True)
@click.option("--tree", "tree_mode", is_flag=True)
@click.option("--width", default=120, type=int)
def show(session_prefix, json_mode, tree_mode, width):
    reader = _store().reader(session_prefix)
    _emit_events(reader.iter_events(), json_mode=json_mode, tree_mode=tree_mode, width=width)


@click.command(help="Last N events for a session.")
@click.argument("session_prefix")
@click.option("-n", "n", default=10, type=int)
@click.option("--json", "json_mode", is_flag=True)
@click.option("--tree", "tree_mode", is_flag=True)
@click.option("--width", default=120, type=int)
def tail(session_prefix, n, json_mode, tree_mode, width):
    reader = _store().reader(session_prefix)
    all_events = list(reader.iter_events())
    _emit_events(all_events[-n:], json_mode=json_mode, tree_mode=tree_mode, width=width)


@click.command(help="Print a single event by seq, fully expanded.")
@click.argument("session_prefix")
@click.argument("seq", type=int)
@click.option("--field", default=None, help="Print only one field of `data`.")
def event(session_prefix, seq, field):
    e = _store().reader(session_prefix).get_event(seq)
    if field is not None:
        data = e.get("data")
        if isinstance(data, dict) and field in data:
            value = data[field]
            if isinstance(value, (str, int, float, bool)):
                click.echo(value)
            else:
                click.echo(json.dumps(value, default=str, ensure_ascii=False))
            return
        raise click.ClickException(f"field {field!r} not found in event data")
    click.echo(json.dumps(e, default=str, ensure_ascii=False, indent=2))


@click.command(help="Search across sessions.")
@click.argument("query")
@click.option("--platform", default=None)
@click.option("--cwd", default=None)
def search(query, platform, cwd):
    for hit in search_fn(_store(), query, platform=platform, cwd=cwd):
        click.echo(json.dumps(asdict(hit), default=str, ensure_ascii=False, separators=(",", ":")))


@click.command(help="Stats for a session, or global if no id given.")
@click.argument("session_prefix", required=False)
def stats(session_prefix):
    store = _store()
    s = store.stats(session_id=session_prefix) if session_prefix else store.stats()
    click.echo(json.dumps(s, default=str, ensure_ascii=False))
