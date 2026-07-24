# feishu-base — advanced surfaces (rare)

Read this only when a request needs something the main skill does not cover. Everything
here runs as the bot. For a command's exact flags, run its `--help` (always allowed)
before composing it — `["base", "+record-history-list", "--help"]`.

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

`+record-batch-update` takes the same columnar shape as `+record-batch-create` plus the
record handle: `{"fields":["_record_id","阶段"],"rows":[["rec…","已成交"]]}`. Read the
`_record_id` values from `+record-list` / `+record-search` first — never construct one.

## Attachments

Attachment cells are NOT ordinary CellValues; use the dedicated commands:
- `["base", "+record-upload-attachment", "--base-token", "<tok>", "--table-id", "<表名>", "--record-id", "<rec…>", "--field-id", "<字段名>", "--file", "<cwd-relative path>"]`
- `+record-download-attachment` (by record, optionally one `--file-token`)
- `+record-remove-attachment` (by `file_token`)

## Record history and share links

- `["base", "+record-history-list", "--base-token", "<tok>", "--table-id", "<表名>", "--record-id", "<rec…>"]`
  — one record's change log. Not a whole-table audit; do not loop it over a table.
- `["base", "+record-share-link-create", …]` — share links for up to 100 records per call.

## Fields: create, update, formula, lookup

- `["base", "+field-create", "--base-token", "<tok>", "--table-id", "<表名>", "--json", "{\"name\":\"负责人\",\"type\":\"user\"}"]`
- `+field-update` is a FULL PUT — `+field-get` first and send back the complete shape, or
  you will silently drop the field's options/format.
- `formula` and `lookup` fields take a computed spec that is easy to get wrong and the CLI
  gates them behind a hidden `--i-have-read-guide` flag. Preview with `--dry-run`, and if
  the spec is not obvious, say the column needs to be added by hand rather than guessing.

## Base structure

`["base", "+base-block-list", "--base-token", "<tok>"]` lists everything inside a Base
(tables, docs, dashboards, workflows, folders) with their ids — useful when a person
describes a Base you have never read. `+base-get` returns the Base's own metadata;
`+base-copy` duplicates one.

## Still not covered

Dashboards, forms, workflows, roles and advanced permissions are not supported by this
app. If a request needs a Base surface none of this describes, say what you cannot do and
stop — never guess a command or ask anyone to log in.
