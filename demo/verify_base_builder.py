#!/usr/bin/env python3
"""Offline checks for the `base-builder` skill. Talks to nothing.

    python3 demo/verify_base_builder.py

Stages the skill the way the sandbox does, then proves the three claims the skill makes:
the schema it infers is the one a person would have chosen, the payloads it writes are in
the CLI's exact dialect, and its validator refuses precisely what the API refuses -- each
rejection quoted from `skills/feishu-base/` where it was verified live.
"""
from __future__ import annotations

import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent / "orgs" / "sandbox" / "skills" / "base-builder"


def stage(tmp: Path) -> Path:
    pkg = tmp / "skills" / "base_builder"
    pkg.mkdir(parents=True)
    for src in SKILL.iterdir():
        if src.suffix in {".py", ".json", ".csv", ".txt"}:
            shutil.copy(src, pkg / src.name)
    sys.path.append(str(tmp))
    return pkg


def refuses(fn, fragment: str, label: str) -> None:
    """The validator must refuse, and its reason must name the real objection."""
    import skills.base_builder.build as bb
    try:
        fn()
    except bb.GrammarError as exc:
        assert fragment.lower() in str(exc).lower(), f"{label}: wrong reason -- {exc}"
        return
    raise AssertionError(f"{label}: accepted a payload the API rejects")


def check_schema(pkg: Path, work: Path) -> None:
    import skills.base_builder.build as bb
    plan = bb.plan(str(pkg / "sample_crm.csv"), name="销售线索库", table="客户",
                   out_dir=str(work),
                   views=[{"name": "按阶段看板", "type": "kanban"}])
    got = {f["name"]: f["type"] for f in plan.schema}
    want = {"客户名": "text", "阶段": "select", "金额": "number", "负责人": "select",
            "下次跟进": "datetime", "来源": "select", "标签": "multi_select",
            "已签约": "checkbox", "备注": "text"}
    assert got == want, f"inferred {got}"
    print("  schema    OK  -- 9 columns, every type as a person would have chosen")

    payload = json.loads(Path(plan.payloads[0]).read_text(encoding="utf-8"))
    assert set(payload) == {"fields", "rows"} and isinstance(payload["rows"][0], list)
    columns = payload["fields"]
    sample = payload["rows"][0]
    cell = dict(zip(columns, sample, strict=True))
    assert isinstance(cell["金额"], (int, float)) and not isinstance(cell["金额"], bool)
    assert isinstance(cell["阶段"], str), "a select writes the plain string, not a list"
    assert isinstance(cell["标签"], list), "a multi-select writes an array"
    assert isinstance(cell["已签约"], bool), "a checkbox writes a real boolean"
    assert re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$", cell["下次跟进"])
    empty = [r for r in payload["rows"] if any(c is None for c in r)]
    assert empty, "the sample has blank cells and they must arrive as null"
    print("  dialect   OK  -- number bare, select plain, multi array, checkbox bool, "
          "datetime YYYY-MM-DD HH:MM:SS, blanks null")


def check_scale(work: Path) -> None:
    import skills.base_builder.build as bb
    rows = [{"名称": f"公司{i}", "阶段": ["新线索", "已成交"][i % 2], "金额": i * 1000}
            for i in range(450)]
    plan = bb.plan(rows, name="大表", table="线索", out_dir=str(work))
    sizes = [c["rows"] for c in plan.chunks]
    assert sizes == [200, 200, 50], sizes
    for chunk in plan.payloads:
        assert len(json.loads(Path(chunk).read_text())["rows"]) <= 200

    report = plan.report()
    schema_block = report.split("NOTES")[0].split("SCHEMA")[1][:200]
    assert "公司400" not in report and "公司1" not in schema_block
    assert len(report) < 6000, f"the plan itself is {len(report)} chars"
    on_disk = sum(Path(p).stat().st_size for p in plan.payloads)
    print(f"  scale     OK  -- 450 rows -> {sizes} per call; {on_disk:,} bytes on disk, "
          f"{len(report):,} chars of plan in the conversation")


