# base-builder — demo runbook

Operator notes for the CodeAct Phase 3 showcase. Not served to the model: this directory
holds no `SKILL.md`, so the loader never attaches these files to a skill.

## What it demonstrates

Not a prettier output — a capability the catalog currently declares impossible. From
`skills/feishu-base/references/base-advanced.md`:

> **No file channel yet.** Attachment upload/download and importing a local .xlsx/.csv into
> a Base both need a file on disk, and this bot has no way to receive one.

With code_exec that is no longer true, and this skill is the proof:

```
stage_url / read_attachment  ->  sandbox workspace
run_python                   ->  rows_001.json … (columnar, ≤200 rows each)
stage_artifact               ->  ./hl-artifact-…  (lark-cli's own cwd)
feishu_cli --json @./hl-…    ->  a live 多维表格
```

Three claims, each measured by `demo/verify_base_builder.py`:

1. **The rows never pass through the conversation.** 450 rows compile to 14,771 bytes on
   disk and 2,011 characters of plan. 10,000 rows cost the same 2,000 characters.
2. **The payloads are right the first time.** Building a Base by hand means the columnar
   batch shape (an array of record objects is rejected), `{name, type}` field JSON
   (`field_name` / `ui_type` / `property` rejected), `{name, type}` view JSON (`view_name`
   fails 800010701), tuple filter conditions (objects fail "Expected array, received
   object"), 200 rows per call, and a different cell dialect per column type. All of it is
   `grammar.json` plus a validator that refuses 15 known-bad payloads offline, each naming
   the objection the API would have made.
3. **The schema is the one a person would have chosen.** On the shipped sample: 阶段 →
   select with 6 options, 金额 → number (after `¥` and commas), 下次跟进 → datetime across
   three input layouts, 标签 → multi-select on `、`, 已签约 → checkbox from 是/否, 备注 →
   text, because its values repeat but are unevenly long.

The A/B is countable: run the same ask with `HL_CODE_EXEC_SKILL_HELPERS_ENABLED` off and
count the rejected calls and the turns.

## Prerequisites

| | where | note |
|---|---|---|
| `HL_CODE_EXEC_ENABLED = "true"` | `hl-ops/orgs/sandbox/config.toml` | already set |
| "Code actions" toggle | the org's web console | both halves gate the helper hook |
| `HL_CODE_EXEC_SKILL_HELPERS_ENABLED = "true"` | `hl-ops/orgs/sandbox/config.toml` | **fleet default is off** — the Phase 3 flag |
| `HL_SKILLS_REF = "<merge SHA>"` | same file | with helpers on, write access to this repo is code execution inside the org's sandbox |
| `HL_CODE_EXEC_URL_ALLOW_HOSTS = "raw.githubusercontent.com"` | same file | only for the start-from-a-link demo. EMPTY means `stage_url` is not mounted at all — that is the fail-closed default, and the list is what stops it being an SSRF primitive pointed at the org's egress |
| Base scopes granted | Feishu admin console | `base:app:create`, `base:table:create`, `base:record:create`, `base:view:write_only`, `drive:drive`. A missing one returns 99991672 with a grant deep-link |
| a node with Landlock | `node_labels = ["landlock=true"]` | already pinned |

## The demo

Two openings. The second is the one that uses the download handle.

> 这是我们的客户名单，建个多维表格   （+ a CSV attachment）

> 把 https://raw.githubusercontent.com/<org>/<repo>/main/customers.csv 建成一个多维表格，按阶段做成看板

Expected turn: `read_skill("base-builder")` → `stage_url` or `read_attachment` → **one**
`run_python` (prints the schema + the plan) → `stage_artifact` per chunk → `+base-create`,
`+record-batch-create` per chunk, `+view-create`, `drive +member-add` → report the Base url.

What to point at while it runs: the SCHEMA block (types chosen from the data), the line
`0 rows through this conversation`, and the fact that no call is retried.

## If it goes wrong

- **No helper line in the `read_skill` result** → the gates, in the order they are
  consulted: `code_exec_skill_helpers_enabled`, then `provider_enabled(code_exec)` (fleet
  switch AND the org's console row), then `runner.confined()` (no Landlock, no tool).
- **`stage_url` missing** → `code_exec_url_allow_hosts` is empty, so it was never mounted.
- **99991672** → an app scope was never granted; the reply carries the admin grant link.
- **The CLI refuses an `@` path** → an absolute one was passed. It must be the relative
  `./hl-artifact-…` that `stage_artifact` returned.
- **The Base is invisible to the person who asked** → the `drive +member-add` step did not
  run. It is the last step of the plan for exactly this reason.

## Checking it without a deployment

```
python3 demo/verify_base_builder.py
```

Stages the package the way the sandbox does and checks inference, the cell dialect, 200-row
chunking, 15 offline refusals, plan hygiene (no rows in argv, `@file` only, relative paths,
share step present) and the dirty-input paths. Talks to nothing; needs no dependencies.

Not provable here: that lark-cli accepts every argv as written. The grammar came from
`skills/feishu-base/`, which states it was verified live against the pinned CLI 1.0.63 —
worth one `--help` spot-check on the box before a customer sees it.
