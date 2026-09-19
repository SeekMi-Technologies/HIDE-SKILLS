"""Read a dirty CSV and aggregate it without ever throwing away a row in silence.

    import skills.one_pager.tidy as tidy
    rows, led = tidy.load_csv(path)
    x, y = tidy.by_day(rows, "timestamp", agg="count", ledger=led)
    print(led.summary())          # -> the string that belongs in spec['footer']

Everything here is the `data-analysis` skill's prose turned into code. That skill tells
you to coerce every field at the edge and to say what you dropped; this module does it,
so the honest footer is produced by construction rather than by remembering.

The two failure modes it exists for are both real, both from a live Langfuse export:
`judge_pass` came back as `[1]` (a list -- unhashable, so `Counter` raised) and
`latencyMs` mixed numbers with strings (so `mean` raised). Each one killed a program on
row ~900 of 3000, AFTER it had printed half an answer.
"""

from __future__ import annotations

import collections
import csv
import datetime as _dt
import json


class Ledger:
    """What was dropped and why. `summary()` is a sentence, not a log line."""

    def __init__(self) -> None:
        self.total = 0
        self.reasons: collections.Counter = collections.Counter()
        self.excluded: collections.Counter = collections.Counter()
        self.notes: list[str] = []

    def drop(self, reason: str, n: int = 1) -> None:
        """A row whose value could not be READ -- a real loss, counted as dropped."""
        self.reasons[reason] += n

    def exclude(self, reason: str, n: int = 1) -> None:
        """A row that was legitimately EMPTY for one panel -- not a loss, and not a drop.

        The distinction is the whole honesty of the footer: 47 traces with no failure
        mode are 47 successes, and reporting them as "dropped" turns a clean week into
        a broken file.
        """
        self.excluded[reason] += n

    def note(self, text: str) -> None:
        if text not in self.notes:
            self.notes.append(text)

    @property
    def dropped(self) -> int:
        return sum(self.reasons.values())

    def summary(self) -> str:
        parts = []
        if self.dropped:
            why = ", ".join(f"{n} {reason}"
                            for reason, n in self.reasons.most_common())
            parts.append(f"dropped {self.dropped:,} of {self.total:,} rows: {why}")
        elif self.total:
            parts.append(f"{self.total:,} rows, none dropped")
        for reason, n in self.excluded.most_common():
            parts.append(f"{n:,} {reason}")
        parts.extend(self.notes)
        return "  ·  ".join(parts)


def load_csv(path: str, ledger: Ledger | None = None) -> tuple[list[dict], Ledger]:
    """Rows as dicts, plus the ledger every later call keeps writing to.

    Tries UTF-8 first and GBK second: a spreadsheet exported from a Chinese Windows box
    is GBK often enough that failing on it is the wrong default, and a wrong encoding is
    not a silent error here -- it is recorded on the ledger.
    """
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

    rows, seen = [], set()
    duplicates = 0
    for row in csv.DictReader(text.splitlines()):
        led.total += 1
        if not any((v or "").strip() for v in row.values()):
            led.drop("blank line")
            continue
        fingerprint = json.dumps(row, sort_keys=True, default=str)
        if fingerprint in seen:
            duplicates += 1
        seen.add(fingerprint)
        rows.append(row)
    if duplicates:
        # NOT dropped: two identical rows may be two identical events. Said out loud so
        # whoever reads the page can decide, which is not a decision this module may make.
        led.note(f"{duplicates:,} exactly duplicated rows kept")
    return rows, led


def num(value) -> float | None:
    """Anything -> float, or None. For any column you will sum, average or rank by."""
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, (list, tuple)) and len(value) == 1:
        return num(value[0])
    try:
        return float(str(value).strip().replace(",", "").rstrip("%"))
    except (TypeError, ValueError, AttributeError):
        return None


def key(value):
    """Anything -> something hashable. For any column you will count or group by.

    A ONE-ELEMENT list is unwrapped, so `judge_pass` arriving as `[1]` on some rows and
    `1` on others counts as one group rather than two. `num` already does this, and a
    grouping that disagrees with the arithmetic about what a cell means is a bug wearing
    a plausible face. Longer lists keep their shape -- they are a real, different value.
    """
    if isinstance(value, (list, tuple)) and len(value) == 1:
        inner = key(value[0])
        # Back to text, because the twin it has to match came out of a CSV cell and is
        # `"1"`, not `1`. Two groups where the data means one is the bug this prevents.
        if isinstance(inner, (int, float)) and not isinstance(inner, bool):
            return str(inner)
        return inner
    if isinstance(value, (list, dict)):
        return json.dumps(value, sort_keys=True, default=str)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped[:1] in "[{":
            try:
                return key(json.loads(stripped))
            except ValueError:
                return stripped
        return stripped
    return value