def check_refusals(work: Path) -> None:
    import skills.base_builder.build as bb

    refuses(lambda: bb.validate_records([{"客户名": "张三"}]),
            "columnar", "an array of record objects")
    refuses(lambda: bb.validate_records({"fields": ["a"], "rows": [["x"], ["y"]] * 150}),
            "over the api", "more than 200 rows in one call")
    refuses(lambda: bb.validate_records({"fields": ["a", "b"], "rows": [["x"]]}),
            "cells for", "a row that is short a cell")
    refuses(lambda: bb.validate_records({"fields": ["金额"], "rows": [["12000"]]},
                                        {"金额": "number"}),
            "bare number", "a number written as a string")
    refuses(lambda: bb.validate_records({"fields": ["阶段"], "rows": [[["已成交"]]]},
                                        {"阶段": "select"}),
            "plain option string", "a select written as a list")
    refuses(lambda: bb.validate_records({"fields": ["下次跟进"], "rows": [["2026-10-01"]]},
                                        {"下次跟进": "datetime"}),
            "yyyy-mm-dd hh:mm:ss", "a date without its time")
    refuses(lambda: bb.validate_fields([{"field_name": "客户", "type": "text"}]),
            "field_name", "the field_name key")
    refuses(lambda: bb.validate_fields([{"name": "阶段", "type": "select",
                                         "property": {"options": []}}]),
            "property", "a property wrapper")
    refuses(lambda: bb.validate_fields([{"name": "x", "type": "单选"}]),
            "not a base field type", "an invented field type")
    refuses(lambda: bb.validate_fields([{"name": "a", "type": "text"},
                                        {"name": "a", "type": "number"}]),
            "duplicate", "two columns with one name")
    refuses(lambda: bb.validate_fields([{"name": "x", "type": "select",
                                         "options": [{"name": str(i)} for i in range(80)]}]),
            "over the", "80 select options")
    refuses(lambda: bb.validate_view({"view_name": "看板", "view_type": "kanban"}),
            "view_name", "the view_name key")
    refuses(lambda: bb.validate_view({"name": "看板", "type": "board"}),
            "not a view type", "an invented view type")
    refuses(lambda: bb.validate_filter([{"field": "阶段", "operator": "intersects"}]),
            "tuples", "an object-shaped filter condition")
    refuses(lambda: bb.validate_filter([["阶段", "contains", ["x"]]]),
            "not a filter operator", "an operator from the other filter dialect")
    print("  refusals  OK  -- 15 payloads the API rejects, refused offline, each naming "
          "the real objection")


def check_plan_hygiene(pkg: Path, work: Path) -> None:
    import skills.base_builder.build as bb
    plan = bb.plan(str(pkg / "sample_crm.csv"), name="销售线索库", table="客户",
                   out_dir=str(work),
                   views=[{"name": "按阶段看板", "type": "kanban"}],
                   queries=[{"what": "大单", "filter": [["金额", ">=", 100000]],
                             "sort": [{"field": "金额", "desc": True}]}])
    argvs = [s["argv"] for s in plan.steps]
    flat = json.dumps(argvs, ensure_ascii=False)
    assert "张三科技" not in flat, "row data must never reach the argv"
    assert "@<staged path>" in flat, "row payloads ride as @file, never inline"
    assert not re.search(r'"/[^"]*rows_\d+\.json"', flat), \
        "an absolute @path is refused by the CLI outright"
    share = argvs[-1]
    assert share[:2] == ["drive", "+member-add"] and "--type" in share and \
        share[share.index("--type") + 1] == "bitable", "the share step must close the plan"
    view = next(a for a in argvs if "+view-create" in a)
    body = json.loads(view[view.index("--json") + 1])
    assert set(body) == {"name", "type"} and body["type"] == "kanban", body
    query = plan.queries[0]["argv"]
    conditions = json.loads(query[query.index("--filter-json") + 1])["conditions"]
    assert isinstance(conditions[0], list), "filter conditions are tuples"
    print("  plan      OK  -- no rows in argv, @file only, relative paths, share step "
          "present, tuple filters")


def check_dirt(work: Path) -> None:
    import skills.base_builder.build as bb
    import skills.base_builder.infer as infer

    ragged = work / "ragged.csv"
    ragged.write_text("名称,金额,备注\n甲公司,140,000,追加预算\n乙公司,90000,ok\n",
                      encoding="utf-8")
    led = infer.Ledger()
    infer.load(str(ragged), led)
    assert "wrong number of cells" in led.summary(), led.summary()

    gbk = work / "gbk.csv"
    gbk.write_bytes("名称,阶段\n甲公司,已成交\n".encode("gbk"))
    led2 = infer.Ledger()
    infer.load(str(gbk), led2)
    assert "gbk" in led2.summary()

    try:
        infer.cell("rec_123", "link", None, "关联客户")
    except ValueError as exc:
        assert "read off the target table" in str(exc)
    else:
        raise AssertionError("a link cell must refuse to be invented")

    plan = bb.plan([{"a": 1}], name="x", table="t", out_dir=str(work),
                   views=[{"name": "板", "type": "kanban"}])
    assert "kanban groups by a select column" in plan.ledger.summary()
    print("  dirt      OK  -- ragged rows named, GBK announced, link cells refused, "
          "a pointless kanban called out")


def main() -> int:
    with tempfile.TemporaryDirectory() as raw:
        tmp = Path(raw)
        pkg = stage(tmp)
        work = tmp / "call"
        work.mkdir()
        print(f"staged {SKILL.name} as skills.base_builder in {tmp}")
        check_schema(pkg, work)
        check_scale(work)
        check_refusals(work)
        check_plan_hygiene(pkg, work)
        check_dirt(work)
    print("\nall checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
