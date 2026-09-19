# motion — demo runbook

Operator notes. Not served to the model: `demo/` holds no `SKILL.md`, so the loader never
attaches these files to a skill.

## What it demonstrates

This product has never produced a moving artifact. `motion` ships a bar-chart-race engine;
the agent supplies the rows and gets back a GIF that plays.

Four things in the shipped code are what a model improvises wrong, every time:

1. **Ranks slide.** Interpolating values and re-sorting each frame teleports a bar the
   instant it overtakes. Position is eased separately from value, and settles faster, so an
   overtake reads as an overtake instead of two bars sharing a row for half the month.
2. **Colour follows the entity, never the rank.** Otherwise the colours stand still while
   the data moves — the single most common way a race chart becomes unreadable.
3. **The file fits.** `run_python` runs under RLIMIT_FSIZE (8 MiB), and a file over it does
   not raise — it kills the process with SIGXFSZ and the turn ends with no output at all.
   The encoder builds in memory, measures, then degrades palette → scale → frame count
   (lengthening each surviving frame so the animation keeps its duration), and refuses
   rather than writing something that would trip the limit.
4. **Every number it reports is read back off the file.** Pillow folds consecutive
   identical frames into one with a longer delay, so the frame count you sent is not the
   frame count on disk. Measured: 140 frames, 13.1 s, 365 KiB for the shipped sample.

## The demo

> 把这个表做成一个会动的排名图

Attachment, or `stage_url` from a link. Expect `read_skill("motion")` → one `run_python` →
`stage_artifact` → `docs +create` / `docs +media-insert` / `drive +member-add`.

The sample ships with the skill: 6 regions, 14 months, with a real overtake in it
(华东 leads at the start, 华南 by the end) — a race where nothing changes places is not a race.

## The one thing to check before a customer sees it

**Does the GIF animate inside Feishu, or does it arrive as an attachment?** Every
`docs +media-insert` call in this codebase and in the skills passes `--type file`
(`artifacts/tools.py:249`, `data-analysis/SKILL.md`). Whether the CLI also takes
`--type image`, and whether a doc plays a GIF inline, is not established anywhere in the
repo — so run `["docs", "+media-insert", "--help"]` on the box and look. If it only
attaches, the demo still works (open the attachment) but say "downloads and plays" rather
than "plays in the doc".

## Prerequisites

| | where |
|---|---|
| `HL_CODE_EXEC_ENABLED = "true"` | `hl-ops/orgs/sandbox/config.toml` — already set |
| "Code actions" toggle | the org's web console |
| `HL_CODE_EXEC_SKILL_HELPERS_ENABLED = "true"` | same file — **fleet default is off** |
| `HL_SKILLS_REF = "<merge SHA>"` | same file — with helpers on, write access to this repo is code execution in the org's sandbox |
| a CJK font in the image | `fonts-wqy-zenhei`, already in the Dockerfile. Without it Chinese labels draw as boxes and the skill says so in `notes` |

## Checking it without a deployment

```
python3 demo/verify_motion.py
```

Renders real GIFs and checks: three input shapes agree, `¥` and commas survive, a missing
month carries forward instead of collapsing to zero, colours are stable and the lead
actually changes, the reported frames/seconds/bytes match the file, a tight budget degrades
without shortening the animation, an impossible budget refuses instead of writing, the CJK
warning fires only when there is CJK, and a one-period race is refused by name.
