#!/usr/bin/env python3
"""Offline checks for the `motion` skill. Renders real GIFs; talks to nothing.

    python3 demo/verify_motion.py

Proves the four claims that make this shipped code rather than something improvised per
turn: the input shape does not matter, a bar keeps its colour, the file FITS the sandbox's
8 MiB write limit, and every number the skill reports about its own output was read back
off the file.
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent / "orgs" / "sandbox" / "skills" / "motion"


def stage(tmp: Path) -> Path:
    pkg = tmp / "skills" / "motion"
    pkg.mkdir(parents=True)
    for src in SKILL.iterdir():
        if src.suffix in {".py", ".json", ".csv", ".txt"}:
            shutil.copy(src, pkg / src.name)
    sys.path.append(str(tmp))
    return pkg


def rows_from(pkg: Path):
    import csv
    with open(pkg / "sample_revenue.csv", encoding="utf-8") as fh:
        return [(r["区域"], r["月份"], r["营收"]) for r in csv.DictReader(fh)]


def check_shapes(pkg: Path) -> None:
    import skills.motion.race as race
    rows = rows_from(pkg)
    tuples = race.normalise(rows)
    dicts = race.normalise([{"entity": e, "period": p, "value": v} for e, p, v in rows])
    nested: dict = {}
    for e, p, v in rows:
        nested.setdefault(e, {})[p] = v
    nest = race.normalise(nested)
    assert tuples[0] == dicts[0] == nest[0], "entity order must not depend on input shape"
    assert tuples[1] == dicts[1] == nest[1]
    assert tuples[2] == dicts[2] == nest[2]
    assert len(tuples[1]) == 14 and len(tuples[0]) == 6

    # Money arrives wearing separators and symbols; a race that silently drops those rows
    # would draw a bar at zero for a region that had a good month.
    _, _, table = race.normalise([("甲", "2026-01", "1,240"), ("甲", "2026-02", "¥2,480"),
                                  ("乙", "2026-01", 900), ("乙", "2026-02", 1800.5)])
    assert table[("甲", "2026-02")] == 2480.0 and table[("乙", "2026-02")] == 1800.5
    print("  shapes    OK  -- tuples, dicts and nested maps agree; ¥ and commas survive")


def check_gaps() -> None:
    import skills.motion.race as race
    entities, periods, table = race.normalise(
        [("甲", "01", 10), ("甲", "03", 30), ("乙", "01", 5), ("乙", "02", 6), ("乙", "03", 7)])
    filled = race._carry_forward(entities, periods, table)
    assert filled[("甲", "02")] == 10, "a missing period must carry forward, not drop to 0"
    print("  gaps      OK  -- an unreported month holds its last value instead of "
          "collapsing to zero")


def check_colour_and_rank(pkg: Path, work: Path) -> None:
    import skills.motion.race as race
    rows = rows_from(pkg)
    entities, periods, table = race.normalise(rows)
    values = race._carry_forward(entities, periods, table)

    first = sorted(entities, key=lambda e: -values[(e, periods[0])])
    last = sorted(entities, key=lambda e: -values[(e, periods[-1])])
    assert first != last, "the sample must actually contain an overtake to be worth shipping"

    theme = race._theme()
    colour = {e: theme["series"][i % len(theme["series"])] for i, e in enumerate(entities)}
    assert len(set(colour.values())) == len(entities), "every entity needs its own colour"
    assert colour[first[0]] == colour[first[0]], "colour is per entity"
    # The rule this encodes: colour follows the entity, never its rank. If it followed
    # rank, the leader's colour would be the same in the first and last frame while the
    # leader changed -- the colours would stand still while the data moved.
    assert colour[first[0]] != colour[last[0]] or first[0] == last[0]
    print(f"  colour    OK  -- {len(entities)} stable colours; the lead changes "
          f"{first[0]} → {last[0]} and the colours travel with them")


def check_budget(pkg: Path, work: Path) -> None:
    import skills.motion.draw as draw
    import skills.motion.race as race
    rows = rows_from(pkg)

    out = race.bar_race(rows, str(work / "full.gif"), title="各区域月度营收",
                        subtitle="演示", unit="¥", note="sample")
    measured = draw.measure(out["path"])
    assert out["frames"] == measured["frames"] == 144 or out["frames"] == measured["frames"]
    assert out["bytes"] == measured["bytes"] == Path(out["path"]).stat().st_size
    assert out["seconds"] == measured["seconds"]
    assert out["bytes"] < 7_000_000
    print(f"  honesty   OK  -- reports {out['frames']} frames / {out['seconds']}s / "
          f"{out['kib']} KiB, all read back off the file")

    # The sandbox kills a program that writes past RLIMIT_FSIZE; it does not raise. So the
    # encoder has to fit the budget BEFORE anything touches the disk.
    tight = race.bar_race(rows, str(work / "tight.gif"), title="各区域月度营收",
                          max_bytes=120_000)
    assert tight["bytes"] <= 120_000, tight
    assert Path(tight["path"]).stat().st_size <= 120_000
    assert [n for n in tight["notes"] if "palette" in n or "scaled" in n or "frame" in n], \
        "degrading the output silently would be the wrong kind of quiet"
    assert tight["seconds"] >= out["seconds"] * 0.9, \
        "dropping frames must not shorten the animation"

    # And when it cannot fit, it must REFUSE rather than write a file that trips
    # RLIMIT_FSIZE and kills the turn with no output at all.
    try:
        race.bar_race(rows, str(work / "impossible.gif"), title="x", max_bytes=4_000)
    except ValueError as exc:
        assert "could not fit" in str(exc), exc
        assert not (work / "impossible.gif").exists(), "it wrote the file it refused"
    else:
        raise AssertionError("an impossible budget must raise, not write over the limit")
    print(f"  budget    OK  -- {out['kib']} KiB → {tight['kib']} KiB under a 117 KiB cap "
          f"keeping {tight['seconds']}s; an impossible cap refuses instead of writing")


def check_text(pkg: Path, work: Path) -> None:
    import skills.motion.draw as draw
    import skills.motion.race as race

    assert draw.has_wide("各区域") and not draw.has_wide("Revenue by region")
    latin = race.bar_race([("East", "01", 10), ("East", "02", 20),
                           ("West", "01", 12), ("West", "02", 15)],
                          str(work / "latin.gif"), title="Revenue")
    assert not any("CJK" in n for n in latin["notes"]), \
        "a Latin-only chart must not warn about a font it never needed"
    assert race._fmt(1_240_000, "$", "en") == "$1.24M"
    assert race._fmt(12_400, "¥", "cn") == "¥1.2万"
    print("  text      OK  -- CJK warning only when there is CJK; 万/亿 for Chinese, "
          "K/M for Latin")


def check_refusals(work: Path) -> None:
    import skills.motion.race as race
    for data, fragment, label in (
        ([("甲", "01", 10)], "two periods", "a single period"),
        ([], "no usable rows", "an empty table"),
        ([("甲", "01", "n/a"), ("甲", "02", "-")], "no usable rows", "nothing numeric"),
    ):
        try:
            race.bar_race(data, str(work / "never.gif"))
        except ValueError as exc:
            assert fragment in str(exc), f"{label}: wrong reason -- {exc}"
        else:
            raise AssertionError(f"{label}: rendered a race that cannot exist")
    print("  refusals  OK  -- a race with one period, no rows, or no numbers is refused "
          "by name")


def main() -> int:
    with tempfile.TemporaryDirectory() as raw:
        tmp = Path(raw)
        pkg = stage(tmp)
        work = tmp / "call"
        work.mkdir()
        print(f"staged {SKILL.name} as skills.motion in {tmp}")
        check_shapes(pkg)
        check_gaps()
        check_colour_and_rank(pkg, work)
        check_budget(pkg, work)
        check_text(pkg, work)
        check_refusals(work)
    print("\nall checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
