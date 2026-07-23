---
name: inspect-trace
description: "Read when asked why a trace failed, how the bot performed, or to review Langfuse traces/scores — analysis, not grading."
---

# Inspect traces — on-demand analysis

A human is asking what happened: "why did this trace fail", "how did the bot do
today", "show me the worst traces this week". Your job is explanation grounded in
evidence, not scoring. You do NOT write scores here — if asked to actually grade,
read the `grade-traces` skill and follow its rubric instead.

## How

- One specific trace: `langfuse_read_trace(trace_id)` → walk through what the user
  asked, what the agent did (tool by tool), where it went wrong or right. Quote the
  actual tool results, not your impression of them. If the question is about the
  aftermath ("did the user get what they wanted"), read the next trace in that
  environment for the user's reaction.
- A period ("today", "this week"): `langfuse_find_traces(environment, minutes_back)`
  for the raw activity; `listScores {"limit": 100, "name": ["judge_pass"],
  "environment": ["<env>"]}` for what the grading routine already concluded — lead
  with those verdicts instead of re-judging from scratch, and read only the traces
  worth explaining (failures, or whatever the human pointed at).
- Aggregates (counts, costs, latency): `queryMetrics` — check `getMetricsSchema`
  first if unsure of the shape.

## Vocabulary

Use the same failure words the grading routine writes, so scores and your analysis
line up: `incomplete` (no real reply delivered), `false_success` (claimed success
that didn't satisfy the user), `wrong_target` (right action, wrong entity/person),
`fabricated_result` (invented specifics), `off_task`, `unapproved_action`.

## Bounds

- Read-only: never create, update, or delete anything in Langfuse from this skill.
- Be selective: read the few traces that answer the question, not everything the
  period contains; ≤2 follow-up reads per trace you explain.
- Answer with a conclusion first, evidence second, trace urls for anything you cite.
