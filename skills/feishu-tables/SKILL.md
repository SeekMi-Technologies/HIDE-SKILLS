---
name: feishu-tables
description: 多维表格(Base) — 建库建表、字段、记录增删查、分享协作。Use for ANY 表格/多维表格/bitable/spreadsheet request or /base/ link — plain 电子表格 (sheets) is not enabled, Base covers it.
commands: ["base +base-create", "base +record-upsert", "base +record-search", "base +field-list", "drive +member-add"]
---
Commands (grammar verified against the pinned lark-cli; open_ids come from the
[Team directory] block):

- Create — ONE SHOT with the full schema (later field edits are high-risk writes
  that pause for confirmation; a complete --fields up front avoids every one):
  ["base", "+base-create", "--name", "<库名>", "--table-name", "<表名>", "--fields",
   "[{\"name\":\"标题\",\"type\":\"text\"},{\"name\":\"状态\",\"type\":\"select\",\"options\":[{\"name\":\"Todo\"},{\"name\":\"Done\"}]}]"]
  Field JSON is top-level {type, name, …} ONLY. Valid types: text, number, select,
  datetime, user, group_chat, link, formula, lookup, auto_number, attachment,
  location, checkbox, created_at/updated_at/created_by/updated_by. NEVER the old
  shapes (field_name / property / ui_type / numeric type) — the API rejects them.
  formula/lookup: read the guide first via
  read_skill("lark-base", "references/formula-field-guide.md").

- HARD RULE — a bot-created Base is invisible to the requester until shared:
  ["drive", "+member-add", "--token", "<base_token>", "--type", "bitable",
   "--member-id", "<ou_a,ou_b>", "--member-type", "openid", "--perm", "edit"]
  --type bitable is REQUIRED with a bare token (a full URL infers it). Then put the
  Base URL in your reply. If +base-create output carries permission_grant, report
  what it says. Batching 2+ ids in one call takes a different API path needing
  docs:permission.member; if that 99991672s, add people ONE call each — do not
  report failure, and never ask anyone to log in for it.

- Records: ["base", "+record-upsert", "--base-token", "<tok>", "--table-id", "<表名|tbl_>",
   "--json", "{\"标题\":\"Alice\",\"状态\":\"Todo\"}"] — a TOP-LEVEL field map, never
  wrapped in "fields". No --record-id = create; with = update that record.
  CellValue quick map: text → "x"; number → 12.5; select → "Todo";
  multi-select → ["A","B"]; datetime → "2026-03-24 10:00:00"; checkbox → true;
  user/link → [{"id":"ou_xxx"}] / [{"id":"rec_xxx"}] (resolve ids first, never guess).
  Batch: +record-batch-create / +record-batch-update.

- Read: +table-list / +field-list (ALWAYS +field-list before writing records —
  never write system/formula/lookup fields), +record-list / +record-search,
  +record-get. A pasted URL → ["base", "+url-resolve", "--url", "<url>"].

Identity & traps:
- A plain 电子表格 (sheets) request lands here too: that domain is not granted to this
  app, so build a Base instead — typed columns cover the same need. Only say sheets
  are unavailable if the person insists on an actual spreadsheet or an xlsx export.
- bot (default) covers the whole data plane: base/table/field/record create, read,
  update, delete, plus views. USER-ONLY: +title-resolve (find a Base by title as the
  speaker) and department-wide grants.
- Dashboards, forms, workflows and roles are NOT granted to this app. Those calls
  return 99991672 no matter how they are phrased — say the app does not have that
  permission and stop; do not retry or reword.
- There is NO +base-list. Destructive ops (+record-delete, +table-delete,
  +field-update — it is a full PUT) pause for confirmation; +field-get first.
- A bot 99991672 with no recovery hint means the resource was never shared with the
  bot — do not just retry; a 91403 means no access at all, same rule. A user-identity
  scope error DOES carry a recovery hint — follow it (or offer feishu_connect_user)
  rather than silently falling back to bot.

For anything not covered above — view configuration, advanced permissions, record
history, or any command whose behavior surprises you — read_skill("lark-base") for
the full manual before guessing; it is the source of truth this skill was distilled
from.