def day(value) -> _dt.date | None:
    """Anything -> a date, or None. ISO, slashes, and epoch milliseconds."""
    if isinstance(value, _dt.datetime):
        return value.date()
    if isinstance(value, _dt.date):
        return value
    text = str(value or "").strip()
    if not text:
        return None
    if text.isdigit() and len(text) >= 10:   # epoch seconds or milliseconds
        stamp = int(text)
        if stamp > 10_000_000_000:
            stamp //= 1000
        try:
            return _dt.datetime.fromtimestamp(stamp, _dt.timezone.utc).date()
        except (OverflowError, OSError, ValueError):
            return None
    head = text.replace("/", "-").replace("T", " ").split(" ")[0]
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%m-%d-%Y", "%Y-%m"):
        try:
            return _dt.datetime.strptime(head, fmt).date()
        except ValueError:
            continue
    return None


def by_day(rows, date_col: str, value_col: str | None = None, agg: str = "count",
           ledger: Ledger | None = None, fill_gaps: bool = True):
    """(labels, values) per calendar day, zero-traffic days included.

    A trend that silently omits the quiet days is a trend that lies about its shape.
    """
    led = ledger or Ledger()
    buckets: dict[_dt.date, list[float]] = collections.defaultdict(list)
    for row in rows:
        when = day(row.get(date_col))
        if when is None:
            led.drop(f"unreadable {date_col}")
            continue
        if agg == "count":
            buckets[when].append(1.0)
            continue
        value = num(row.get(value_col))
        if value is None:
            led.drop(f"non-numeric {value_col}")
            continue
        buckets[when].append(value)
    if not buckets:
        return [], []

    days = sorted(buckets)
    if fill_gaps:
        span, cursor = [], days[0]
        while cursor <= days[-1]:
            span.append(cursor)
            cursor += _dt.timedelta(days=1)
        days = span

    out = []
    for when in days:
        values = buckets.get(when) or []
        if agg == "count":
            out.append(float(len(values)))
        elif agg == "sum":
            out.append(float(sum(values)))
        elif agg == "mean":
            out.append(sum(values) / len(values) if values else 0.0)
        else:
            raise ValueError(f"agg must be count, sum or mean -- got {agg!r}")
    return [d.strftime("%m-%d") for d in days], out


def top_n(rows, col: str, n: int = 5, value_col: str | None = None,
          ledger: Ledger | None = None, skip: tuple = ("", "none", "null", "nan")):
    """(labels, values) for the n biggest groups -- counted, or summed over value_col."""
    led = ledger or Ledger()
    totals: collections.Counter = collections.Counter()
    for row in rows:
        group = key(row.get(col))
        if group is None or str(group).strip().lower() in skip:
            # Empty is not unreadable: a blank failure mode means the turn had none.
            led.exclude(f"rows with no {col}")
            continue
        if value_col is None:
            totals[str(group)] += 1
            continue
        value = num(row.get(value_col))
        if value is None:
            led.drop(f"non-numeric {value_col}")
            continue
        totals[str(group)] += value
    ranked = totals.most_common(n)
    return [label for label, _ in ranked], [value for _, value in ranked]


def quantiles(values, qs=(0.5, 0.95)) -> tuple:
    """Linear-interpolated quantiles over whatever coerces to a number. None if empty."""
    clean = sorted(v for v in (num(v) for v in values) if v is not None)
    if not clean:
        return tuple(None for _ in qs)
    out = []
    for q in qs:
        position = (len(clean) - 1) * min(max(q, 0.0), 1.0)
        low, high = int(position), min(int(position) + 1, len(clean) - 1)
        out.append(clean[low] + (clean[high] - clean[low]) * (position - low))
    return tuple(out)


def pct_change(current, previous) -> float | None:
    """A fraction (0.12 = +12%), or None when there is no baseline to compare against."""
    a, b = num(current), num(previous)
    if a is None or b in (None, 0):
        return None
    return (a - b) / abs(b)
