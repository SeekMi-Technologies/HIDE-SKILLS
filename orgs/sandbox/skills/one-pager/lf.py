"""Langfuse numbers, fetched from INSIDE the sandbox, shaped for `report.render`.

    import skills.one_pager.lf as lf
    lf.bind(hide)                       # <- required first line; see below
    x, y = lf.daily(7)

WHY `bind`: the sandbox injects `hide` into YOUR program's globals, not into imported
modules, so this file cannot reach it on its own. One line hands it over. (If you
forget, `bind` is attempted automatically from the calling frame -- but write the line;
magic that half-works is worse than a rule.)

WHAT THIS BUYS YOU: the Metrics v2 query body, the fact that the daily bucket field has
to be discovered rather than assumed, the p50/p95 fallback, the MCP content unwrapping,
and the fact that a refused panel must not take the page down. All of it is decided once
here instead of re-derived, differently, every turn.

BUDGET: the bridge allows 64 calls and 5 MB per program. Every function here is one
call, except `daily`'s fallback path, which spends one per day IN A SINGLE ROUND TRIP
via `hide.gather`. Nothing here pages through traces: the agent surface is metrics and
scores (`queryMetrics`, `listScores`, `getMetricsSchema`) -- raw observation reads are
deliberately not available, because one trace is 0.3-5.9 MB.

NOTHING HERE RAISES. A refusal, a missing toolkit or an unexpected payload returns an
empty result and appends a line to `lf.notes`, which belongs in `spec['footer']` so the
page says which panel is missing and why.
"""

from __future__ import annotations

import datetime as _dt
import json
import sys

notes: list[str] = []

_BOUND = None
_SHAPE = None       # which call shape queryMetrics accepted; learned once, then reused
_ROW_LIMIT = 500


def bind(hide_obj) -> bool:
    """Hand over the `hide` object from your program's globals. True if langfuse is there."""
    global _BOUND
    _BOUND = hide_obj
    return available()


def _resolve():
    if _BOUND is not None:
        return _BOUND
    # Fallback: find `hide` in a caller's globals. The program is somewhere up this stack.
    frame = sys._getframe(1)
    for _ in range(12):
        if frame is None:
            break
        candidate = frame.f_globals.get("hide")
        if candidate is not None:
            return candidate
        frame = frame.f_back
    return None


def available() -> bool:
    """Is the bridge on AND the langfuse toolkit loaded this turn?"""
    hide_obj = _resolve()
    if hide_obj is None:
        _note("the code bridge is off here, so Langfuse cannot be read from inside a "
              "program -- use a CSV instead")
        return False
    if getattr(hide_obj, "langfuse", None) is None:
        _note("the langfuse toolkit is not loaded this turn -- call "
              "load_toolkit('langfuse') outside the program, then run again")
        return False
    return True


def _note(text: str) -> None:
    if text not in notes:
        notes.append(text)


def _window(days: int) -> tuple[str, str]:
    now = _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0)
    start = (now - _dt.timedelta(days=days)).replace(hour=0, minute=0, second=0)
    iso = lambda d: d.isoformat().replace("+00:00", "Z")  # noqa: E731
    return iso(start), iso(now)


def _query(view: str, metrics: list[dict], dimensions=None, environment=None,
           since=None, until=None, days: int = 7, granularity=None,
           order_by=None) -> dict:
    """One Metrics v2 query body -- the shape proven against production."""
    start, end = (since, until) if since and until else _window(days)
    body: dict = {
        "view": view,
        "dimensions": dimensions or [],
        "metrics": metrics,
        "filters": [],
        "fromTimestamp": start,
        "toTimestamp": end,
        "orderBy": order_by,
        "config": {"row_limit": _ROW_LIMIT},
    }
    if environment:
        body["filters"].append({"type": "stringOptions", "column": "environment",
                                "operator": "any of", "value": [environment]})
    if granularity:
        body["timeDimension"] = {"granularity": granularity}
    return body


def _shapes(body: dict):
    """The ways this MCP server might want the query. Learned once, then reused."""
    return [("query_obj", {"query": body}),
            ("query_str", {"query": json.dumps(body, separators=(",", ":"))}),
            ("flat", dict(body))]


def _call(slug: str, **kwargs):
    """One bridge call. Returns None and records why, rather than raising."""
    hide_obj = _resolve()
    tool = getattr(getattr(hide_obj, "langfuse", None), slug, None)
    if tool is None:
        _note(f"langfuse.{slug} is not available to this program")
        return None
    try:
        return tool(**kwargs)
    except Exception as exc:  # noqa: BLE001 -- a refusal is data here, not an error
        kind = type(exc).__name__
        if kind == "NeedsApproval":
            _note(f"{slug} needs a human, so it cannot run inside code")
        else:
            _note(f"{slug} failed: {str(exc)[:120]}")
        return None


