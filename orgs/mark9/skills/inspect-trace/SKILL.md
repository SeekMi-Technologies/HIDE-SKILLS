---
name: inspect-trace
description: "When someone pastes bot output or asks why a reply was off/failed — locate the trace, explain with evidence."
---

# Inspect traces — find what happened and explain it

The typical ask is NOT a trace id. It is a human pasting a fragment — part of what
they typed, or part of what the bot answered — and saying "this is off, check it".
Your job: locate the actual trace, then explain what really happened, grounded in
the evidence inside it. You analyze; you never write scores (if asked to grade,
read the `grade-traces` skill and follow its rubric).

## Locating the trace

What you need before searching: **which environment** and **roughly when**. If the
message doesn't say, ASK — one short question covering both at once, in the user's
language, and offer the likely default: a complaint about THIS bot's own behaviour
almost always means this deployment's own environment. A vague time ("just now",
"this morning", "last night") is precise enough — never demand exact times, and
never guess a window silently when the user said nothing.

Then funnel, cheapest first:

1. `langfuse_find_traces(environment=<env>, minutes_back=<window covering the stated
   time>)` — candidates are the real agent turns (`commander_turn`, `task_run`)
   near the stated time.
2. `langfuse_read_trace` the closest candidates and match the pasted fragment
   against the user request and final reply in each transcript. The paste is often
   partial, reformatted, or quoted from Feishu — match meaning, not exact bytes.
3. Read at most 5 candidates. No match → tell the user what window you searched and
   ask them to narrow (a longer paste, a closer time, a different env) — do NOT
   silently widen the window and keep burning reads.
4. Two plausible matches → show both one-liners with start times and ask which.

Given an explicit trace id, skip all of this and read it directly.

## Explaining

- Walk what actually happened: what the user asked, what the agent did tool by
  tool, where it went wrong or right. Quote the actual tool results, not your
  impression of them.
- If the question is about the aftermath ("did it really work?"), read the next
  trace in that environment for the user's reaction.
- If the grading routine already scored the trace, lead with its verdict
  (`listScores {"limit": 100, "name": ["judge_pass"], "traceId": ["<id>"]}`) and
  then explain — don't re-judge from scratch.
- Name failures with the same words the grading routine writes, so analysis and
  scores line up: `incomplete` (no real reply delivered), `false_success` (claimed
  success that didn't satisfy the user), `wrong_target` (right action, wrong
  entity/person), `fabricated_result` (invented specifics), `off_task`,
  `unapproved_action`.
- For aggregate questions ("how did the bot do this week"): `listScores` with
  `fromTimestamp` for verdicts, `queryMetrics` for counts/cost/latency
  (`getMetricsSchema` first if unsure of the shape).

## Bounds

- Trace content ONLY through `langfuse_find_traces` / `langfuse_read_trace` — never
  attempt raw observation pulls; full payloads run megabytes and will blow up the
  context. There is no content-search tool: locating is always find + read + match.
- Read-only: never create, update, or delete anything in Langfuse from this skill.
- ≤5 candidate reads while locating, ≤2 follow-up reads while explaining.
- Answer with the conclusion first, evidence second, and the trace url for anything
  you cite.
