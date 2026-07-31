# feishu-base — deep grammar per surface

Read the section the skill body routed you to; everything here runs as the bot and was
verified live. For a command's exact flags, run its `--help` (always allowed) before
composing it — `["base", "+record-batch-update", "--help"]`.

## Linked-record (关联) fields

- Create: `["base", "+field-create", "--base-token", "<tok>", "--table-id", "<会谈记录>",
  "--json", "{\"name\":\"关联客户\",\"type\":\"link\",\"link_table\":\"<tbl_ or name of 客户>\"}"]`
  `link_table` sits at the TOP level — a `property` wrapper or `type:18` is rejected.
  Add `"bidirectional":true` for 双向关联; the response's `bidirectional_link_field_id`
  is the auto-created column in the OTHER table.
- Rename that auto column with the SAME minimal shape, aimed at the other table:
  `["base", "+field-update", "--base-token", "<tok>", "--table-id", "<客户>", "--field-id",
  "<bidirectional_link_field_id>", "--json",
  "{\"name\":\"相关会谈\",\"type\":\"link\",\"link_table\":\"<会谈记录>\",\"bidirectional\":true}"]`
  The field handle is the `--field-id` FLAG; echoing `id` or `bidirectional_link_field_id`
  inside the JSON is rejected ("Unrecognized key(s)").
- Cell values are record ids FROM THE TARGET TABLE: `"关联客户":[{"id":"rec_xxx"}]` — read
  them off the target with +record-list/+record-search first, never construct one. The
  same value form works in +record-upsert, inside columnar +record-batch-create rows, and
  as a +record-batch-update patch.

## Bulk jobs (linking or updating tens of rows)

1. Count calls BEFORE writing: one +record-batch-create per 200 new rows (columnar); one
   +record-batch-update per DISTINCT value (one patch → every id in `record_id_list`,
   ≤200 — group rows sharing a value and write each group once); one +record-upsert per
   row only when every row differs. State the count in your plan.
2. Read every page first: `--limit` ≤200 with `--offset`, continue while the `Meta:` line
   says has_more. Grouping from a half-read table writes wrong data. NO `Meta:` line in
   the output means the page was truncated before its tail — re-read smaller (--limit 50)
   and project only needed columns with repeated `--field-id`.
3. Make the job resumable from the TABLE, not memory: remaining rows =
   `--filter-json '{"logic":"and","conditions":[["<target col>","empty"]]}'` — a
   continuation after any interruption costs two reads, not a re-exploration.
4. Report progress in numbers ("42/62 家已关联") and only what actually ran.

## Filtered and sorted reads

`+record-search` and `+record-list` both take:
- `--view-id <名称|vew_>` — read through an existing view's filter/sort.
- `--filter-json '{"logic":"and","conditions":[["阶段","intersects",["已成交"]]]}'` —
  overrides the view's filters. Each condition is a TUPLE `[field, operator, value]`
  (`{"field":…,"operator":…}` objects are rejected: "Expected array, received object").
  Value by field type: text → `"发布"` with `intersects`; number → `3.5` with `>=`;
  select/multi-select → `["Doing","Blocked"]`; user/created_by → `[{"id":"ou_xxx"}]`;
  group_chat → `[{"id":"oc_xxx"}]`; link → `[{"id":"rec_xxx"}]`; `empty` / `non_empty`
  take a 2-item tuple. Note `+record-search` still requires its own `--keyword`, so a
  pure filter read goes through `+record-list`.
- `--sort-json '[{"field":"金额","desc":true}]'` — order is priority, max 10.
- `--field-id <字段名>` (repeatable) — project only the columns you need.
- `--limit` (1–200, default 10) + `--offset` for paging; the Meta line reports `has_more`.

## data-query DSL, beyond a plain group-by

```
{"datasource":{"type":"table","table":{"tableName":"线索"}},
 "dimensions":[{"field_name":"阶段","alias":"stage"}],
 "measures":[{"field_name":"金额","aggregation":"sum","alias":"total"}],
 "filters":{"type":1,"conjunction":"and",
            "conditions":[{"field_name":"阶段","operator":"is","value":["已成交"]}]},
 "sort":[{"field_name":"total","order":"desc"}],
 "pagination":{"limit":10},
 "shaper":{"format":"flat"}}
```
`dimensions` and `measures` cannot both be empty. Use `tableId` instead of `tableName`
when an id is at hand. Results are `{alias: {value: …}}` rows — no record ids.

`filters` here is its own dialect, NOT the tuple form `--filter-json` takes: conditions are
objects `{field_name, operator, value}`, operators are `is / isNot / contains /
doesNotContain / isEmpty / isNotEmpty` (plus numeric/date comparisons), and a person or
chat value is a PLAIN STRING id array — `{"field_name":"负责人","operator":"is","value":["ou_xxx"]}`.
Passing `[{"id":…}]` here fails with 800004006 "failed to parse lite filter".

## Batch update

`+record-batch-update` applies ONE patch to MANY records:
`{"record_id_list":["rec…","rec…"],"patch":{"阶段":"已成交"}}` — identical values land on
every id, max 200 per call. It cannot write per-row different values; for those call
`+record-upsert` once per record. Read the ids from `+record-list` / `+record-search`
first — never construct one.

## Fields: create, update, formula, lookup

- `["base", "+field-create", "--base-token", "<tok>", "--table-id", "<表名>", "--json", "{\"name\":\"负责人\",\"type\":\"user\"}"]`
  Linked-record (关联) columns: create/rename/cell grammar is the "Linked-record
  (关联) fields" section at the top of this file.
- `+field-update` REPLACES the field definition: `+field-get` first, then send back every
  WRITABLE property you want kept (options, format) — and only those. Read-only keys the
  get returns (`id`, `bidirectional_link_field_id`) are rejected with
  "Unrecognized key(s)"; the field's handle goes in the `--field-id` flag, never the JSON.
- `formula` and `lookup` fields take a computed spec this skill has never verified. Say the
  column has to be added by hand; do not guess one.

## Base structure

`["base", "+base-block-list", "--base-token", "<tok>"]` lists everything inside a Base
(tables, docs, dashboards, workflows, folders) with their ids — useful when a person
describes a Base you have never read. `+base-get` returns the Base's own metadata;
`+base-copy` duplicates one.

## Not available — two different answers, never blur them

**The scope was never granted** (the app can do it; an admin has to turn it on). Name the
permission, say the admin was sent a grant link, stop: dashboards `base:dashboard:read`,
forms `base:form:read`, workflows `base:workflow:read`, roles and advanced permissions
`base:role:read`, one record's change history `base:history:read`.

**No file channel yet.** Attachment upload/download and importing a local .xlsx/.csv into
a Base both need a file on disk, and this bot has no way to receive one. Say the file
cannot be taken in yet — do not offer a workaround.

For any other Base surface none of this describes, say what you cannot do and stop.
