"""Render one page: title, up to four KPI tiles, a trend, a ranked bar list, a footer.

    import skills.one_pager.report as report
    report.render(spec, "one-pager.png")   -> absolute path to the PNG

The point of this module is that the LAYOUT IS NOT YOUR PROBLEM. You supply a small
spec dict of numbers and labels; everything that makes a chart look designed rather
than default -- the palette, the type scale, the CJK font, the tile geometry, the
recessive grid, the direct labels -- happens here, identically every time.

Two rules it enforces on your behalf, because both are silent failures otherwise:

  * The CJK font is resolved explicitly against what this host actually has.
    matplotlib's default (DejaVu Sans) carries NO CJK glyphs and does not warn -- it
    draws a page of empty boxes. If no CJK face is found, the page still renders and
    says so in the footer. A picture that lies about being fine is worse than one
    that admits it.
  * A panel you leave out collapses; the rest of the page re-flows. A missing number
    never leaves a blank rectangle on something someone is about to forward.

The canvas is fixed (11x7in at 150dpi = 1650x1050) and `bbox_inches="tight"` is
deliberately NOT used: a one-pager that changes size with its longest label is not a
one-pager. Colours come from `theme.json` beside this file; a missing or malformed
theme falls back to the defaults below rather than raising.
"""

from __future__ import annotations

import json
import os
import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # the runner sets MPLBACKEND=Agg too; explicit so this also works locally

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Rectangle  # noqa: E402
from matplotlib.ticker import FuncFormatter, MaxNLocator  # noqa: E402

_HERE = Path(__file__).resolve().parent

# Fallback only. `theme.json` is the file to edit -- these values exist so a broken or
# absent theme degrades to a correct page instead of a traceback.
_DEFAULTS = {
    "surface": "#fcfcfb", "panel": "#ffffff", "ink": "#0b0b0b",
    "ink_secondary": "#52514e", "ink_muted": "#8a8983",
    "rule": "#e2e1dc", "grid": "#e7e6e2",
    "series": ["#2a78d6", "#eb6834", "#1baf7a"],
    "bar": "#2a78d6", "bar_track": "#eef3fb",
    "good": "#0ca30c", "bad": "#d03b3b", "warning": "#fab219",
    "fonts": ["Noto Sans CJK SC", "WenQuanYi Zen Hei", "Source Han Sans SC",
              "Noto Sans CJK JP", "Heiti SC", "Microsoft YaHei", "DejaVu Sans"],
    "type_scale": {"title": 22, "subtitle": 11, "tile_label": 10.5, "tile_value": 26,
                   "tile_delta": 10.5, "panel_title": 12.5, "tick": 9.5,
                   "bar_label": 10.5, "footer": 9},
    "figure": {"width_in": 11.0, "height_in": 7.0, "dpi": 150},
}

# A face on this list that is NOT one of these is assumed to carry CJK. Kept as a set of
# the known Latin-only fallbacks rather than a positive list, so adding a CJK face to
# theme.json needs no code change.
_LATIN_ONLY = {"DejaVu Sans", "Liberation Sans", "Arial", "Helvetica"}

MAX_KPIS = 4
MAX_BARS = 8


