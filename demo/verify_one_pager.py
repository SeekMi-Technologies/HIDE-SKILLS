#!/usr/bin/env python3
"""Offline checks for the `one-pager` skill. Nothing here talks to Langfuse or Feishu.

    python3 demo/verify_one_pager.py            # needs matplotlib + numpy in the env

It stages the skill the way the sandbox does -- `<root>/skills/one_pager/` on sys.path --
then exercises: the dirty-data contract, the font branch both ways, four shapes of
Langfuse server against a stand-in bridge, and a real render of each route. It lives in
`demo/` because this directory is not a skill directory: the loader only serves files that
sit beside a SKILL.md, so nothing here is ever shown to the model or put in the sandbox.
"""
from __future__ import annotations

import collections
import dataclasses
import importlib
import json
import shutil
import sys
import tempfile
import warnings
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent / "orgs" / "sandbox" / "skills" / "one-pager"


def stage(tmp: Path) -> Path:
    """Exactly what `skill_helpers.materialize` does: kebab name -> snake package."""
    pkg = tmp / "skills" / "one_pager"
    pkg.mkdir(parents=True)
    for src in SKILL.iterdir():
        if src.suffix in {".py", ".json", ".csv", ".txt"}:
            shutil.copy(src, pkg / src.name)
    sys.path.append(str(tmp))       # APPEND, like child.py -- stdlib keeps priority
    return pkg


# --------------------------------------------------------------------------- the bridge
class BridgeError(RuntimeError):
    def __init__(self, kind, message):
        super().__init__(message)
        self.kind = kind


class NeedsApproval(BridgeError):
    pass


def _content(payload):
    return [{"type": "text", "text": json.dumps(payload)}]


class FakeLangfuse:
    """Same envelope and refusals as the real one, with the two unknowns as switches:
    whether it groups by a time dimension, and which argument shape it accepts."""

    def __init__(self, time_dimension=True, accepts="query_str", percentiles=True):
        self.time_dimension, self.accepts, self.percentiles = time_dimension, accepts, percentiles
        self.calls = 0

    def queryMetrics(self, **kwargs):  # noqa: N802 -- the MCP slug's own spelling
        self.calls += 1
        if self.accepts == "query_str":
            if set(kwargs) != {"query"} or not isinstance(kwargs["query"], str):
                raise BridgeError("BridgeProtocolError", "query must be a JSON string")
            body = json.loads(kwargs["query"])
        else:
            if set(kwargs) != {"query"} or not isinstance(kwargs["query"], dict):
                raise BridgeError("BridgeProtocolError", "query must be an object")
            body = kwargs["query"]

        dims = [d["field"] for d in body.get("dimensions") or []]
        measures = [(m["measure"], m["aggregation"]) for m in body["metrics"]]
        names = {m for m, _ in measures}
        if "name" in dims:
            return _content({"data": [{"name": n, "count_count": c} for n, c in
                                      [("commander_turn", 812), ("task_turn", 208),
                                       ("automation_turn", 96), ("digest_turn", 41)]]})
        if "latency" in names:
            if not self.percentiles and any(a in {"p50", "p95"} for m, a in measures
                                            if m == "latency"):
                raise BridgeError("ToolError", "aggregation p95 is not supported")
            row = {"latency_avg": 3480.0}
            if self.percentiles:
                row |= {"latency_p50": 2950.0, "latency_p95": 6640.0}
            return _content({"data": [row]})
        if "totalCost" in names:
            return _content({"data": [{"totalCost_sum": 4.21, "totalTokens_sum": 1284000}]})
        if body.get("timeDimension"):
            if not self.time_dimension:
                return _content({"data": [{"count_count": 1174}]})   # no date column at all
            import datetime as dt
            start = dt.date.today() - dt.timedelta(days=6)
            return _content({"data": [
                {"time_dimension": (start + dt.timedelta(days=i)).isoformat(),
                 "count_count": float(120 + 13 * i)} for i in range(7)]})
        return _content({"data": [{"count_count": 160.0}]})

    def listScores(self, **kwargs):  # noqa: N802
        self.calls += 1
        if kwargs:
            raise BridgeError("BridgeProtocolError", "unexpected arguments")
        modes = ["incomplete"] * 6 + ["wrong_target"] * 4 + ["off_task"] * 2
        rows = [{"name": "judge_pass", "value": 1 if i % 7 else 0} for i in range(40)]
        rows += [{"name": "judge_failure_mode", "stringValue": m} for m in modes]
        return _content({"data": rows})

    def createScore(self, **kwargs):  # noqa: N802
        raise NeedsApproval("NeedsApproval", "createScore writes, so it needs a human")


