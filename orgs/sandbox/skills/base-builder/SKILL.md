---
name: base-builder
description: Build a real Feishu 多维表格 from a data file — typed columns, select options, a kanban view, shared — in one pass. Read it for 建个表 / 多维表格 / bitable / 把这批数据入表 / 导入, or whenever rows have to land in Base. It compiles a checked call plan and the rows ride as files, never through the chat.
scopes: ["base:app:create", "base:table:create", "base:record:create", "base:record:read", "base:view:write_only", "drive:drive"]
commands: ["base +base-create", "base +record-batch-create", "base +view-create", "base +record-list", "drive +member-add"]
summary:
  zh: "把数据文件直接变成一个能用的多维表格——字段类型、选项、看板视图、共享，一次搞定"
  en: "Turn a data file into a working Feishu Base — typed fields, options, a kanban view, shared"
---
**This skill ships code, and reading it has already put that code in the sandbox.** The
package `skills.base_builder` exists for `run_python` in this conversation.

It closes a gap the `feishu-base` reference still describes as impossible ("no file
channel yet"): a file CAN now reach lark-cli. `read_attachment` / `stage_url` put it in
the sandbox, `stage_artifact` puts it where the CLI can see it, and a `--json` body takes
`@<that relative path>`. **So the rows never pass through this conversation** — 450 rows
cost about 2,000 characters of plan, and so do 10,000.

## The whole job, one program

```python
import skills.base_builder.build as bb

plan = bb.plan(path,                       # from read_attachment / stage_url, or a list of dicts
               name="销售线索库", table="客户",
               views=[{"name": "按阶段看板", "type": "kanban"}],
               queries=[{"what": "十万以上的大单",
                         "filter": [["金额", ">=", 100000]],
                         "sort": [{"field": "金额", "desc": True}]}])
print(plan.report())
```

`report()` prints the inferred schema, the numbered call plan, and what it had to coerce.
Nothing has run yet. **Read the schema before you execute** — if a column came out wrong,
re-run with `types={"金额": "number"}` rather than fixing it in Base afterwards, which is a
separate write per column.

Nothing to work from? The package ships `sample_crm.csv` beside it — say plainly that it
is sample data.

## Then execute the plan, in order

1. **Step 1 as printed** → keep `base_token` and the `url` from the reply.
2. **Each `rows_00N.json`** comes back in `run_python`'s `artifacts`. For each one:
   `stage_artifact("<that absolute path>")` → it returns `./hl-artifact-…`. Run the printed
   batch argv with `<base_token>` filled in and `--json "@./hl-artifact-…"`.
   The `@` path must be the RELATIVE one you were just handed; the CLI refuses an absolute one.
3. **The view calls**, then **the share call** — the share is REQUIRED, in this same turn.
   A bot-created Base is invisible to everyone else until it runs. Never add `--yes`.
4. Report the Base **url**, the row count, and anything in the plan's NOTES.

Substitute `<base_token>` everywhere it appears. Never invent one.

## What it decides for you, and why that is the point

- **Column types** from the values: select vs free text by how the values repeat AND how
  evenly long they are, number after stripping `¥` and thousands separators, datetime from
  seven layouts into the one spelling the CLI takes, checkbox from 是/否, multi-select on
  `、；|,/`, `user` from `ou_` ids.
- **The cell dialect per type** — a select writes the plain string although reads return a
  list; a checkbox writes a real boolean; a number writes bare; an empty cell writes `null`.
- **Columnar batch bodies**, chunked at 200 rows, written to files.
- **Every payload checked offline** against `grammar.json` before a call exists: an array
  of record objects, `field_name` / `ui_type` / `property`, `view_name` / `view_type`,
  object-shaped filter conditions, unknown types, duplicate columns, over-long option
  lists. Each refusal names the objection the API would have made.

## Rules

- **Do not print the rows.** They are in files on purpose. Printing them re-imports the
  whole table into this conversation and undoes the entire design.
- **One program.** Compile once, then execute. Re-running `plan()` to look at it again is
  a wasted turn — `report()` already said everything.
- **A failed call: paste the error, change ONE thing, retry once.** Then stop and report.
- **Say what was coerced.** The plan's NOTES line is not decoration; it carries it forward
  into your reply.

## What it will not do

- **关联 (link) columns.** Their cells are record ids read off the target table, and this
  compiler refuses to invent one. Build the second table, then read the ids and write the
  links per row (`references/base-advanced.md` in `feishu-base` has the resumable recipe).
- **formula / lookup columns.** Nobody here has verified their spec. Say the column has to
  be added by hand.
- **Fix an existing table.** This builds a new Base. Adding a column to a live one is one
  write per column through `feishu-base`.

## When NOT to use this

- A handful of rows someone dictated in chat → `+record-upsert` once each, via `feishu-base`.
- A question about data already in a Base → `feishu-base` (`+data-query` aggregates server-side).
- They wanted a picture or a summary, not a table → `one-pager` / `data-analysis`.