def query_metrics(body: dict):
    """queryMetrics with whichever argument shape this server accepts. Rows, or []."""
    global _SHAPE
    shapes = _shapes(body)
    if _SHAPE is not None:
        shapes = [s for s in shapes if s[0] == _SHAPE] + [s for s in shapes if s[0] != _SHAPE]
    before = len(notes)
    for name, kwargs in shapes:
        reply = _call("queryMetrics", **kwargs)
        if reply is not None:
            rows = _rows(reply)
            if rows or _SHAPE == name:
                _SHAPE = name
                del notes[before:]          # a shape that failed on the way is not news
                return rows
    # Every shape failed. The FIRST message is the server's real objection; the rest are
    # this function trying the other spellings, and three of those on one page is noise.
    del notes[before + 1:]
    return []


def _rows(reply) -> list[dict]:
    """MCP content -> a list of row dicts, whatever envelope it arrived in."""
    if reply is None:
        return []
    if isinstance(reply, str):
        try:
            return _rows(json.loads(reply))
        except ValueError:
            return []
    if isinstance(reply, list):
        if reply and isinstance(reply[0], dict) and "text" in reply[0]:
            return _rows(reply[0]["text"])       # [{"type":"text","text":"<json>"}]
        return [r for r in reply if isinstance(r, dict)]
    if isinstance(reply, dict):
        for field in ("data", "rows", "result", "content", "items"):
            if field in reply:
                return _rows(reply[field])
        return [reply]
    return []


def _pick(row: dict, *fragments: str):
    """The first value whose key contains every fragment -- Metrics v2 names its columns
    `<measure>_<aggregation>` (`count_count`, `latency_p95`), and that spelling is not
    something to hard-code from memory."""
    for column, value in row.items():
        low = column.lower()
        if all(f.lower() in low for f in fragments):
            return value
    return None


def _bucket(rows: list[dict]):
    """The column holding the day, found by parsing rather than by name."""
    from . import tidy
    for column in (rows[0] if rows else {}):
        if all(tidy.day(r.get(column)) is not None for r in rows[:5]):
            return column
    return None


def daily(days: int = 7, environment: str | None = None, view: str = "traces"):
    """(labels, counts) per day, zero-traffic days included. ([], []) if unavailable."""
    from . import tidy
    if not available():
        return [], []
    metrics = [{"measure": "count", "aggregation": "count"}]
    rows = query_metrics(_query(view, metrics, environment=environment, days=days,
                                granularity="day"))
    column = _bucket(rows)
    if rows and column:
        counted = {tidy.day(r.get(column)): float(_pick(r, "count") or 0) for r in rows}
    else:
        # This server has no time dimension, so ask day by day -- in ONE round trip.
        if rows:
            _note("daily buckets came back without a date column; asked per day instead")
        counted = _per_day(days, environment, view, metrics)
    if not counted:
        return [], []
    start, end = min(counted), max(counted)
    labels, values, cursor = [], [], start
    while cursor <= end:
        labels.append(cursor.strftime("%m-%d"))
        values.append(counted.get(cursor, 0.0))
        cursor += _dt.timedelta(days=1)
    return labels, values


def _per_day(days: int, environment, view: str, metrics: list[dict]) -> dict:
    hide_obj = _resolve()
    today = _dt.datetime.now(_dt.timezone.utc).date()
    wanted = [today - _dt.timedelta(days=n) for n in range(days - 1, -1, -1)]
    bodies = []
    for when in wanted:
        start = _dt.datetime.combine(when, _dt.time.min, _dt.timezone.utc)
        bodies.append(_query(view, metrics, environment=environment,
                             since=start.isoformat().replace("+00:00", "Z"),
                             until=(start + _dt.timedelta(days=1)).isoformat()
                             .replace("+00:00", "Z")))
    # Day one goes through query_metrics so the accepted call shape is LEARNED before the
    # batch: a gather sent in the wrong shape fails all seven at once and reads as "no data".
    counted = {}
    first = _rows_to_count(query_metrics(bodies[0]))
    if first is not None:
        counted[wanted[0]] = first

    gather = getattr(hide_obj, "gather", None)
    tool = getattr(getattr(hide_obj, "langfuse", None), "queryMetrics", None)
    shape = _SHAPE or "query_obj"
    rest = list(zip(wanted[1:], bodies[1:]))
    replies = []
    if gather is not None and tool is not None and rest:
        try:
            replies = gather([(tool, dict(_shapes(b))[shape]) for _, b in rest])
        except Exception as exc:  # noqa: BLE001
            _note(f"per-day gather failed: {str(exc)[:100]}")
            replies = []
    if not replies:
        replies = [_call("queryMetrics", **dict(_shapes(b))[shape]) for _, b in rest]

    if len(replies) != len(rest):
        # A short batch is not a quiet day. Truncating here would draw a zero for a day
        # nobody measured, which is the one thing a page like this must never do.
        _note(f"the per-day batch answered {len(replies)} of {len(rest)} days")
    for (when, _), reply in zip(rest, replies):
        if isinstance(reply, BaseException) or reply is None:
            continue
        counted[when] = _rows_to_count(_rows(reply)) or 0.0
    missing = [d for d in wanted if d not in counted]
    if missing:
        _note(f"{len(missing)} day(s) could not be read and are drawn as zero")
    return counted


