# feishu-base — advanced surfaces (rare)

Read this only when a request needs something the main skill does not cover. Everything
here runs as the bot. For a command's exact flags, run its `--help` (always allowed)
before composing it — `["base", "+record-batch-update", "--help"]`.

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
- `+field-update` is a FULL PUT — `+field-get` first and send back the complete shape, or
  you will silently drop the field's options/format.
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

For any other Base surface none of this describes, say what you cannot do and stop —
never guess a command or ask anyone to log in.
