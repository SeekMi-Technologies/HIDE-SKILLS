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
- **Failures come back with the traceback.** Fix and retry ONCE. After two failures in a
  row, stop and report what broke.

## Available in the sandbox

`csv`, `json`, `statistics`, `datetime`, `re`, `collections`, `itertools`, `math`,
`decimal` — plus **numpy** and **pillow (PIL)**.

No network. No access to your other tools. **matplotlib is NOT installed** — for a chart,
either draw it with PIL (`ImageDraw`: a bar or histogram is a loop over rectangles) or
write an SVG by hand with string formatting. Both work; SVG is smaller and scales, PNG
displays inline in more places. Ask which they want if it matters, and if a picture is not
worth the effort, say so and give a table instead — a clear table beats a bad chart.

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
