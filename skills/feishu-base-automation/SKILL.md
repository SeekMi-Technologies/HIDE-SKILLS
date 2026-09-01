---
name: feishu-base-automation
description: Wire a Feishu Base (多维表格) to an automation — a new record starts a run, the platform builds BOTH ends (the automation and the Base-side workflow). Use when a person pastes a /base/ link or names a 表格 and wants new records to notify or trigger anything (新增记录就通知/推送/处理).
scopes: ["base:workflow:create", "base:workflow:read", "base:workflow:update", "base:workflow:write", "base:workflow:delete"]
commands: ["base +table-list", "base +field-list"]
summary:
  zh: "多维表格接自动化：新增一条记录就自动跑——没人碰密钥，没人进表格配置"
  en: "Connect a Base table to an automation — a new record starts a run; no keys, no Base UI"
---
THE SHAPE: the person says which table and what should happen. After they confirm
the card, the PLATFORM creates and enables the「新增记录 → HTTP」workflow inside
their Base, pointed at the automation's own address and key. Nobody pastes an
address, nobody sees a key, nobody opens the Base UI — so never offer the webhook
address and never send anyone to configure anything in the Base.

THE TRIGGER:
`{"type": "feishu_base", "base": "<link or token, VERBATIM>", "table": "<name or
tbl id>", "watched_field": "<field name>"}`
- `base`: the pasted link exactly as pasted — the platform resolves it, wiki-hosted
  links included. Do not extract tokens yourself.
- `table`: the table the person named. Several tables and they didn't say?
  ["base", "+table-list", "--base-token", "<tok>"] and ask.
- `watched_field` is REQUIRED and load-bearing: the workflow fires when a new
  record has THIS field filled, so a field that stays empty is an automation that
  never fires. Read the fields first — ["base", "+field-list", "--base-token",
  "<tok>", "--table-id", "<表名>"] — and pick the column whose being filled marks
  a record as real (usually the main/title column). Your choice lands on the card
  for the person to check; ask when no column is an obvious spine.

WHAT A DELIVERY CARRIES → what instructions can use:
`{"base_token": …, "table_id": …, "record_id": …, "<watched field name>": <value>}`
Only those four keys. Instructions that need MORE fields must SAY the run reads
the full record itself — it has base_token/table_id/record_id in the delivery and
the base read commands (the feishu-base skill). A renamed watched field keeps its
creation-time key in deliveries; the value still arrives.

PREREQUISITES — the two refusals and their fixes, in the platform's own words:
- Missing `base:workflow:*` scopes → the refusal carries a ready grant link; hand
  it to an admin, then create again.
- The bot must be a COLLABORATOR on that one Base — the app grant does not cover
  the document. The person adds the bot (or a group chat it is in) through the
  Base's share dialog, then asks again.

LIFECYCLE:
- Cancelling the automation disables the Base-side workflow with it. The disabled
  row stays visible in the Base's automation list (titled "Ola · …"); a human can
  delete it there — the platform deliberately cannot.
- Two automations on the same table are two independent workflows — fine when the
  person wants two behaviours, wasteful as duplicates of one request.
- 记录更新 (a record being CHANGED) is not wired yet: this trigger fires on NEW
  records only. Say so plainly when someone asks for update-triggered runs.