class FakeHide:
    def __init__(self, **kw):
        self.langfuse = FakeLangfuse(**kw)

    def gather(self, entries):
        out = []
        for fn, kwargs in entries:
            try:
                out.append(fn(**kwargs))
            except Exception as exc:  # noqa: BLE001
                out.append(exc)
        return out


# ---------------------------------------------------------------------------- the checks
def check_tidy(pkg: Path) -> None:
    import skills.one_pager.tidy as tidy

    rows, led = tidy.load_csv(str(pkg / "sample_traces.csv"))
    raw = [r["judge_pass"] for r in rows]
    assert "[1]" in raw, "the sample must still carry the list-valued cell"
    counts = collections.Counter(tidy.key(v) for v in raw)   # a bare list would raise here
    assert "[1]" not in counts, "a one-element list must count with its scalar twin"
    assert tidy.num("2,104") == 2104.0 and tidy.num("  1 843  ") is None

    p50, p95 = tidy.quantiles([r["latencyMs"] for r in rows])
    assert p95 > p50 > 0, "quantiles must survive a column with 'n/a' in it"

    x, y = tidy.by_day(rows, "timestamp", agg="count", ledger=led)
    assert len(x) == 7 and sum(y) == len(rows) - 2
    labels, values = tidy.top_n(rows, "judge_failure_mode", n=5, ledger=led)
    assert values == sorted(values, reverse=True)
    assert led.dropped == 2, "an empty category is not a dropped row"
    assert led.excluded["rows with no judge_failure_mode"] == 47
    summary = led.summary()
    for fragment in ("dropped 2 of 61", "47 rows with no judge_failure_mode",
                     "exactly duplicated rows kept"):
        assert fragment in summary, summary
    print("  tidy      OK  --", summary)


def check_font() -> None:
    from matplotlib import font_manager
    import skills.one_pager.report as report

    real = list(font_manager.fontManager.ttflist)
    base = next(f for f in real if f.name == "DejaVu Sans")
    name, cjk = report.font_in_use()
    assert cjk is False, "a host with no CJK face must not claim one"
    plain = name

    font_manager.fontManager.ttflist = [dataclasses.replace(base, name="Heiti SC"),
                                        dataclasses.replace(base, name="Noto Sans CJK SC")] + real
    importlib.reload(report)
    picked, cjk = report.font_in_use()
    assert (picked, cjk) == ("Noto Sans CJK SC", True), (picked, cjk)
    font_manager.fontManager.ttflist = real
    importlib.reload(report)
    print(f"  font      OK  -- bare host picks {plain} and says so; "
          f"with faces present it picks the theme's first, not the alphabet's")


