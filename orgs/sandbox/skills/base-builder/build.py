"""Compile a dataset into a complete, validated lark-cli plan for building a live Base.

    import skills.base_builder.build as bb
    plan = bb.plan("data.csv", name="销售线索库", table="客户")
    print(plan.report())

WHAT THIS IS FOR. Building a real 多维表格 by hand is a long sequence of brittle payloads
with documented traps: batch JSON is COLUMNAR and an array of record objects is rejected;
field JSON is `{name, type}` and `field_name` / `ui_type` / `property` are rejected; view
JSON is `{name, type}` and `view_name` fails with 800010701; `--filter-json` conditions are
TUPLES and objects fail with "Expected array, received object"; 200 rows per call. Each of
those is a failed call and a wasted turn. They are encoded once, here, and checked OFFLINE
against `grammar.json` before anything runs.

THE ROWS NEVER PASS THROUGH THE CONVERSATION. Row payloads are written to FILES in the
call directory, so they come back in `run_python`'s `artifacts`. `stage_artifact` puts each
one where lark-cli can see it and hands back a RELATIVE path, and the CLI takes a JSON body
as `@<that path>`. Ten thousand rows cost the same context as ten. That closes the gap
`feishu-base/references/base-advanced.md` still describes as "no file channel yet".

WHAT IT REFUSES TO DO. Link (关联) cells take record ids read off the target table; this
compiler will not invent one. Formula and lookup columns take a spec nobody here has
verified. Both come back as a stated limitation rather than a guess.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from . import infer

_HERE = Path(__file__).resolve().parent
_DATETIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")


class GrammarError(ValueError):
    """A payload the CLI would reject, caught before the call is made."""


def _grammar() -> dict:
    with open(_HERE / "grammar.json", encoding="utf-8") as fh:
        return json.load(fh)


G = _grammar()
LIMITS = G["limits"]


def _json(value) -> str:
    """The exact string that goes after a --json / --fields flag."""
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


# --------------------------------------------------------------------------- validators
def validate_fields(fields: list[dict]) -> list[dict]:
    seen = set()
    for field in fields:
        bad = [k for k in field if k in G["rejected_keys"]["field"]]
        if bad:
            raise GrammarError(f"{bad} in field JSON — {G['rejections']['field_name_key']}")
        if "name" not in field or "type" not in field:
            raise GrammarError(f"every field needs name and type — got {sorted(field)}")
        if field["type"] not in G["field_types"]:
            raise GrammarError(f"{field['type']!r} is not a Base field type "
                               f"(have: {', '.join(G['field_types'])})")
        if field["name"] in seen:
            raise GrammarError(f"duplicate column name {field['name']!r}")
        seen.add(field["name"])
        options = field.get("options") or []
        if options and field["type"] not in {"select", "multi_select"}:
            raise GrammarError(f"{field['name']!r} is {field['type']} and cannot carry options")
        if len(options) > LIMITS["select_options"]:
            raise GrammarError(f"{field['name']!r} has {len(options)} options, over the "
                               f"{LIMITS['select_options']} this compiler allows")
        if "link_table" in field and field["type"] != "link":
            raise GrammarError("link_table belongs to a link field — "
                               + G["rejections"]["link_property_wrapper"])
    return fields


def validate_records(payload, types: dict | None = None) -> dict:
    """The columnar batch body, checked the way the API checks it."""
    if isinstance(payload, list):
        raise GrammarError(G["rejections"]["records_as_object_array"])
    if not isinstance(payload, dict) or set(payload) != {"fields", "rows"}:
        got = sorted(payload) if isinstance(payload, dict) else type(payload).__name__
        raise GrammarError("batch JSON is exactly {\"fields\": [...], \"rows\": [[...]]} — "
                           f"got {got}")
    names, rows = payload["fields"], payload["rows"]
    if not isinstance(names, list) or not all(isinstance(n, str) for n in names):
        raise GrammarError("'fields' is the column ORDER: a list of column names")
    if len(rows) > LIMITS["rows_per_batch"]:
        raise GrammarError(f"{len(rows)} rows in one call, over the API's "
                           f"{LIMITS['rows_per_batch']} — split into chunks")
    kinds = types or {}
    for i, row in enumerate(rows):
        if not isinstance(row, list):
            raise GrammarError(f"row {i} is {type(row).__name__}, not a list — "
                               + G["rejections"]["records_as_object_array"])
        if len(row) != len(names):
            raise GrammarError(f"row {i} has {len(row)} cells for {len(names)} columns")
        for name, value in zip(names, row, strict=True):
            _validate_cell(name, value, kinds.get(name), i)
    return payload


def _validate_cell(name: str, value, kind: str | None, row: int) -> None:
    if value is None or kind is None:
        return
    where = f"row {row}, column {name!r}"
    if kind == "number" and (isinstance(value, bool)
                             or not isinstance(value, (int, float))):
        raise GrammarError(f"{where}: a number cell takes a bare number, got {value!r}")
    if kind == "checkbox" and not isinstance(value, bool):
        raise GrammarError(f"{where}: a checkbox cell takes true/false, got {value!r}")
    if kind == "datetime" and not (isinstance(value, str) and _DATETIME_RE.match(value)):
        raise GrammarError(f"{where}: a datetime cell takes \"YYYY-MM-DD HH:MM:SS\", "
                           f"got {value!r}")
    if kind == "select" and not isinstance(value, str):
        raise GrammarError(f"{where}: a select cell takes the plain option string "
                           f"(reads return a list, writes do not), got {value!r}")
    if kind == "multi_select" and not (isinstance(value, list)
                                       and all(isinstance(v, str) for v in value)):
        raise GrammarError(f"{where}: a multi-select cell takes an array of strings")
    if kind in {"user", "link"} and not (isinstance(value, list) and all(
            isinstance(v, dict) and "id" in v for v in value)):
        raise GrammarError(f"{where}: a {kind} cell takes [{{\"id\": \"...\"}}]")


def validate_view(payload: dict) -> dict:
    bad = [k for k in payload if k in G["rejected_keys"]["view"]]
    if bad:
        raise GrammarError(f"{bad} in view JSON — {G['rejections']['view_name_key']}")
    if set(payload) - {"name", "type"}:
        raise GrammarError(f"a view takes name and type only — got {sorted(payload)}")
    if payload.get("type") not in G["view_types"]:
        raise GrammarError(f"{payload.get('type')!r} is not a view type "
                           f"(have: {', '.join(G['view_types'])})")
    return payload


def validate_filter(conditions) -> list:
    if not isinstance(conditions, list):
        raise GrammarError("--filter-json conditions are a list of tuples")
    for condition in conditions:
        if isinstance(condition, dict):
            raise GrammarError(G["rejections"]["filter_condition_object"])
        if not isinstance(condition, (list, tuple)) or not 2 <= len(condition) <= 3:
            raise GrammarError("each condition is [field, operator] or [field, operator, value]")
        if condition[1] not in G["filter_operators"]:
            raise GrammarError(f"{condition[1]!r} is not a filter operator "
                               f"(have: {', '.join(G['filter_operators'])})")
    return list(conditions)


# -------------------------------------------------------------------------------- plan
class Plan:
    """A validated build, ready to execute. Nothing here has run."""

    def __init__(self, name: str, table: str, schema: list[dict], rows: int,
                 chunks: list[dict], steps: list[dict], queries: list[dict],
                 ledger: infer.Ledger) -> None:
        self.name, self.table = name, table
        self.schema, self.rows, self.chunks = schema, rows, chunks
        self.steps, self.queries, self.ledger = steps, queries, ledger

    @property
    def payloads(self) -> list[str]:
        return [chunk["path"] for chunk in self.chunks]

    def report(self) -> str:
        out = [f"BASE  {self.name} / table {self.table}",
               f"SCHEMA  {len(self.schema)} columns, {self.rows} rows"]
        for field in self.schema:
            options = field.get("options") or []
            tail = field["why"]
            if options:
                tail = " · ".join(o["name"] for o in options[:6])
                if len(options) > 6:
                    tail += f" … +{len(options) - 6}"
            out.append(f"  {field['name']:<14} {field['type']:<13} {tail}")

        out.append("")
        out.append(f"PLAN  {len(self.steps)} calls, {self.rows} rows, "
                   f"0 rows through this conversation")
        for step in self.steps:
            out.append(f"  {step['n']}. {step['what']}")
            if step.get("needs"):
                out.append(f"     {step['needs']}")
            out.append("     " + _json(step["argv"]))
        if self.queries:
            out.append("")
            out.append("SAVED QUERIES  (reads — run when someone asks, do not run now)")
            for query in self.queries:
                out.append(f"  {query['what']}")
                out.append("     " + _json(query["argv"]))
        out.append("")
        out.append("NOTES  " + self.ledger.summary())
        out.append(f"CHECKED  offline against grammar.json (lark-cli "
                   f"{G['cli_version_verified']}): columnar rows, "
                   f"≤{LIMITS['rows_per_batch']}/call, field keys name/type, view keys "
                   f"name/type, tuple filters, cell dialect per column type.")
        return "\n".join(out)


def plan(source, *, name: str, table: str, types: dict | None = None,
         views: list[dict] | None = None, queries: list[dict] | None = None,
         out_dir: str = ".", share_with: str = "<ou_of_the_requester>") -> Plan:
    """Compile `source` (a CSV/JSON path, or a list of dicts) into a Plan.

    `types` overrides inference for named columns. `views` are {name, type} dicts.
    `queries` are {what, filter, sort?} — emitted as ready-to-run READ commands, because
    this CLI creates a view by name and type only; a saved filter is a read, not a view.
    """
    led = infer.Ledger()
    if isinstance(source, str):
        header, rows = infer.load(source, led)
    else:
        rows = [dict(r) for r in source]
        header = []
        for row in rows:
            for key in row:
                if key not in header:
                    header.append(key)
        led.rows = len(rows)

    if not rows:
        raise ValueError("there are no rows to build a table from")

    # ---- schema
    schema: list[dict] = []
    for column in header:
        forced = (types or {}).get(column)
        found = ({"type": forced, "why": "set by the caller", "options": []} if forced
                 else infer.column_type([r.get(column) for r in rows], column))
        field = {"name": column, "type": found["type"]}
        if found.get("options"):
            field["options"] = [{"name": option} for option in found["options"]]
        field["why"] = found["why"]
        if found.get("unreadable"):
            led.count(f"{column}: unreadable date", found["unreadable"])
        schema.append(field)
    validate_fields([{k: v for k, v in f.items() if k != "why"} for f in schema])
    kinds = {f["name"]: f["type"] for f in schema}

    # ---- rows, as files
    names = [f["name"] for f in schema]
    table_rows, empties = [], 0
    for row in rows:
        cells = [infer.cell(row.get(n), kinds[n], led, n) for n in names]
        empties += sum(1 for c in cells if c is None)
        table_rows.append(cells)
    if empties:
        # Empty is not an error -- `null` empties a cell on purpose. It is said out loud
        # because "36 rows loaded" and "36 complete rows" are different claims.
        led.note(f"{empties} of {len(rows) * len(names)} cells were empty and go in as null")

    chunks: list[dict] = []
    size = LIMITS["rows_per_batch"]
    out = Path(out_dir)
    for index in range(0, len(table_rows), size):
        payload = {"fields": names, "rows": table_rows[index:index + size]}
        validate_records(payload, kinds)
        path = out / f"rows_{len(chunks) + 1:03d}.json"
        path.write_text(_json(payload), encoding="utf-8")
        chunks.append({"path": str(path.resolve()), "file": path.name,
                       "rows": len(payload["rows"])})

    # ---- calls
    fields_json = _json([{k: v for k, v in f.items() if k != "why"} for f in schema])
    steps = [{"n": 1, "what": f"create the Base and its first table ({len(schema)} typed columns)",
              "needs": "keep base_token and the url from the reply",
              "argv": ["base", "+base-create", "--name", name, "--table-name", table,
                       "--fields", fields_json]}]
    n = 2
    for chunk in chunks:
        steps.append({
            "n": n,
            "what": f"{chunk['rows']} rows from {chunk['file']}",
            "needs": f"stage_artifact('{chunk['path']}') first — use the ./hl-artifact-… "
                     f"path it returns, NOT this one (the CLI refuses an absolute @path)",
            "argv": ["base", "+record-batch-create", "--base-token", "<base_token>",
                     "--table-id", table, "--json", "@<staged path>"]})
        n += 1

    for view in views or []:
        validate_view(view)
        steps.append({"n": n, "what": f"{view['type']} view “{view['name']}”", "needs": "",
                      "argv": ["base", "+view-create", "--base-token", "<base_token>",
                               "--table-id", table, "--json", _json(view)]})
        n += 1

    steps.append({
        "n": n,
        "what": "share it — REQUIRED, in the same turn, before you report back",
        "needs": "a bot-created Base is invisible to everyone else until this runs",
        "argv": ["drive", "+member-add", "--token", "<base_token>", "--type", "bitable",
                 "--member-id", share_with, "--member-type", "openid", "--perm", "edit"]})

    emitted: list[dict] = []
    for query in queries or []:
        conditions = validate_filter(query.get("filter") or [])
        argv = ["base", "+record-list", "--base-token", "<base_token>", "--table-id", table,
                "--filter-json", _json({"logic": query.get("logic", "and"),
                                        "conditions": conditions})]
        if query.get("sort"):
            argv += ["--sort-json", _json(query["sort"][:LIMITS["sort_keys"]])]
        emitted.append({"what": query.get("what") or "filtered read", "argv": argv})

    if views and any(v["type"] == "kanban" for v in views) and not any(
            f["type"] == "select" for f in schema):
        led.note("a kanban groups by a select column and this table has none — "
                 "it will render as one column")
    return Plan(name, table, schema, len(rows), chunks, steps, emitted, led)
