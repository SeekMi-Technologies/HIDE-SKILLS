---
name: one-pager
description: Turn numbers into ONE forwardable page — KPI tiles, a trend, a ranked list — drawn by a renderer this skill ships. Read it for 一页纸 / 周报 / 日报 / dashboard / report card / 做成一张图, and for "how is the bot doing" (it reads Langfuse itself). For figures or a table, use data-analysis.
scopes: ["im:resource", "docx:document", "drive:drive"]
commands: ["docs +create", "docs +media-insert", "drive +member-add"]
summary:
  zh: "把数据做成一张可直接转发的图：KPI、趋势、排行，样式固定，配色和中文字体都已处理"
  en: "Turn numbers into one forwardable page — KPI tiles, a trend, a ranked list, styled for you"
---
**This skill ships code, and reading it has already put that code in the sandbox.** The
package `skills.one_pager` now exists for `run_python` in this conversation. Import it.
Do not write your own matplotlib — the palette, the type scale, the CJK font and the page
geometry are decided in there, and a hand-rolled chart will be worse and take three turns.

Two routes. Both end in ONE `run_python` call.

## Route A — the bot's own health (no attachment needed)

1. `load_toolkit("langfuse")` **outside** the program. Toolkits are hidden until loaded,
   and code cannot load one.
2. One `run_python`:

```python
import skills.one_pager.lf as lf
import skills.one_pager.report as report

lf.bind(hide)                     # REQUIRED: `hide` is in your globals, not in the module
days = 7
x, y     = lf.daily(days)                      # traces per day
names, v = lf.by_name(days, limit=5)           # busiest trace names
lat      = lf.latency(days)                    # {'p50','p95','avg'} in ms, any may be None
sc       = lf.scores(days)                     # {'pass_rate','modes','count'}

out = report.render({
    "title": "机器人周报",
    "subtitle": f"最近 {days} 天 · environment=sandbox",
    "notes":  [f"p50 {lat['p50']/1000:.1f}s"] if lat["p50"] else [],
    "kpis": [
        {"label": "调用量",     "value": report.compact(sum(y))},
        {"label": "p95 延迟",   "value": f"{lat['p95']/1000:.1f}s" if lat["p95"] else "--",
         "good": "down"},
        {"label": "judge pass", "value": report.pct(sc["pass_rate"]), "good": "up"},
    ],
    "trend": {"title": "每日调用量", "x": x, "series": [{"label": "traces", "y": y}]},
    "bars":  {"title": "失败模式 Top 5",
              "labels": list(sc["modes"])[:5], "values": list(sc["modes"].values())[:5]},
    "footer": "  ·  ".join(lf.notes) or "all panels live from Langfuse",
}, "one-pager.png")
print(out, sum(y), lat, sc["pass_rate"])
```

`lf` never raises. A panel it could not fetch comes back empty and the reason lands in
`lf.notes` — put that in `footer`, and the page says what is missing instead of pretending.
If `lf.available()` is False the bridge is off or the toolkit is not loaded; say so and
use Route B rather than retrying.

Reads available in code: `queryMetrics`, `listScores`, `getMetricsSchema`. Raw traces are
NOT readable from code (one trace is megabytes) — `lf` is the whole surface. Add
`environment="<org>"` to any `lf` call to scope it to one bot.

## Route B — a file someone sent, or the shipped sample

`read_attachment` first (same turn the handles arrive), then:

```python
import skills.one_pager.tidy as tidy
import skills.one_pager.report as report

rows, led = tidy.load_csv(path)                        # path from read_attachment
x, y      = tidy.by_day(rows, "date", agg="sum", value_col="amount", ledger=led)
labels, v = tidy.top_n(rows, "region", value_col="amount", n=5, ledger=led)
out = report.render({... , "footer": led.summary()}, "one-pager.png")
print(out)
```

With nothing sent at all, the package ships `sample_traces.csv` beside it — useful only
for showing what the page looks like; say plainly that it is sample data.

## The spec

| key | type | notes |
|---|---|---|
| `title` | str | required |
| `subtitle` | str | period, source, environment |
| `notes` | list[str] | ≤3, right of the title — p50, cost, anything small |
| `kpis` | list[dict] | ≤4. `label`, `value` (a STRING you formatted), optional `delta` (a fraction: 0.12 = +12%), `good` (`"up"`/`"down"` — which direction is good; omit and the delta is not coloured), `note` |
| `trend` | dict | `title`, `x` (labels), `series`: list of `{label, y}`, ≤3 |
| `bars` | dict | `title`, `labels`, `values` — ranked, ≤8, drawn without an axis |
| `footer` | str | what was dropped, what is missing, where it came from |

Leave a key out and that panel disappears and the page re-flows. `render` returns the
absolute path; it raises `ValueError` naming the key when a spec is malformed.
Helpers: `report.compact(1284) -> '1,284'`, `report.pct(0.87) -> '87%'`.

`tidy`: `load_csv` · `num` · `key` · `day` · `by_day(rows, date_col, value_col, agg=count|sum|mean)`
· `top_n(rows, col, n, value_col)` · `quantiles(values, (0.5, 0.95))` · `pct_change(cur, prev)`.
Pass `ledger=led` to every call, then `led.summary()` is the footer — it separates rows it
could not READ (dropped) from rows that were simply EMPTY for that panel (not a loss).

## Handing it over

```
["docs", "+create", "--title", "机器人周报 2026-09-19"]
["docs", "+media-insert", "--doc", "<doc id>", "--file", "<staged path>", "--type", "file"]
["drive", "+member-add", "--token", "<doc id>", "--member-id", "<their open_id>", "--perm", "edit"]
```

`stage_artifact(<the path run_python printed>)` first — it returns the `<staged path>`.
That doc write is an ordinary write and pauses for confirmation if the policy says so.

## Rules

- **One program.** Fetch, compute and render in a single `run_python`. Re-running to look
  at what you made is a wasted turn — the path comes back in `artifacts`.
- **Print the answer too**, not just the path: the headline numbers belong in your reply,
  and the page is the thing they forward.
- **Never invent a number to fill a tile.** Three honest tiles beat four with a guess.
- **A failure comes back with the traceback.** Fix and retry ONCE, then report what broke.

## When NOT to use this

- Two or three numbers → just say them. A picture of three numbers is worse than three numbers.
- Someone wants the underlying figures, a table, or an answer to a specific question →
  `data-analysis`.
- Audio → `feishu-transcribe`, always.
