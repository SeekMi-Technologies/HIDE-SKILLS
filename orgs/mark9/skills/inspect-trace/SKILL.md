---
name: inspect-trace
description: "MUST read before investigating any bot reply or Langfuse trace — locate by content search, explain."
---

# Inspect traces — find what happened and explain it

The typical ask is a pasted fragment of a bot reply or user message plus "this
looks off, check it". Locate the actual trace, then explain what happened from
the evidence inside it. Analysis only — never write scores here; grading is the
`grade-traces` skill.

## Locate — content search first

**GATE:** you need the **environment** and **roughly when**. If the message
states neither, your ENTIRE reply is one short question asking both at once, in
the user's language — a complaint about THIS bot usually means its own
environment, and a vague time ("just now", "last night") is enough. This is not
politeness: content search requires a bounded time window.

1. Pick a short distinctive substring from the paste (8–20 chars; avoid emoji,
   markdown and links — re-formatting changes them).
2. `langfuse_find_traces(environment=<env>, minutes_back=<window start>,
   until_minutes_back=<window end>, containing=<substring>)` — the window
   brackets the stated time (e.g. "yesterday evening" ≈ 1560/1320). This
   searches both input and output server-side.
3. One hit → `langfuse_read_trace` it. Several → show their one-liners with
   start times and ask which. Zero → try ONE different substring; still zero →
   say plainly you could not find it and ask for a longer paste or closer time.
   Never fall back to browsing and reading everything when a content search can
   answer.
4. Given an explicit trace id, skip all of this and read it directly.

## Explain

- Conclusion first, evidence second: what the user asked, what the agent did
  tool by tool, where it went right or wrong. Quote the actual tool results,
  not your impression of them.
- **HARD RULE — no verdict without the trace.** Task records, memory, and prior
  scores help you FIND the trace; they are never a substitute for reading it.
  Declaring a reply "fabricated" or "failed" based on a different run of a
  similar task is a false accusation and the worst possible output here.
- Aftermath questions ("did it really work?") → read the next trace in that
  environment for the user's reaction.
- Already graded? `listScores {"limit": 100, "name": ["judge_pass"],
  "traceId": ["<id>"]}` — lead with the routine's verdict, then explain.
- Name failures with the grading vocabulary (`incomplete`, `false_success`,
  `wrong_target`, `fabricated_result`, `off_task`, `unapproved_action`) so
  analysis and scores line up.

## Cost & latency

- `langfuse_read_trace`'s header carries the trace's own numbers
  (`cost=$…  wall=…s`) — quote them whenever the question touches speed or
  spend.
- Aggregates and rankings ("slowest today", "spend this week", "most expensive
  traces") → `queryMetrics`, checking `getMetricsSchema` first when unsure of
  the shape. Compare a trace against the period's typical numbers before
  calling it expensive or slow.

## Bounds

- Trace content ONLY through `langfuse_find_traces` / `langfuse_read_trace` —
  never raw observation pulls.
- Read-only: never create, update, or delete anything in Langfuse from this
  skill.
- ≤3 candidate reads while locating, ≤2 follow-up reads while explaining, trace
  urls for anything you cite.
