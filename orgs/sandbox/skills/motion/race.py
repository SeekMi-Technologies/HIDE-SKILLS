"""A bar-chart race: ranked bars that slide past each other as the periods advance.

    import skills.motion.race as race
    race.bar_race(rows, "race.gif", title="各区域月度营收")

What is hard about this, and therefore why it is shipped:

  * RANK MOTION. The bars have to SLIDE past each other. Interpolating each bar's value
    and re-sorting every frame does not do that -- it teleports a bar the instant it
    overtakes, which is the tell of a hand-rolled race. The position is interpolated
    separately from the value: rank at the previous period eased to rank at the next.
  * STABLE COLOUR. A bar keeps its colour for the whole animation. Colouring by rank
    means the colours stay still while the data moves, which is precisely backwards.
  * THE SCALE HAS TO MOVE TOO, and ease with everything else, or the bars jump whenever
    the leader changes.
  * A GIF THAT FITS. See draw.encode.

Input is whatever shape the data arrived in: rows of (entity, period, value) as dicts or
tuples, or {entity: {period: value}}.
"""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw

from . import draw

_HERE = Path(__file__).resolve().parent

_DEFAULTS = {
    "width": 960, "height": 540, "top_n": 8, "steps": 11, "hold": 3, "tail": 18,
    "frame_ms": 55, "hold_ms": 110, "tail_ms": 90,
    "bg": "#12161f", "ink": "#f2f4f8", "muted": "#9aa3b2", "track": "#1b2130",
    "series": ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#4a3aa7",
               "#e34948", "#3fb6c8"],
}


def _theme() -> dict:
    theme = dict(_DEFAULTS)
    try:
        loaded = json.loads((_HERE / "theme.json").read_text(encoding="utf-8"))
        theme.update({k: v for k, v in loaded.items() if not k.startswith("_")})
    except Exception:  # noqa: BLE001 -- a broken theme must not stop the render
        pass
    return theme


def normalise(data) -> tuple[list[str], list[str], dict]:
    """-> (entities in first-seen order, periods sorted, {(entity, period): value})."""
    table: dict = {}
    entities: list[str] = []
    periods: set = set()

    def put(entity, period, value):
        entity, period = str(entity).strip(), str(period).strip()
        try:
            number = float(str(value).replace(",", "").replace("¥", "").strip())
        except (TypeError, ValueError):
            return
        if entity not in entities:
            entities.append(entity)
        periods.add(period)
        table[(entity, period)] = table.get((entity, period), 0.0) + number

    if isinstance(data, dict):
        for entity, by_period in data.items():
            for period, value in (by_period or {}).items():
                put(entity, period, value)
    else:
        for row in data or []:
            if isinstance(row, dict):
                keys = list(row)
                put(row.get("entity", row.get(keys[0])),
                    row.get("period", row.get(keys[1] if len(keys) > 1 else keys[0])),
                    row.get("value", row.get(keys[2] if len(keys) > 2 else keys[0])))
            elif len(row) >= 3:
                put(row[0], row[1], row[2])
    if not table:
        raise ValueError("no usable rows — each needs an entity, a period and a number")
    return entities, sorted(periods), table


def _carry_forward(entities, periods, table) -> dict:
    """A missing period is the last known value, not zero: a race that drops a bar to the
    floor because one month was not reported tells a story that did not happen."""
    filled = {}
    for entity in entities:
        running = 0.0
        seen = False
        for period in periods:
            if (entity, period) in table:
                running = table[(entity, period)]
                seen = True
            filled[(entity, period)] = running if seen else 0.0
    return filled


def _fmt(value: float, unit: str = "", style: str = "cn") -> str:
    absolute = abs(value)
    if style == "en":
        if absolute >= 1_000_000_000:
            return f"{unit}{value / 1_000_000_000:.2f}B"
        if absolute >= 1_000_000:
            return f"{unit}{value / 1_000_000:.2f}M"
        if absolute >= 10_000:
            return f"{unit}{value / 1_000:.1f}K"
        return f"{unit}{value:,.0f}"
    if absolute >= 100_000_000:
        body = f"{value / 100_000_000:.2f}亿"
    elif absolute >= 10_000:
        body = f"{value / 10_000:.1f}万"
    elif absolute >= 1000:
        body = f"{value:,.0f}"
    else:
        body = f"{value:.0f}" if value == int(value) else f"{value:.1f}"
    return f"{unit}{body}"