def _rows_to_count(rows):
    if rows is None:
        return None
    return float(_pick(rows[0], "count") or 0) if rows else 0.0


def by_name(days: int = 7, environment: str | None = None, limit: int = 5,
            view: str = "traces"):
    """(labels, counts) for the busiest trace names. ([], []) if unavailable."""
    if not available():
        return [], []
    rows = query_metrics(_query(
        view, [{"measure": "count", "aggregation": "count"}],
        dimensions=[{"field": "name"}], environment=environment, days=days,
        order_by=[{"field": "count_count", "direction": "desc"}]))
    ranked = [(str(r.get("name") or "(unnamed)"), float(_pick(r, "count") or 0))
              for r in rows]
    ranked.sort(key=lambda pair: pair[1], reverse=True)
    ranked = ranked[:limit]
    return [n for n, _ in ranked], [v for _, v in ranked]


def latency(days: int = 7, environment: str | None = None) -> dict:
    """{'p50':ms,'p95':ms,'avg':ms} -- any value may be None if the server cannot aggregate."""
    if not available():
        return {"p50": None, "p95": None, "avg": None}
    before = len(notes)
    rows = query_metrics(_query("traces", [
        {"measure": "latency", "aggregation": "p50"},
        {"measure": "latency", "aggregation": "p95"},
        {"measure": "latency", "aggregation": "avg"},
    ], environment=environment, days=days))
    if not rows:
        # Percentile aggregations are the part most likely to be unsupported; a mean we
        # can always get, and a labelled mean beats a blank tile.
        rows = query_metrics(_query("traces", [
            {"measure": "latency", "aggregation": "avg"}], environment=environment,
            days=days))
        if rows:
            # One sentence a reader can act on, in place of the raw refusal it replaces.
            del notes[before:]
            _note("percentile latency unavailable on this project; showing the mean")
    if not rows:
        return {"p50": None, "p95": None, "avg": None}
    out = {name: _pick(rows[0], "latency", name) for name in ("p50", "p95", "avg")}
    return {k: (float(v) if v is not None else None) for k, v in out.items()}


def cost_tokens(days: int = 7, environment: str | None = None) -> dict:
    """{'cost': usd, 'tokens': n} over the window; either may be None."""
    if not available():
        return {"cost": None, "tokens": None}
    rows = query_metrics(_query("observations", [
        {"measure": "totalCost", "aggregation": "sum"},
        {"measure": "totalTokens", "aggregation": "sum"},
    ], environment=environment, days=days))
    if not rows:
        return {"cost": None, "tokens": None}
    cost, tokens = _pick(rows[0], "cost"), _pick(rows[0], "token")
    return {"cost": float(cost) if cost is not None else None,
            "tokens": float(tokens) if tokens is not None else None}


def scores(days: int = 7, environment: str | None = None, name_contains: str = "") -> dict:
    """{'pass_rate': float|None, 'modes': {label: n}, 'count': n} from listScores."""
    from . import tidy
    blank = {"pass_rate": None, "modes": {}, "count": 0}
    if not available():
        return blank
    start, end = _window(days)
    reply, before = None, len(notes)
    for kwargs in ({"fromTimestamp": start, "toTimestamp": end, "limit": 100},
                   {"from_timestamp": start, "to_timestamp": end, "limit": 100},
                   {"limit": 100}, {}):
        reply = _call("listScores", **kwargs)
        if reply is not None:
            del notes[before:]   # a shape rejected on the way to one that worked is not news
            break
    rows = _rows(reply)
    if not rows:
        return blank

    numeric, modes = [], {}
    for row in rows:
        label = str(row.get("name") or "")
        if name_contains and name_contains not in label:
            continue
        value = row.get("value")
        text = row.get("stringValue") or row.get("string_value")
        if text:
            modes[str(text)] = modes.get(str(text), 0) + 1
        number = tidy.num(value)
        if number is not None and "fail" not in label.lower():
            numeric.append(1.0 if number >= 0.5 else 0.0)
    return {"pass_rate": (sum(numeric) / len(numeric)) if numeric else None,
            "modes": dict(sorted(modes.items(), key=lambda kv: -kv[1])),
            "count": len(rows)}


def schema():
    """getMetricsSchema, raw -- print it when a query comes back empty and you want to know why."""
    return _call("getMetricsSchema") if available() else None