def _load_theme() -> dict:
    theme = json.loads(json.dumps(_DEFAULTS))  # deep copy
    try:
        loaded = json.loads((_HERE / "theme.json").read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 -- any unreadable theme is the same answer: use defaults
        return theme
    if not isinstance(loaded, dict):
        return theme
    for key, value in loaded.items():
        if key.startswith("_"):
            continue
        if isinstance(value, dict) and isinstance(theme.get(key), dict):
            theme[key].update(value)
        else:
            theme[key] = value
    return theme


THEME = _load_theme()


def font_in_use() -> tuple[str, bool]:
    """(family actually resolved, whether it can draw CJK). Cheap; safe to call anywhere."""
    have = {f.name for f in font_manager.fontManager.ttflist}
    for name in THEME["fonts"]:
        if name in have:
            return name, name not in _LATIN_ONLY
    return "sans-serif", False


def compact(n: float | int | None) -> str:
    """1284 -> '1,284';  12871 -> '12.9K';  4210000 -> '4.2M'. None -> '--'."""
    if n is None:
        return "--"
    try:
        v = float(n)
    except (TypeError, ValueError):
        return str(n)
    a = abs(v)
    if a >= 1_000_000_000:
        return f"{v / 1_000_000_000:.1f}B"
    if a >= 1_000_000:
        return f"{v / 1_000_000:.1f}M"
    if a >= 10_000:
        return f"{v / 1_000:.1f}K"
    if a >= 1000:
        return f"{v:,.0f}"
    if v == int(v):
        return f"{int(v)}"
    return f"{v:.1f}"


def pct(x: float | None, digits: int = 0) -> str:
    """0.873 -> '87%'. Takes a FRACTION, not an already-multiplied percentage."""
    return "--" if x is None else f"{x * 100:.{digits}f}%"


def _clip(text: str, limit: int) -> str:
    text = str(text)
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _has_wide_text(value) -> bool:
    """Does this page actually contain CJK? A warning about a font it never needed is
    noise, and noise on a page someone is about to forward reads as a defect."""
    if isinstance(value, str):
        return any(ord(ch) > 0x2E80 for ch in value)
    if isinstance(value, dict):
        return any(_has_wide_text(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return any(_has_wide_text(v) for v in value)
    return False


def _validate(spec: dict) -> None:
    if not isinstance(spec, dict):
        raise ValueError("render(spec, out): spec must be a dict")
    if not str(spec.get("title") or "").strip():
        raise ValueError("spec['title'] is required and must be a non-empty string")
    for kpi in spec.get("kpis") or []:
        if not isinstance(kpi, dict) or "label" not in kpi or "value" not in kpi:
            raise ValueError("each spec['kpis'] entry needs at least {'label':..., 'value':...}")
    trend = spec.get("trend")
    if trend:
        series = trend.get("series") or []
        if not trend.get("x") or not series:
            raise ValueError("spec['trend'] needs both 'x' and a non-empty 'series' list")
        for s in series:
            if len(s.get("y") or []) != len(trend["x"]):
                raise ValueError(
                    f"spec['trend'] series {s.get('label')!r} has {len(s.get('y') or [])} "
                    f"points but 'x' has {len(trend['x'])} -- they must match")
    bars = spec.get("bars")
    if bars and len(bars.get("labels") or []) != len(bars.get("values") or []):
        raise ValueError("spec['bars']['labels'] and ['values'] must be the same length")


def _tile(fig, rect, kpi, t) -> None:
    x, y, w, h = rect
    fig.patches.append(FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0,rounding_size=0.014",
        mutation_aspect=t["figure"]["width_in"] / t["figure"]["height_in"],
        facecolor=t["panel"], edgecolor=t["rule"], linewidth=0.9,
        transform=fig.transFigure, zorder=1))
    ts = t["type_scale"]
    fig.text(x + 0.018, y + h - 0.022, _clip(kpi["label"], 14), va="top", ha="left",
             fontsize=ts["tile_label"], color=t["ink_secondary"], zorder=2)
    fig.text(x + 0.018, y + h * 0.44, str(kpi["value"]), va="center", ha="left",
             fontsize=ts["tile_value"], color=t["ink"], fontweight="bold", zorder=2)

    delta, note = kpi.get("delta"), kpi.get("note") or ""
    if delta is not None:
        try:
            d = float(delta)
        except (TypeError, ValueError):
            d = None
        if d is not None:
            # Direction is not goodness: a falling refund rate is good. The KPI says which
            # way is up for it; without that we colour nothing and just state the change.
            good = str(kpi.get("good") or "").lower()
            arrow = "▲" if d >= 0 else "▼"
            colour = t["ink_secondary"]
            if good in {"up", "down"}:
                helpful = (d >= 0) == (good == "up")
                colour = t["good"] if helpful else t["bad"]
            places = 0 if abs(d) >= 0.1 else 1
            label = f"{arrow} {abs(d) * 100:.{places}f}%" + (f"  {note}" if note else "")
            fig.text(x + 0.018, y + 0.022, label, va="bottom", ha="left",
                     fontsize=ts["tile_delta"], color=colour, zorder=2)
            return
    if note:
        fig.text(x + 0.018, y + 0.022, _clip(note, 22), va="bottom", ha="left",
                 fontsize=ts["tile_delta"], color=t["ink_muted"], zorder=2)


def _panel_title(fig, rect, text, t) -> None:
    x, y, w, h = rect
    fig.text(x, y + h + 0.014, text, va="bottom", ha="left",
             fontsize=t["type_scale"]["panel_title"], color=t["ink"], fontweight="bold")


def _trend(fig, rect, trend, t) -> None:
    _panel_title(fig, rect, trend.get("title") or "", t)
    ax = fig.add_axes(rect)
    ax.set_facecolor("none")
    labels = [str(v) for v in trend["x"]]
    xs = list(range(len(labels)))
    series = trend["series"][:3]
    peak = 0.0
    for i, s in enumerate(series):
        ys = [0.0 if v is None else float(v) for v in s["y"]]
        peak = max([peak] + ys)
        colour = t["series"][i % len(t["series"])]
        ax.plot(xs, ys, color=colour, lw=2.0, solid_capstyle="round",
                label=str(s.get("label") or ""), zorder=3 + i)
        if len(series) == 1:
            ax.fill_between(xs, 0, ys, color=colour, alpha=0.08, lw=0, zorder=2)
        if len(xs) <= 14:
            ax.plot(xs, ys, "o", ms=4.5, color=colour, mec=t["surface"], mew=1.2,
                    zorder=5 + i)
        # One direct label, on the point people actually look for. Never one per point.
        if xs:
            ax.annotate(compact(ys[-1]), (xs[-1], ys[-1]), textcoords="offset points",
                        xytext=(0, 9), ha="center", fontsize=t["type_scale"]["tick"],
                        color=t["ink"], fontweight="bold", zorder=6)

    ax.set_ylim(0, (peak * 1.14) or 1.0)
    ax.set_xlim(-0.35, max(len(xs) - 0.65, 0.65))
    step = max(1, len(xs) // 7 + (1 if len(xs) % 7 else 0))
    ticks = xs[::step]
    ax.set_xticks(ticks)
    ax.set_xticklabels([labels[i] for i in ticks])
    ax.yaxis.set_major_locator(MaxNLocator(3, prune="lower"))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _pos: compact(v)))
    ax.grid(axis="y", color=t["grid"], lw=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(t["rule"])
    ax.tick_params(length=0, pad=6, labelsize=t["type_scale"]["tick"],
                   colors=t["ink_secondary"])
    if len(series) > 1:
        ax.legend(frameon=False, fontsize=t["type_scale"]["tick"], loc="upper left",
                  labelcolor=t["ink_secondary"], handlelength=1.6, ncols=len(series))


def _bars(fig, rect, bars, t) -> None:
    _panel_title(fig, rect, bars.get("title") or "", t)
    ax = fig.add_axes(rect)
    ax.set_facecolor("none")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    pairs = list(zip(bars["labels"], bars["values"]))[:MAX_BARS]
    if not pairs:
        return
    values = [0.0 if v is None else float(v) for _, v in pairs]
    top = max(values) or 1.0
    rows = len(pairs)
    row_h = 1.0 / rows
    ts = t["type_scale"]
    for i, ((label, _), value) in enumerate(zip(pairs, values)):
        row_top = 1.0 - i * row_h
        bar_y = row_top - row_h * 0.78
        bar_h = row_h * 0.30
        # The category name sits ABOVE its bar rather than in a left column: labels here
        # are free text of any length, and a left column would either clip them or shove
        # the plot around. This way nothing collides, whatever anyone names a failure mode.
        ax.text(0, row_top - row_h * 0.26, _clip(label, 22), va="center", ha="left",
                fontsize=ts["bar_label"], color=t["ink"])
        ax.text(1, row_top - row_h * 0.26, compact(value), va="center", ha="right",
                fontsize=ts["bar_label"], color=t["ink_secondary"])
        ax.add_patch(Rectangle((0, bar_y), 1, bar_h, facecolor=t["bar_track"],
                               edgecolor="none", zorder=1))
        ax.add_patch(Rectangle((0, bar_y), max(value / top, 0.004), bar_h,
                               facecolor=t["bar"], edgecolor="none", zorder=2))


def _footer(fig, text, t) -> None:
    m = 0.045
    fig.add_artist(Line2D([m, 1 - m], [0.098, 0.098], color=t["rule"], lw=0.9,
                          transform=fig.transFigure))
    if not text:
        return
    words, lines, line = str(text).split(), [], ""
    for word in words:
        if len(line) + len(word) + 1 > 150:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    lines.append(line)
    fig.text(m, 0.072, "\n".join(lines[:2]), va="top", ha="left",
             fontsize=t["type_scale"]["footer"], color=t["ink_muted"], linespacing=1.5)


def render(spec: dict, out_path: str = "one-pager.png") -> str:
    """Draw the page and return the absolute path of the file written."""
    _validate(spec)
    t = THEME
    family, cjk_ok = font_in_use()
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": [family] + list(t["fonts"]),
        "axes.unicode_minus": False,
    })

    fig = plt.figure(figsize=(t["figure"]["width_in"], t["figure"]["height_in"]),
                     dpi=t["figure"]["dpi"])
    fig.patch.set_facecolor(t["surface"])
    m, content = 0.045, 1 - 2 * 0.045
    ts = t["type_scale"]

    fig.text(m, 0.955, str(spec["title"]), va="top", ha="left", fontsize=ts["title"],
             color=t["ink"], fontweight="bold")
    if spec.get("subtitle"):
        fig.text(m, 0.902, str(spec["subtitle"]), va="top", ha="left",
                 fontsize=ts["subtitle"], color=t["ink_secondary"])
    if spec.get("notes"):
        fig.text(1 - m, 0.952, "  ·  ".join(str(n) for n in spec["notes"][:3]),
                 va="top", ha="right", fontsize=ts["subtitle"], color=t["ink_secondary"])

    kpis = list(spec.get("kpis") or [])[:MAX_KPIS]
    trend, bars = spec.get("trend"), spec.get("bars")
    panels_top = 0.645 if kpis else 0.855

    if kpis:
        gap = 0.016
        w = (content - gap * (len(kpis) - 1)) / len(kpis)
        for i, kpi in enumerate(kpis):
            _tile(fig, (m + i * (w + gap), 0.700, w, 0.155), kpi, t)

    panel_bottom = 0.170
    panel_h = panels_top - panel_bottom - 0.030  # room for the panel title above the axes
    if trend and bars:
        tw = content * 0.575
        bw = content - tw - 0.045
        _trend(fig, (m, panel_bottom, tw, panel_h), trend, t)
        _bars(fig, (m + tw + 0.045, panel_bottom, bw, panel_h), bars, t)
    elif trend:
        _trend(fig, (m, panel_bottom, content, panel_h), trend, t)
    elif bars:
        _bars(fig, (m, panel_bottom, content * 0.62, panel_h), bars, t)

    footer = str(spec.get("footer") or "")
    if not cjk_ok and _has_wide_text(spec):
        warning = ("no CJK font on this host, so non-Latin labels above may be drawn as "
                   "empty boxes")
        footer = f"{footer}  ·  {warning}" if footer else warning
    _footer(fig, footer, t)

    with warnings.catch_warnings():
        if not cjk_ok:
            # Already reported, in the footer, in one line. Forty per-glyph warnings on
            # stderr say nothing more and cost the model its output budget.
            warnings.filterwarnings("ignore", message=".*missing from font.*")
        fig.savefig(out_path, facecolor=t["surface"])
    plt.close(fig)
    return os.path.abspath(out_path)
