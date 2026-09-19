"""Read a messy table and decide what each column IS, in Feishu Base's terms.

A Base column is typed, and the type decides the cell dialect: a select takes the plain
option string, a datetime takes `YYYY-MM-DD HH:MM:SS` and nothing else, a checkbox takes
a real boolean, a number takes a bare number. Guessing a column wrong is not a cosmetic
mistake -- the write is rejected, or worse, accepted with every cell as text and a table
nobody can group, sort or filter.

So inference here is conservative and it SHOWS ITS WORK: every column comes back with the
evidence that decided it, and anything it had to coerce or could not read is counted.
Text is the safe answer and it is the default; a richer type has to earn itself.
"""

from __future__ import annotations

import collections
import datetime as _dt
import json
import re

# A column becomes a select when the values repeat enough to be a vocabulary rather than
# free text. Both gates matter: 3 distinct values in 4 rows is a coincidence, and 200
# distinct values in 5000 rows is a name column, not a status column.
_SELECT_MAX_OPTIONS = 50
_SELECT_MAX_RATIO = 0.35
_SELECT_MAX_LEN = 24
_MULTI_DELIMS = ("、", ";", "；", "|", ",", "，", "/")
_TRUE = {"是", "true", "yes", "y", "1", "✓", "√", "已完成", "有"}
_FALSE = {"否", "false", "no", "n", "0", "✗", "×", "未完成", "无"}
_DATE_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%Y/%m/%d",
                 "%Y/%m/%d %H:%M", "%d/%m/%Y", "%Y年%m月%d日", "%Y-%m-%dT%H:%M:%S",
                 "%Y-%m-%dT%H:%M:%SZ")
_NUM_STRIP = str.maketrans({",": "", "，": "", "¥": "", "$": "", "￥": "", " ": "",
                            " ": "", "%": ""})
_OU = re.compile(r"^ou_[A-Za-z0-9]+$")


class Ledger:
    """What was coerced, what was dropped, and why -- reported, never swallowed."""

    def __init__(self) -> None:
        self.rows = 0
        self.notes: list[str] = []
        self.counts: collections.Counter = collections.Counter()

    def count(self, reason: str, n: int = 1) -> None:
        self.counts[reason] += n

    def note(self, text: str) -> None:
        if text not in self.notes:
            self.notes.append(text)

    def summary(self) -> str:
        parts = [f"{n} {reason}" for reason, n in self.counts.most_common()]
        return "  ·  ".join([*parts, *self.notes]) or "nothing to report"


def blank(value) -> bool:
    return value is None or str(value).strip() in {
        "", "-", "--", "null", "None", "NULL", "N/A", "n/a"}


def as_number(value):
    """A bare number, or None. Strips the separators a spreadsheet export leaves behind."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    text = str(value).strip().translate(_NUM_STRIP)
    if not text or text in {"-", "+", "."}:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    return int(number) if number.is_integer() and abs(number) < 2**53 else number


def as_datetime(value) -> str | None:
    """The CLI's one datetime spelling, or None. Epoch ms and seconds are understood."""
    if isinstance(value, _dt.datetime):
        return value.strftime(_DATE_FORMATS[0])
    if isinstance(value, _dt.date):
        return _dt.datetime.combine(value, _dt.time.min).strftime(_DATE_FORMATS[0])
    text = str(value or "").strip()
    if not text:
        return None
    if text.isdigit() and len(text) in (10, 13):
        stamp = int(text) // (1000 if len(text) == 13 else 1)
        try:
            return _dt.datetime.fromtimestamp(stamp, _dt.timezone.utc).strftime(_DATE_FORMATS[0])
        except (OverflowError, OSError, ValueError):
            return None
    for fmt in _DATE_FORMATS:
        try:
            return _dt.datetime.strptime(text, fmt).strftime(_DATE_FORMATS[0])
        except ValueError:
            continue
    return None


def as_bool(value):
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    if text in _TRUE:
        return True
    if text in _FALSE:
        return False
    return None


def split_multi(value) -> list[str] | None:
    """The parts of a multi-value cell, or None when it holds exactly one thing."""
    text = str(value or "").strip()
    for delim in _MULTI_DELIMS:
        if delim in text:
            parts = [p.strip() for p in text.split(delim) if p.strip()]
            if len(parts) > 1:
                return parts
    return None


