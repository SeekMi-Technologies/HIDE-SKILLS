---
name: feishu-base
description: 多维表格(Base) — 建库建表、写/改/查记录、分组统计、看板视图、分享给人。Use for ANY 表格/多维表格/bitable/spreadsheet request or /base/ link — plain 电子表格 (sheets) is not enabled, Base covers it.
scopes: ["base:app:create", "base:table:read", "base:record:create", "base:record:update", "drive:drive"]
commands: ["base +base-create", "base +table-list", "base +field-list", "base +record-upsert", "base +record-batch-create", "base +record-search", "base +record-list", "base +data-query", "base +view-create", "base +url-resolve", "drive +member-add"]
---
Every command below runs as the BOT and was verified live against this CLI. Values go
through flags only; `--table-id` accepts a table NAME as well as a `tbl…` id.

FIND THE BASE FIRST — never invent a token:
- A pasted link ⇒ ["base", "+url-resolve", "--url", "<url>"] → `base_token`.
- "有哪些多维表格 / 我们建过什么表" ⇒ ["drive", "files", "list"] and keep the
  `type: "bitable"` entries — their `token` IS the base_token. This is a Drive question,
  not a Base one (`base` has no list command), and it answers what the BOT can see, so
  say that rather than claiming it is everything.
- A title you can match against that list ⇒ use its token. Still ambiguous ⇒ ASK.
  (`+title-resolve` is user-identity-only; never call it, never offer a login for it.)
- Nothing exists yet ⇒ create one (below).

CREATE — one shot, whole schema (adding fields later is a separate write per column):
  ["base", "+base-create", "--name", "<库名>", "--table-name", "<表名>", "--fields",
   "[{\"name\":\"客户名\",\"type\":\"text\"},{\"name\":\"阶段\",\"type\":\"select\",\"options\":[{\"name\":\"新线索\"},{\"name\":\"已成交\"}]},{\"name\":\"金额\",\"type\":\"number\"},{\"name\":\"下次跟进\",\"type\":\"datetime\"}]"]
  Field JSON is top-level `{name, type, …}` — NEVER `field_name` / `ui_type` / `property`.
  Types: text, number, select, multi_select, datetime, user, group_chat, link, checkbox,
  attachment, location, auto_number, created_at/updated_at/created_by/updated_by.
  Returns `base_token` + the Base `url`; report the url.

SHARE — HARD RULE, in the SAME turn as the create, before you report back:
  ["drive", "+member-add", "--token", "<base_token>", "--type", "bitable",
   "--member-id", "<ou_requester,ou_others>", "--member-type", "openid", "--perm", "edit"]
  A bot-created Base is invisible to everyone else — the CLI itself warns "created with
  bot identity … auto-grant was skipped". `--type bitable` is REQUIRED with a bare token.
  This is high-risk-write: the platform handles the confirmation, so issue the command and
  never add `--yes` yourself. If batching 2+ ids 99991672s (that path needs
  docs:permission.member), repeat the call ONE person at a time — never ask anyone to log in.

READ:
- ["base", "+table-list", "--base-token", "<tok>"] → `{id, name}` per table.
- ["base", "+field-list", "--base-token", "<tok>", "--table-id", "<表名|tbl_>"] — ALWAYS
  before writing. Fields come back as `{id, name, type, style, options}`; never write
  system, formula or lookup fields.
- ["base", "+record-list", "--base-token", "<tok>", "--table-id", "<表名>"] — a markdown
  table with a `_record_id` column (that column is the record handle, not a field).
- ["base", "+record-search", "--base-token", "<tok>", "--table-id", "<表名>", "--keyword",
  "<词>", "--search-field", "<字段名>"] — repeat `--search-field` for more columns.
  `--limit` defaults to 10 (max 200); `--filter-json` / `--sort-json` for precise reads.

WRITE:
- One record: ["base", "+record-upsert", "--base-token", "<tok>", "--table-id", "<表名>",
  "--json", "{\"客户名\":\"张三科技\",\"阶段\":\"新线索\",\"金额\":120000,\"下次跟进\":\"2026-07-28 10:00:00\"}"]
  A TOP-LEVEL field map, never wrapped in "fields". No `--record-id` = create; with it = update.