def check_langfuse(tmp: Path) -> None:
    import skills.one_pager.report as report

    for label, kw in (("time dimension", {}),
                      ("per-day fallback", {"time_dimension": False}),
                      ("object-shaped server", {"accepts": "query_obj"}),
                      ("no percentiles", {"percentiles": False})):
        for mod in [m for m in list(sys.modules) if m.startswith("skills.one_pager.lf")]:
            del sys.modules[mod]
        lf = importlib.import_module("skills.one_pager.lf")
        hide = FakeHide(**kw)
        assert lf.bind(hide) is True
        x, y = lf.daily(7)
        names, counts = lf.by_name(7, limit=5)
        lat, sc = lf.latency(7), lf.scores(7)
        assert len(x) == 7 and sum(y) > 0, (label, x, y)
        assert names and lat["avg"] and sc["pass_rate"], label
        assert hide.langfuse.calls <= 64, "the bridge budget is 64 calls per program"
        expected = {"time dimension": [], "object-shaped server": []}.get(label)
        if expected is not None:
            assert lf.notes == expected, (label, lf.notes)
        else:
            assert lf.notes, f"{label} must SAY what it could not do"
        out = report.render({
            "title": "Bot health", "subtitle": f"7 days - {label}",
            "kpis": [{"label": "traces", "value": report.compact(sum(y)),
                      "delta": 0.12, "good": "up", "note": "vs prior week"},
                     {"label": "judge pass", "value": report.pct(sc["pass_rate"]), "good": "up"}],
            "trend": {"title": "Traces per day", "x": x, "series": [{"label": "traces", "y": y}]},
            "bars": {"title": "Failure modes", "labels": list(sc["modes"])[:5],
                     "values": list(sc["modes"].values())[:5]},
            "footer": "  ·  ".join(lf.notes) or "every panel live from Langfuse",
        }, str(tmp / f"lf-{label.replace(' ', '-')}.png"))
        print(f"  langfuse  OK  -- {label}: {hide.langfuse.calls} bridge calls, "
              f"{len(lf.notes)} note(s), {Path(out).name}")

    # No bridge at all: the answer is a sentence, not a traceback.
    for mod in [m for m in list(sys.modules) if m.startswith("skills.one_pager.lf")]:
        del sys.modules[mod]
    lf = importlib.import_module("skills.one_pager.lf")
    lf.bind(None)
    assert lf.available() is False and lf.daily(7) == ([], []) and lf.notes
    print("  no bridge OK  --", lf.notes[0])


def check_render(tmp: Path, pkg: Path) -> None:
    import skills.one_pager.report as report
    import skills.one_pager.tidy as tidy

    rows, led = tidy.load_csv(str(pkg / "sample_traces.csv"))
    x, y = tidy.by_day(rows, "timestamp", agg="count", ledger=led)
    labels, values = tidy.top_n(rows, "judge_failure_mode", n=5, ledger=led)
    p50, p95 = tidy.quantiles([r["latencyMs"] for r in rows])
    spec = {
        "title": "机器人周报 · sandbox",
        "subtitle": f"最近 7 天 · {len(rows)} 条 trace · sample_traces.csv",
        "notes": [f"p50 {p50 / 1000:.1f}s", f"p95 {p95 / 1000:.1f}s"],
        "kpis": [{"label": "调用量", "value": report.compact(len(rows)), "delta": 0.12,
                  "good": "up", "note": "vs 上周"},
                 {"label": "p95 延迟", "value": f"{p95 / 1000:.1f}s", "delta": -0.04,
                  "good": "down", "note": "vs 上周"},
                 {"label": "judge pass", "value": report.pct(0.77), "delta": 0.03, "good": "up"},
                 {"label": "活跃用户", "value": report.compact(len({r["user"] for r in rows}))}],
        "trend": {"title": "每日调用量", "x": x, "series": [{"label": "traces", "y": y}]},
        "bars": {"title": "失败模式 Top 5", "labels": labels, "values": values},
        "footer": led.summary(),
    }
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        out = report.render(spec, str(tmp / "csv-route.png"))
    assert Path(out).stat().st_size > 20_000, "a page that small did not draw"

    for broken, expected in (({"kpis": []}, "title"),
                             ({"title": "x", "trend": {"x": [1, 2], "series": [{"y": [1]}]}},
                              "must match")):
        try:
            report.render(broken, str(tmp / "never.png"))
        except ValueError as exc:
            assert expected in str(exc), exc
        else:
            raise AssertionError(f"a malformed spec must raise, not draw: {broken}")
    print(f"  render    OK  -- {Path(out).name} "
          f"({Path(out).stat().st_size // 1024} KiB), malformed specs refused by name")


def main() -> int:
    with tempfile.TemporaryDirectory() as raw:
        tmp = Path(raw)
        pkg = stage(tmp)
        print(f"staged {SKILL.name} as skills.one_pager in {tmp}")
        check_tidy(pkg)
        check_font()
        check_langfuse(tmp)
        check_render(tmp, pkg)
    print("\nall checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
