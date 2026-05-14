from __future__ import annotations

import json

import click

from thirdeye.config import Config
from thirdeye.meta import read_meta, write_meta
from thirdeye.paths import meta_path, session_dir
from thirdeye.store import Store
from thirdeye.tags import TagStore, validate_tag


def _store() -> Store:
    return Store(Config.load())


def _parse_tags(raw: str) -> list[str]:
    out: list[str] = []
    for piece in raw.split(","):
        orig = piece.strip()
        if not orig:
            continue
        try:
            out.append(validate_tag(orig.lower()))
        except ValueError:
            raise click.ClickException(
                f"invalid tag '{orig}': must match [a-z0-9_-]{{1,64}}"
            ) from None
    return out


@click.command("tag", help="Add, remove, or list tags on session events.")
@click.argument("session_prefix")
@click.argument("seq", required=False, type=int)
@click.option("--add", "add_raw", default=None, help="Comma-separated tags to add.")
@click.option("--remove", "remove_raw", default=None, help="Comma-separated tags to remove.")
@click.option("--list", "list_mode", is_flag=True, help="List tagged events in session.")
def tag(session_prefix, seq, add_raw, remove_raw, list_mode):
    store = _store()
    try:
        platform, sid = store.resolve_session_id(session_prefix)
    except ValueError as e:
        raise click.ClickException(str(e)) from None

    sd = session_dir(store.config.root, platform, sid)
    mp = meta_path(sd)

    if list_mode:
        if add_raw is not None or remove_raw is not None:
            raise click.ClickException("--list cannot be combined with --add or --remove")
        if seq is not None:
            raise click.ClickException("--list does not take a seq argument")
        ts = TagStore(sd)
        for s in sorted(ts.all_tags().keys()):
            tags_sorted = sorted(ts.tags_for(s))
            click.echo(json.dumps({"seq": s, "tags": tags_sorted}, separators=(",", ":")))
        return

    if add_raw is None and remove_raw is None:
        raise click.ClickException("provide --add, --remove, or --list")
    if seq is None:
        raise click.ClickException("SEQ is required for --add/--remove")

    meta = read_meta(mp)
    if meta is None:
        raise click.ClickException(f"no meta for session {sid}")
    n = meta.event_count
    if seq < 0 or seq >= n:
        raise click.ClickException(f"seq {seq} not found in session {sid} (event_count={n})")

    ts = TagStore(sd)
    if add_raw is not None:
        for t in _parse_tags(add_raw):
            ts.add(seq, t)
    if remove_raw is not None:
        for t in _parse_tags(remove_raw):
            ts.remove(seq, t)

    meta.tag_count = ts.tagged_seq_count()
    write_meta(mp, meta)


@click.command("tags", help="Show global tag inventory across all sessions.")
@click.option("--json", "json_mode", is_flag=True, help="Emit one JSON object per line.")
def tags(json_mode):
    store = _store()
    event_counts: dict[str, int] = {}
    session_counts: dict[str, int] = {}
    for meta in store.list_sessions():
        sd = session_dir(store.config.root, meta.platform, meta.session_id)
        ts = TagStore(sd)
        per_tag_events: dict[str, int] = {}
        for tag_set in ts.all_tags().values():
            for t in tag_set:
                per_tag_events[t] = per_tag_events.get(t, 0) + 1
        for t, c in per_tag_events.items():
            event_counts[t] = event_counts.get(t, 0) + c
            session_counts[t] = session_counts.get(t, 0) + 1

    rows = sorted(event_counts.items(), key=lambda kv: (-kv[1], kv[0]))
    for tag_name, ev_count in rows:
        sess_count = session_counts[tag_name]
        if json_mode:
            click.echo(
                json.dumps(
                    {"tag": tag_name, "events": ev_count, "sessions": sess_count},
                    separators=(",", ":"),
                )
            )
        else:
            click.echo(f"{tag_name}\t{ev_count}\t{sess_count}")
