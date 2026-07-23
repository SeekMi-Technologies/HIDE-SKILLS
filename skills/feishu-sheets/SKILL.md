---
name: feishu-sheets
description: 电子表格 — create a spreadsheet, write rows, read cells back. Use for any 表格/spreadsheet/excel request that is NOT a 多维表格/Base.
scopes: ["sheets:spreadsheet", "sheets:spreadsheet:read", "drive:drive"]
commands: ["sheets +workbook-create", "sheets +table-put", "sheets +cells-get", "drive +member-add"]
---
表格 (spreadsheet) is NOT 多维表格 (Base) — a Base request goes to feishu-tables.

- Create: ["sheets", "+workbook-create", "--title", "<名字>"] → returns
  spreadsheet_token + url. Pre-fill in the same call with --values (untyped) or
  --sheets (typed) when you already have the data.
- HARD RULE — a bot-created spreadsheet is invisible to the requester until you
  share it, in the SAME turn as the create, before you report back:
  ["drive", "+member-add", "--token", "<spreadsheet_token>", "--type", "sheet",
   "--member-id", "<ou_requester,ou_others>", "--member-type", "openid",
   "--perm", "full_access"]
  --type sheet is REQUIRED with a bare token; --member-id takes up to 10 ids in ONE
  call. Then put the URL in your reply — never hand over a link they cannot open.
- Write rows: ["sheets", "+table-put", "--spreadsheet-token", "<tok>", "--sheets",
  "{\"sheets\":[{\"name\":\"Sheet1\",\"columns\":[\"列A\",\"列B\"],\"data\":[[\"a\",\"b\"]]}]}"]
  The {"sheets":[...]} envelope and each item's "name" are both required. Omit
  "dtypes" and every column writes as text — fine for plain data.
- Read: ["sheets", "+workbook-info", "--token", "<tok>"] for the sub-sheet list,
  ["sheets", "+cells-get", …] for values.

Traps:
- +table-put reads the workbook structure first, so it needs sheets:spreadsheet:read
  on top of sheets:spreadsheet. A 99991672 naming that scope is an ADMIN grant —
  report it, do not retry and do not ask anyone to log in.
- Ranges are sheet-prefixed (Sheet1!A1:B2). +cells-clear / +cells-batch-clear are
  irreversible and pause for confirmation.

For anything not covered above — charts, pivot tables, conditional formats, filters,
styling, formulas, imports/exports — read_skill("lark-sheets") for the full manual
before guessing; it is the source of truth this skill was distilled from.
