# one-pager — demo runbook

Operator notes for the CodeAct Phase 3 showcase. Not served to the model: this directory
holds no `SKILL.md`, and the loader only serves files that sit beside one.

## What it demonstrates

Phase 3 lets a skill ship `.py` helpers that are materialized into the sandbox when the
model reads the skill, and imported by `run_python` as `skills.<name>.<module>`. The
one-pager is what that buys:

1. **The skill ships the code, not a description of the code.** ~850 lines of renderer,
   palette, CJK font resolution, Metrics-v2 query building and dirty-data coercion.
   Before, the model wrote chart code inline every time: default grey matplotlib,
   `口口口` wherever a label was Chinese (DejaVu has no CJK glyphs and does not warn),
   two or three `run_python` roundtrips, a different-looking page each run.
2. **Prose rules became executable.** "Coerce dirty fields, say what you dropped" was a
   paragraph a model could skip. It is now a ledger that produces the footer by
   construction — and one that distinguishes a row it could not READ from a row that was
   simply EMPTY for one panel.
3. **The data never passes through the context window.** `lf.daily()` calls
   `hide.langfuse.queryMetrics` from inside the sandbox and returns into a variable.

## Prerequisites

| | where | note |
|---|---|---|
| `HL_CODE_EXEC_ENABLED = "true"` | `hl-ops/orgs/sandbox/config.toml` | already set |
| "Code actions" toggle | the org's web console | both halves gate the helper hook |
| `HL_CODE_EXEC_SKILL_HELPERS_ENABLED = "true"` | `hl-ops/orgs/sandbox/config.toml` | **fleet default is off** — the Phase 3 flag |
| `HL_SKILLS_REF = "<merge SHA>"` | same file | unpinned only warns, but with helpers on, write access to this repo is code execution inside the org's sandbox. The pin is the control. |
| `HL_CODE_EXEC_BRIDGE_ENABLED = "true"` | same file | **Route A only.** Not set anywhere in hl-ops today and the code default is `False`; confirm before promising a live-Langfuse demo. |
| langfuse integration enabled | the org's web console | Route A only |
| a node with Landlock | `node_labels = ["landlock=true"]` | already pinned; without it `run_python` never mounts |

Route B (a CSV, or the shipped sample) needs none of the last three.

## The demo

Ask, in Feishu, in one sentence:

> 给我这周机器人表现的一页纸

Expected turn: `load_toolkit("langfuse")` → `read_skill("one-pager")` → **one**
`run_python` → `stage_artifact` → `docs +create` + `docs +media-insert` behind the
ordinary approval card. In the core log: `code_exec: ok tenant=sandbox … artifacts=1`.

Without Langfuse, send any CSV and ask for 一页纸 — the same skill, Route B.

## If the helper line is missing from the read_skill result

The result should end with "This skill ships code helpers, materialized in the sandbox as
the `skills.one_pager` package". If it does not, check the gates in this order — they are
consulted in exactly this sequence:

1. `code_exec_skill_helpers_enabled` (fleet flag)
2. `provider_enabled(code_exec)` — fleet kill switch AND the org's console row
3. `runner.confined()` — the sandbox verdict; a node without Landlock gets no tool at all

A skill disabled in the console has its package pruned at tool assembly, synchronously,
before the turn's tools go out. That is the same mechanism, working as intended.

## A/B, for the pitch

Same sentence, twice, with `HL_CODE_EXEC_SKILL_HELPERS_ENABLED` off and then on. Capture
both replies. Off, the model has to write the chart itself and the skill body tells it to
import a package that is not there — so the honest comparison is against the
`data-analysis` skill, which is what it would have used before this existed. Count
`run_python` calls and look at the two images side by side.

## Checking the skill without a deployment

```
python3 demo/verify_one_pager.py
```

Stages the skill exactly as the sandbox does and exercises the dirty-data contract, the
font branch both ways, four shapes of Langfuse server, the no-bridge path, and a real
render of each route. Needs matplotlib and numpy; talks to nothing.

Two things it cannot prove on a machine without a CJK font installed: that the glyphs
actually draw, and that the image's `fonts-wqy-zenhei` is the face picked. Render inside
the app image for those.