def bar_race(data, out_path: str = "race.gif", *, title: str = "", subtitle: str = "",
             unit: str = "", note: str = "", top_n: int | None = None,
             number_style: str = "auto",
             seconds_per_period: float | None = None, max_bytes: int = 7_000_000) -> dict:
    """Render the race. Returns {path, frames, seconds, bytes, notes, periods, entities}."""
    theme = _theme()
    entities, periods, table = normalise(data)
    if len(periods) < 2:
        raise ValueError(f"a race needs at least two periods; got {periods}")
    values = _carry_forward(entities, periods, table)

    # More than eight bars is unreadable at this size AND forces colour reuse, which breaks
    # the one rule that makes a race legible: a bar keeps its colour throughout.
    shown = min(int(top_n or theme["top_n"]), 8, len(entities))
    colour = {e: theme["series"][i % len(theme["series"])] for i, e in enumerate(entities)}

    steps = int(theme["steps"])
    if seconds_per_period:
        steps = max(4, round(seconds_per_period * 1000 / theme["frame_ms"]))

    ranks = {}
    for period in periods:
        order = sorted(entities, key=lambda e: (-values[(e, period)], e))
        ranks[period] = {entity: i for i, entity in enumerate(order)}

    W, H = int(theme["width"]), int(theme["height"])
    frames, durations = [], []
    notes: list[str] = []
    wide = draw.has_wide([title, subtitle, note, *entities])
    # 万/亿 on a chart whose labels are all Latin is as wrong as 口口 on a Chinese one.
    style = number_style if number_style != "auto" else ("cn" if wide else "en")
    if wide and not draw.cjk_ok():
        notes.append("no CJK font on this host — non-Latin labels may render as boxes")

    def frame_at(p_from: str, p_to: str, t: float):
        eased = draw.ease(t)
        # Position settles in the first 55% of the transition; the value keeps climbing
        # for all of it. Easing both at the same rate leaves two bars sharing one row for
        # half the period, which a viewer reads as a rendering fault, not as an overtake.
        settled = draw.ease(min(1.0, t / 0.55))
        live = {}
        for entity in entities:
            value = draw.lerp(values[(entity, p_from)], values[(entity, p_to)], eased)
            slot = draw.lerp(ranks[p_from][entity], ranks[p_to][entity], settled)
            live[entity] = (value, slot)
        peak = max(1.0, max(v for v, _ in live.values()))
        label = p_to if t > 0.5 else p_from
        return _paint(theme, W, H, live, colour, peak, shown, title, subtitle,
                      label, unit, note, style)

    for index in range(len(periods) - 1):
        p_from, p_to = periods[index], periods[index + 1]
        for step in range(steps):
            frames.append(frame_at(p_from, p_to, step / steps))
            durations.append(theme["frame_ms"])
        for _ in range(int(theme["hold"])):
            frames.append(frame_at(p_from, p_to, 1.0))
            durations.append(theme["hold_ms"])
    # Hold the final standings: a race that loops the instant it finishes is a race nobody
    # can read the result of.
    last = frames[-1]
    for _ in range(int(theme["tail"])):
        frames.append(last)
        durations.append(theme["tail_ms"])

    report = draw.encode(frames, out_path, durations, max_bytes=max_bytes)
    notes.extend(report["gave_up"])
    return {"path": str(Path(out_path).resolve()), "frames": report["frames"],
            "seconds": report["seconds"],
            "bytes": report["bytes"], "kib": report["bytes"] // 1024,
            "periods": len(periods), "entities": len(entities), "shown": shown,
            "notes": notes}


def _paint(theme, W, H, live, colour, peak, shown, title, subtitle, period, unit, note,
           style="cn"):
    image = Image.new("RGB", (W, H), theme["bg"])
    d = ImageDraw.Draw(image)
    pad = 34
    top = pad + (46 if title else 0) + (22 if subtitle else 0)
    bottom = H - pad - (20 if note else 0)
    row_h = (bottom - top) / max(1, shown)
    bar_h = min(row_h * 0.62, 46)
    left = pad + 132          # the label column
    right = W - pad - 96      # room for the value

    if title:
        draw.text(d, (pad, pad), title, 27, theme["ink"])
    if subtitle:
        draw.text(d, (pad, pad + 34), subtitle, 13, theme["muted"])
    # The period is the clock of the whole thing, so it is the biggest number on screen.
    draw.text(d, (W - pad, pad + 6), period, 42, theme["ink"], anchor="ra")

    for entity, (value, slot) in sorted(live.items(), key=lambda kv: -kv[1][1]):
        if slot > shown - 0.35:      # off the board, but still eased so it slides away
            continue
        y = top + slot * row_h + (row_h - bar_h) / 2
        width = max(2.0, (right - left) * (value / peak))
        draw.rounded(d, (left, y, left + width, y + bar_h), bar_h * 0.22, colour[entity])
        draw.text(d, (left - 12, y + bar_h / 2), entity, 15, theme["ink"], anchor="rm")
        draw.text(d, (left + width + 10, y + bar_h / 2), _fmt(value, unit, style), 15,
                  theme["muted"], anchor="lm")
    if note:
        draw.text(d, (pad, H - pad - 4), note, 11, theme["muted"], anchor="ls")
    return image