- Many records: ["base", "+record-batch-create", …, "--json",
  "{\"fields\":[\"客户名\",\"阶段\"],\"rows\":[[\"李四贸易\",\"跟进中\"],[\"王五制造\",\"已成交\"]]}"]
  TRAP: batch JSON is COLUMNAR — a `fields` order plus `rows` arrays. An array of record
  objects is rejected. `null` empties a cell. Max 200 rows per call.
- Cell values: text "x"; number 12.5; select "已成交" (write the plain string even though
  reads return `["已成交"]`); multi-select ["A","B"]; datetime "2026-07-28 10:00:00";
  checkbox true; user/link [{"id":"ou_xxx"}] / [{"id":"rec_xxx"}] — resolve every id from
  the [Team directory] first; a wrong one fails loudly with 800030405 not_found.

WHOSE ROWS ARE THESE — filter on a person field, never read the table and eyeball it.
A CRM-style table usually carries an owner column (`{"name":"负责人","type":"user"}`), and
"我的客户 / 我要跟进谁" means the SPEAKER's rows. The two commands take DIFFERENT filter
dialects — this is the easiest thing here to get wrong:
- ["base", "+record-list", …, "--filter-json",
   "{\"logic\":\"and\",\"conditions\":[[\"负责人\",\"intersects\",[{\"id\":\"ou_xxx\"}]]]}"]
  Conditions are TUPLES `[field, operator, value]`; a person value is an OBJECT array.
  Operators: == != > >= < <= intersects disjoint empty non_empty. (`+record-search` still
  wants its `--keyword`; use `+record-list` for a pure filter.)
- Inside `+data-query`'s `filters`, the same person is a PLAIN STRING id:
  `{"field_name":"负责人","operator":"is","value":["ou_xxx"]}` — objects there fail with
  800004006 "failed to parse lite filter".
Reading someone else's rows is a real request ("老王手上有哪些客户") — filter by THEIR
open_id, and only when the person asking is entitled to it.

COUNT / SUM / GROUP — use the server, never pull the whole table and add it up yourself:
  ["base", "+data-query", "--base-token", "<tok>", "--dsl",
   "{\"datasource\":{\"type\":\"table\",\"table\":{\"tableName\":\"<表名>\"}},\"dimensions\":[{\"field_name\":\"阶段\",\"alias\":\"stage\"}],\"measures\":[{\"field_name\":\"金额\",\"aggregation\":\"sum\",\"alias\":\"total\"}],\"shaper\":{\"format\":\"flat\"}}"]
  aggregation: sum | avg | min | max | count | distinct_count. Add `filters` / `sort` /
  `pagination` for filtered or Top-N answers (see references/base-advanced.md). Rows come
  back grouped, WITHOUT record ids — use the read commands when the person needs rows.

VIEWS — a kanban is the fastest way to make a table feel like a board:
  ["base", "+view-create", "--base-token", "<tok>", "--table-id", "<表名>", "--json",
   "{\"name\":\"按阶段看板\",\"type\":\"kanban\"}"]
  TRAP: the keys are `name` / `type` — `view_name` / `view_type` are rejected (800010701).
  type: grid | kanban | gallery | calendar | gantt. A kanban auto-groups by the table's
  select field. `+view-list` to see what exists.

Traps and boundaries:
- Destructive commands (+record-delete, +table-delete, +field-update — a full PUT) pause
  for the user's confirmation; run them anyway when asked, never add `--yes`, and never
  report a change you did not actually execute.
- 99991672 = a missing APP scope: name the permission, say the admin was sent a grant
  link, stop. A "no permission" without 99991672 = this Base was never shared with the
  bot — ask for it to be shared. Neither is a reason to switch identity or send a login.
- 仪表盘 (dashboards), 表单 (forms), 流程 (workflows), 角色/高级权限 are NOT supported by
  this app — say so plainly and stop; do not call them, do not reword the request.
- A plain 电子表格 (sheets) request lands here too: that domain is not enabled, so build a
  Base — typed columns cover the same need. Only say spreadsheets are unavailable if the
  person insists on an actual .xlsx.

Attachments, record history, share links, formula/lookup columns, view filters and sorts
are in references/base-advanced.md — read it only when a request needs one. For a Base
need neither file covers, say what you cannot do and stop; never guess a command.