def column_type(values: list, name: str = "") -> dict:
    """{'type': ..., 'why': ..., 'options': [...]} for one column's raw values."""
    present = [v for v in values if not blank(v)]
    if not present:
        return {"type": "text", "why": "every cell is empty", "options": []}

    texts = [str(v).strip() for v in present]
    uniques = sorted(set(texts))

    if all(_OU.match(t) for t in texts):
        return {"type": "user", "why": "every value is an ou_ open_id", "options": []}

    bools = [as_bool(v) for v in present]
    if all(b is not None for b in bools) and len(uniques) <= 2:
        return {"type": "checkbox", "why": f"two truthy values ({'/'.join(uniques)})",
                "options": []}

    numbers = [as_number(v) for v in present]
    if all(n is not None for n in numbers):
        # A column of numbers that repeat a handful of times is still a number column:
        # 金额 and 数量 must stay sortable and summable. Only text becomes a select.
        return {"type": "number", "why": "every value parses as a number", "options": []}

    dates = [as_datetime(v) for v in present]
    if sum(d is not None for d in dates) >= max(1, int(0.8 * len(present))):
        unread = sum(d is None for d in dates)
        why = "at least 80% of values parse as dates"
        return {"type": "datetime", "why": why, "options": [], "unreadable": unread}

    multi = [split_multi(v) for v in present]
    if sum(m is not None for m in multi) >= max(1, int(0.3 * len(present))):
        parts = sorted({p for m in multi if m for p in m}
                       | {t for t, m in zip(texts, multi, strict=True) if m is None})
        if len(parts) <= _SELECT_MAX_OPTIONS and all(len(p) <= _SELECT_MAX_LEN for p in parts):
            return {"type": "multi_select",
                    "why": f"{sum(m is not None for m in multi)} cells hold several values",
                    "options": parts}

    ratio = len(uniques) / len(texts)
    # Two ways to be a vocabulary. The ratio gate is for real tables; the small-vocabulary
    # gate catches a short one, where 3 statuses over 5 rows is 60% unique and would
    # otherwise read as free text -- a demo table would lose every select it has.
    vocabulary = (len(uniques) <= _SELECT_MAX_OPTIONS and ratio <= _SELECT_MAX_RATIO) or (
        len(uniques) <= 8 and len(uniques) < len(texts))
    # A vocabulary's members are about the same length: 新线索 / 已成交 / 谈判中. One value
    # far longer than the rest means free text that happens to repeat -- a 备注 column of
    # canned remarks. Turning that into a select gives someone an option list with a
    # sentence in it, and no way to write a new note.
    lengths = sorted(len(t) for t in uniques)
    median = lengths[len(lengths) // 2]
    even = max(lengths) <= max(12, 2.5 * median)
    if vocabulary and even and max(lengths) <= _SELECT_MAX_LEN:
        return {"type": "select",
                "why": f"{len(uniques)} distinct values over {len(texts)} rows "
                       f"({ratio:.0%} unique)",
                "options": uniques}

    return {"type": "text", "why": f"{len(uniques)} distinct values ({ratio:.0%} unique)",
            "options": []}


def cell(value, field_type: str, ledger: Ledger | None = None, column: str = ""):
    """One value in the dialect its column's type demands. `None` empties the cell."""
    led = ledger
    if blank(value):
        return None
    if field_type == "number":
        number = as_number(value)
        if number is None and led:
            led.count(f"{column}: unreadable number")
        return number
    if field_type == "datetime":
        when = as_datetime(value)
        if when is None and led:
            led.count(f"{column}: unreadable date")
        return when
    if field_type == "checkbox":
        flag = as_bool(value)
        if flag is None and led:
            led.count(f"{column}: unreadable yes/no")
        return flag
    if field_type == "multi_select":
        return split_multi(value) or [str(value).strip()]
    if field_type == "user":
        return [{"id": str(value).strip()}]
    if field_type == "link":
        # Record ids are READ off the target table. Constructing one is the fastest way
        # to an 800030405 not_found, so a raw value here is refused rather than guessed.
        raise ValueError(
            f"{column}: a link cell takes record ids read off the target table "
            f"([{{'id': 'rec_...'}}]), which this compiler cannot invent")
    if field_type == "select":
        return str(value).strip()
    return str(value).strip()


def read_csv(text: str, ledger: Ledger | None = None) -> tuple[list[str], list[dict]]:
    """Header + rows from CSV text, blank lines dropped, duplicate headers made unique."""
    import csv
    import io

    reader = csv.reader(io.StringIO(text))
    header: list[str] = []
    rows: list[dict] = []
    ragged: list[int] = []
    for raw in reader:
        if not any((c or "").strip() for c in raw):
            continue
        if not header:
            seen: collections.Counter = collections.Counter()
            for i, name in enumerate(raw):
                clean = (name or "").strip() or f"列{i + 1}"
                seen[clean] += 1
                header.append(clean if seen[clean] == 1 else f"{clean}_{seen[clean]}")
            continue
        if len(raw) != len(header):
            # A ragged row is the signature of an unquoted delimiter inside a cell, and
            # every column after it is shifted. Padding it in silence is how a table ends
            # up with 负责人 full of amounts -- so it is counted and named.
            ragged.append(len(rows) + 2)   # +2: 1-indexed, and the header is line 1
        rows.append({header[i]: (raw[i] if i < len(raw) else "") for i in range(len(header))})
    if ragged and ledger is not None:
        ledger.count(f"rows with the wrong number of cells (first at line {ragged[0]})",
                     len(ragged))
        ledger.note("a ragged row usually means an unquoted comma inside a cell; the "
                    "columns after it are shifted and the types below may be wrong")
    return header, rows


def load(path: str, ledger: Ledger | None = None) -> tuple[list[str], list[dict]]:
    """CSV or JSON (a list of objects) off disk, decoded as UTF-8 then GBK."""
    led = ledger or Ledger()
    text = None
    for encoding in ("utf-8-sig", "gbk", "latin-1"):
        try:
            with open(path, encoding=encoding) as fh:
                text = fh.read()
            if encoding != "utf-8-sig":
                led.note(f"file decoded as {encoding}, not UTF-8")
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise ValueError(f"{path}: could not decode as UTF-8, GBK or Latin-1")

    stripped = text.lstrip()
    if stripped[:1] in "[{":
        data = json.loads(stripped)
        rows = data if isinstance(data, list) else data.get("rows") or data.get("data") or []
        rows = [r for r in rows if isinstance(r, dict)]
        header: list[str] = []
        for row in rows:
            for key in row:
                if key not in header:
                    header.append(key)
        led.rows = len(rows)
        return header, rows

    header, rows = read_csv(text, led)
    led.rows = len(rows)
    return header, rows
