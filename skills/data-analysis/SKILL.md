---
name: data-analysis
description: Analyse a data file someone sent — a CSV, TSV, JSON or text export — by writing Python that reads it, and hand back numbers, a file or a chart. Read this the moment a message carries a data file, or someone asks you to count, total, group, rank, compare or chart something in one. NOT for audio (feishu-transcribe owns that).
scopes: ["im:resource", "docx:document", "drive:drive"]
commands: ["docs +create", "docs +media-insert", "drive +member-add"]
---
Three tools, in this order: `read_attachment` puts the file on disk, `run_python` reads it
and computes, `stage_artifact` hands a produced file back to the Feishu tools.

## The one rule that matters

**OPEN THE FILE. Never retype its contents into your program.**

`read_attachment` deliberately shows you a *schema* — column names, a row count, two or
three sample rows — and not the data. That is not a limitation to work around by asking
for more; it is the point. The file is already on disk and stays there for the whole
conversation.

```python
import csv
with open("/var/lib/hl/code-exec/<...>/scores.csv") as fh:      # the `path` you were given
    rows = list(csv.DictReader(fh))
```

Measured on 2026-08-22: a model shown a 46-row preview transcribed all 46 values as Python
literals into six separate programs, ~3 000 characters each, and never called `open()`.
Every number went through the model on every call, the conversation's rolling summary
overflowed twice, and the answers were no better than one `open()` would have given.

## The flow

  1. **Read the handles in the SAME turn they arrive.** `[attachment message_id=… file_key=…]`
     is gone once the conversation folds, and then nobody can get that file back.
  2. `read_attachment(message_id, file_key, file_name)` → `path`, `columns`, `rows_estimate`.
  3. `run_python(code, description)` — open the path, compute, `print()` the ANSWER.
  4. Only if they want a file or a picture: write it, then `stage_artifact(path)` using a
     path straight out of `artifacts`, then deliver it (below).

## Writing the program

- **Print the answer, not the data.** A program that prints its input wastes the turn and
  buries the result. Print totals, counts, the top N — never the corpus.
- **One program, not five.** Compute every figure you were asked for in a single call.
  Re-running to "check the path" or "see what I made" is a wasted turn: `run_python`
  already returns `artifacts` as full paths, and files persist for the conversation.
- **Say what you dropped.** Blank cells, unparseable dates, duplicate rows, a `0` that
  means "did not sit the exam" rather than "scored nothing" — name the count and what you
  did with it. A total presented as complete when it is not is worse than no total.
  If a `0` might mean "absent", give both figures and say which is which.
- **Assume every field is dirty, especially in an export.** A real Langfuse export broke
  two programs in a row this way: `judge_pass` was `[1]` (a list, so `Counter` raised
  `unhashable type: 'list'`) and `latencyMs` mixed numbers with strings (so
  `statistics.mean` raised `can't convert type 'str'`). Coerce at the edge, once:

  ```python
  def num(x):                      # for anything you will average or sum
      try:    return float(x)
      except (TypeError, ValueError): return None

  def key(x):                      # for anything you will count or group by
      return json.dumps(x, sort_keys=True) if isinstance(x, (list, dict)) else x

  values = [v for v in (num(r.get("latencyMs")) for r in rows) if v is not None]
  counts = collections.Counter(key(r.get("judge_pass")) for r in rows)
  ```

  Then report how many rows you had to skip. Guarding costs three lines; not guarding
  costs the whole program on row 900 of 3000, after it has printed half the answer.
- **Failures come back with the traceback.** Fix and retry ONCE. After two failures in a
  row, stop and report what broke.

## Available in the sandbox

`csv`, `json`, `statistics`, `datetime`, `re`, `collections`, `itertools`, `math`,
`decimal` — plus **numpy**, **pillow (PIL)**, **matplotlib** and **pypdf**.

pypdf is the PDF reader here. **PyMuPDF / `import fitz` is not installed** and will not be —
its licence rules it out — so do not spend a call discovering that.

No network. No access to your other tools.

### PDFs

`read_attachment` already tells you the page count and the first few hundred words, which
is often enough to answer "what is this document". To work with the whole thing:

```python
import pypdf
reader = pypdf.PdfReader(path)
text = "\n".join((page.extract_text() or "") for page in reader.pages)
```

Two things to know before you promise anything:

- **A PDF with no text layer is one you LOOK at, not one you extract.** When
  `read_attachment` finds no text it renders the first pages and attaches them to its own
  result as images — so the pages are already in front of you. Read the document from what
  you can see. Two rules: this is not OCR, so say plainly what is too small or too unclear
  to make out rather than guessing, and never invent a figure you cannot actually read. The
  PNGs sit on disk beside the PDF, so you can crop or scale one in `run_python` when a
  detail matters. Only if no pages came back is there nothing to be done — then say so and
  ask for a text-based PDF, and do NOT report the document as empty, which is what the raw
  extraction looks like.
- **"No text layer" is not the same as "a scan."** A design or a map exported with its text
  converted to outlines reads identically to a scan through pypdf. Describe what the pages
  actually show; do not tell someone their poster is a bad scan.
- **Tables come out as running text.** pypdf gives you a page's words in reading order,
  not cells. For a simple two-column layout, splitting lines on runs of whitespace usually
  works; for anything complicated, say what you can see and ask whether a CSV export
  exists. A confidently wrong table is worse than an honest "this needs the source data".

Quote page numbers when you cite something — `reader.pages` is zero-indexed, humans are not.

### Charts

matplotlib works. The backend is already `Agg` and the font cache already points somewhere
writable, so nothing needs configuring:

```python
import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=(7, 4))
ax.bar(labels, values)
ax.set_title("Q3 totals by region")
fig.savefig("q3.png", dpi=110, bbox_inches="tight")
```

**Chinese, Japanese or Korean labels need the CJK font named explicitly.** matplotlib's
default is DejaVu, which has no CJK glyphs, and it does not warn — it draws a chart full
of empty boxes:

```python
plt.rcParams["font.sans-serif"] = ["WenQuanYi Zen Hei"]
plt.rcParams["axes.unicode_minus"] = False        # or minus signs become boxes too
```

A chart costs about 70 MiB and a second or two, well inside the sandbox's limits — the
first one in a conversation is slower because the font cache is built once. Save PNG (it
displays inline in more places) unless someone asks for SVG.

Still true: if a picture would not actually help, say so and give a table. A clear table
beats a bad chart, and three numbers never needed a chart at all.

## Handing a file back

`stage_artifact(path)` moves it where the Feishu tools can see it and returns a short
relative path. Then deliver it as a normal write — for example create a doc and insert it:

```
["docs", "+create", "--title", "Q3 scores"]
["docs", "+media-insert", "--doc", "<doc id>", "--file", "<staged path>", "--type", "file"]
["drive", "+member-add", "--token", "<doc id>", "--member-id", "<their open_id>", "--perm", "edit"]
```

That is an ordinary write and pauses for confirmation if the policy says so. Do not try to
send the file any other way.

## When NOT to use this

- An audio recording → `feishu-transcribe`, always.
- A question you can answer from what is already in front of you → just answer it. Two
  numbers do not need a program.
- A file nobody asked you to do anything with → say what it looks like (name, size,
  columns) and ask. Never invent an analysis.
