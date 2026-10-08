---
name: data-analysis
description: Analyse a data file someone sent — CSV, TSV, JSON, PDF, Excel or a text export — by writing Python that reads it, and hand back numbers, a file or a chart; also compute over a toolkit read too big to page through, and install a missing library. Read this the moment a message carries a data file, someone asks you to count, total, rank or chart something, or run_python hits ModuleNotFoundError. NOT for audio (feishu-transcribe).
scopes: ["im:resource", "docx:document", "drive:drive"]
commands: ["docs +create", "docs +media-insert", "drive +member-add"]
summary:
  zh: "读取别人发来的数据文件，用 Python 算出结果、生成图表或文件"
  en: "Read a data file someone sent and compute over it with Python — figures, a chart or a file"
---
Three tools, in this order: `read_attachment` puts the file on disk, `run_python` reads it
and computes, `stage_artifact` hands a produced file back to the Feishu tools.

**If `run_python` is not in your tools, Code actions is switched off for this workspace**
(or this deployment has not been upgraded yet). Then none of this applies: say you cannot
open or compute over files here, describe what you can see (name, size, type), and offer
what you can do without code. Never pretend to have run an analysis.

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

**Excel is not preinstalled** — there is no openpyxl, xlrd or pandas out of the box. If
`install_package` is in your tools, install the reader (below): `openpyxl` for `.xlsx`,
`xlrd` for the old `.xls`. If not, ask for a CSV export (File → Save As → CSV in
Excel/WPS/Numbers) rather than trying.

No network, and no credentials. The program cannot `pip install` — the only ways out are
the bridge and `install_package`, both below.

## Installing a missing library (`install_package`)

Only when `install_package` is in your tools (Package installs switched on for this
workspace). If it is not, the sandbox is what it is: work with the list above, or say
what the task would need.

- **Install only for a real need.** A `ModuleNotFoundError`, an `.xlsx` to read, a format
  the standard library cannot parse. Do not install pandas to sum a column — `csv` and
  `statistics` do that, and they are what you write most reliably.
- **Name everything in ONE call.** `install_package(["openpyxl"])`, or
  `install_package(["pandas", "openpyxl"])` — `requirements` is a list, and one call is
  one install and at most one approval. Five one-package calls are five cards for a
  person to tap. Pin a version only when the task needs a specific one.
- **It may pause for approval.** Packages outside the workspace's allowlist wait on a
  card. That pause is the answer for this turn — do not retry, and do not try to work
  around it in code.
- **Read the result.** `installed` lists what landed, `already_available` what was there
  already. A refusal says why in one line — a conflict with an installed version (those
  cannot be upgraded or replaced: ask for a compatible version, or do without), no wheel
  for this sandbox (source-only packages never install), or not allowed (tell the person
  and stop). Say it plainly; do not guess at another package name to get around it.
- **Then import it as usual** in `run_python`. Installs last for this conversation only;
  in a new conversation, install again.
- A `note` about compiled extensions means a large library may fail to import with
  `MemoryError` under the sandbox's memory limit. If it does, say so rather than retrying.

```python
# after install_package(["openpyxl"])
from openpyxl import load_workbook
wb = load_workbook(path, read_only=True, data_only=True)   # data_only: values, not formulas
ws = wb.active
rows = list(ws.iter_rows(values_only=True))
header, body = rows[0], rows[1:]
print(wb.sheetnames, len(body))
```

`data_only=True` returns the values Excel last saved; a workbook never opened in Excel
may have formulas with no cached value — those come back as `None`, so say so rather than
reporting blanks as zeros. Name the sheet you used when there is more than one.

## Reading your tools from inside the program (the bridge)

When you load a toolkit and the result says its read-only tools are *also callable as
`hide.<toolkit>.<TOOL>(...)`*, the program can call them directly. Use it whenever a read
would be too big to page through the conversation — every issue in a repo, every page of
a list — and print only what you worked out:

```python
issues = hide.github.GITHUB_LIST_REPOSITORY_ISSUES(owner="o", repo="r", state="open", per_page=100)
```

Tool names are exactly the ones the load message listed, full prefix included.
Independent reads go in ONE round trip — the child makes one request at a time, so twelve
single calls are twelve serial waits:

```python
rows = hide.gather([
    (hide.github.GITHUB_LIST_REPOSITORY_ISSUES, {"owner": "o", "repo": "a"}),
    (hide.github.GITHUB_LIST_REPOSITORY_ISSUES, {"owner": "o", "repo": "b"}),
])
ok = [r for r in rows if not isinstance(r, Exception)]   # a failed read is an Exception in its slot
```

Pass the tool itself in `hide.gather`, not the result of calling it. Only reads work in
code: anything that writes or needs approval raises `NeedsApproval` (catch it, print what
you would have changed, then make that change as an ordinary tool call where the person
can confirm it). A tool the load message did not offer as `hide.…` is not reachable from
code — do not guess names.

## A file a tool only LINKED to

Some tools answer with a short-lived signed URL instead of the content — GitHub Actions
logs are the usual one. If `stage_url` is in your tools, pass the URL exactly as the tool
returned it, in the same turn (links expire), and the file lands on disk for `run_python`;
a zip is unpacked for you. If `stage_url` is not in your tools, fetching by URL is switched
off here — ask the tool for the content directly, or ask the person to send the file.

### PDFs

`read_attachment` already tells you the page count and the first few hundred words, which
is often enough to answer "what is this document". To work with the whole thing:

```python
import pypdf
reader = pypdf.PdfReader(path)
text = "\n".join((page.extract_text() or "") for page in reader.pages)
```

Two things to know before you promise anything:

- **A PDF with no text layer cannot be read here.** If `read_attachment` came back with
  `likely_scanned`, or `extract_text()` returns almost nothing, the pages are pictures of
  words. There is no OCR on this deployment and you cannot see the pages. Say so plainly
  and ask for a text-based PDF, or for the figures another way — do NOT report the document
  as empty, which is what the raw extraction looks like.
- **"No text layer" is not the same as "a scan."** A design or a map exported with its text
  converted to outlines reads identically to a scan through pypdf. So describe the limit
  honestly — "I can't get any text out of this file" — and do not tell someone their poster
  is a bad scan when you have no way of knowing what it is.
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
