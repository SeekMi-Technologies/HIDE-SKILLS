---
name: motion
description: Make the numbers MOVE — an animated bar-chart race as a GIF, ranks sliding past each other month by month. Read it for 动图 / GIF / 动画 / 让数据动起来 / 排名变化 / bar chart race, or when someone wants a picture that plays rather than one that sits still. A static chart is one-pager's job.
scopes: ["im:resource", "docx:document", "drive:drive"]
commands: ["docs +create", "docs +media-insert", "drive +member-add"]
summary:
  zh: "把数据做成会动的 GIF——排名随月份变化，条形互相超越"
  en: "Turn data into a moving GIF — a bar-chart race where ranks overtake month by month"
---
**This skill ships code, and reading it has already put that code in the sandbox.** The
package `skills.motion` exists for `run_python` in this conversation. Do not write your own
animation loop — the parts that look easy are the parts that come out wrong.

## The whole job, one program

```python
import csv
import skills.motion.race as race

with open(path) as fh:                       # from read_attachment / stage_url
    rows = [(r["区域"], r["月份"], r["营收"]) for r in csv.DictReader(fh)]

out = race.bar_race(rows, "race.gif",
                    title="各区域月度营收", subtitle="2026 全年 · 来源 销售明细.csv",
                    unit="¥", note="数据截至 2027-02")
print(out)
```

`out` is `{path, frames, seconds, bytes, kib, periods, entities, shown, notes}` — every
number read back off the written file, not estimated. Put `notes` in your reply if it is
not empty; it says what the encoder had to give up.

Input can be any of these; you do not need to reshape it:
`[(entity, period, value), ...]` · `[{"entity":…, "period":…, "value":…}, ...]` ·
`{entity: {period: value}}`. Values may carry `¥`, `$` and thousands separators.

## What it decides, so you do not have to

- **A bar keeps its colour for the whole animation.** Colour follows the entity, never its
  rank — otherwise the colours stand still while the data moves.
- **Ranks SLIDE.** Position eases separately from value, and settles faster, so an overtake
  reads as an overtake instead of two bars sharing a row for half the month.
- **A missing period carries forward.** An unreported month is not a collapse to zero.
- **The scale eases too**, so nothing jumps when the leader changes.
- **万 / 亿 for Chinese labels, K / M for Latin** — and the CJK font is resolved on the host
  by path, because Pillow has no fallback chain and draws missing glyphs as silent boxes.
- **The file FITS.** `run_python` runs under an 8 MiB write limit, and a file over it does
  not raise — it kills the process with SIGXFSZ and the turn is lost with no output. The
  encoder degrades palette, then size, then frame count (never shortening the animation),
  and if it still cannot fit it REFUSES rather than writing.

Useful arguments: `top_n` (max 8 — more bars than that cannot keep distinct colours),
`seconds_per_period`, `number_style` (`"auto"`, `"cn"`, `"en"`), `max_bytes`.

## Handing it over

```
["docs", "+create", "--title", "各区域月度营收"]
["docs", "+media-insert", "--doc", "<doc id>", "--file", "<staged path>", "--type", "file"]
["drive", "+member-add", "--token", "<doc id>", "--member-id", "<their open_id>", "--perm", "edit"]
```

`stage_artifact(<the path the program printed>)` first — it returns the `<staged path>`.
Say in your reply how long the animation runs and what the last frame shows, because a
reader may see a still preview before they open it.

## Rules

- **One program.** Build the GIF in a single `run_python`. Re-running it to look at the
  file is a wasted turn.
- **Say the result out loud too.** Who ended up on top, who moved. A GIF is the evidence,
  not the answer.
- **Two periods minimum**, and it refuses below that — a race needs something to race.
- **Never invent a period to smooth the curve.** Gaps carry forward and that is the honest
  shape.

## When NOT to use this

- One point in time → `one-pager`. A race over a single month is a bar chart pretending.
- Someone asked a question about the data → answer it; `data-analysis` owns the numbers.
- More than ~20 periods or ~8 entities → say it will be unreadable and offer the top few.
