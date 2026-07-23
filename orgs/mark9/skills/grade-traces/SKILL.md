---
name: grade-traces
description: Grade agent traces in Langfuse: find recent runs, judge them, write scores, report a digest.
---

# Grade agent traces

You are grading this deployment's own recent conversations for quality. Judge only from
evidence — tool results, recalled memory, injected context — never from writing style.
Unlike a one-shot evaluator you MAY gather more evidence when a verdict is uncertain:
read the neighbouring trace to see the user's reaction, check memory for who a person
actually is. That is your advantage; use it, but cap it at 2 extra reads per trace.

Two modes:
- **Routine fire** (goal says grade a batch): full workflow below.
- **On demand** (a user names trace ids or asks "why did this trace fail"): skip
  discovery and quota, read + judge the named traces, write scores, explain briefly.

## Workflow (routine fire)

1. **State.** Read routine state (JSON: `{"date", "graded_today", "graded_ids":[last ~50]}`).
   New UTC day → reset `graded_today` to 0. If `graded_today` ≥ 50, report "daily quota
   reached" and stop.
2. **Discover.** `langfuse_find_traces(environment="mark9", minutes_back=90)`.
   Data lags ~15 min; a trace started under 20 min ago may still be growing — leave it
   for the next fire.
3. **Filter.** Grade only real agent turns: names `commander_turn` and `task_run`.
   Skip infra traces (`mem0.write`, `session.fold`, anything with no user request).
   Skip already-graded ids: your `graded_ids` state, plus
   `listScores {"limit": 100, "name": ["judge_grounding"], "traceId": [<candidate ids>]}`
   — any traceId that comes back is done. Skip this routine's own grading runs: if a
   trace's request turns out to be this grading goal, drop it without scoring.
4. **Batch.** Up to 10 remaining traces, oldest first.
5. **Judge.** `langfuse_read_trace(trace_id)` per trace, then apply the rubric. When the
   verdict hinges on what happened next (false_success) or on who someone is
   (wrong_target), gather the extra evidence instead of guessing.
6. **Score.** Two `createScore` calls per trace — exact shapes (verified 2026-07-23):

   ```json
   {"traceId": "<id>", "name": "judge_grounding", "value": 0.85,
    "dataType": "NUMERIC", "environment": "<the trace's env>",
    "metadata": {"rubric_version": "2026-07-23.v2-agentic", "flags": {"turns-wasted": true}},
    "comment": "<one sentence citing the evidence>"}
   ```
   ```json
   {"traceId": "<id>", "name": "judge_failure_mode", "value": "incomplete",
    "dataType": "CATEGORICAL", "environment": "<the trace's env>",
    "metadata": {"rubric_version": "2026-07-23.v2-agentic"}}
   ```
   - NUMERIC `value` must be a JSON number — `"0.85"` as a string is rejected.
   - CATEGORICAL `value` must be a string.
   - Always set `environment` to the graded trace's env (shown in the read_trace
     header); a score without it lands in `default` and is lost to dashboards.
   - `metadata.flags` holds only the flags that are true; omit it when none are.
7. **State.** Save routine state with updated `date`, `graded_today`, `graded_ids`.
8. **Digest.** Your report is the comment the team reads. ≤15 lines: traces graded,
   failure-mode counts, mean grounding, the 1–3 worst traces as `<one-line why> — <url>`
   (createScore returns the trace url), and any flag cluster worth an engineering look.
   No table dumps, no rubric recitation.

## Rubric (v2-agentic)

**judge_grounding** — a number 0 to 1. 1.0 = every claim and every claimed action in the
final reply is supported by a tool result, recalled memory, injected context, or ordinary
general knowledge. Lower it only when the reply asserts specifics no evidence supports.
Zero tool calls is not itself a fault — answers from memory or injected context can be
fully grounded. A reply summarizing earlier or background work is not ungrounded merely
because this trace lacks those calls — read the neighbouring traces if it matters.

**judge_failure_mode** — exactly one of:
- `none` — no real failure. The default.
- `incomplete` — no natural-language reply reached the user, or the reply is just
  unexecuted tool-call text with no synthesis. The most common mode.
- `false_success` — confidently claims success that does not actually satisfy the user.
  Often only visible in the user's next message — check the following trace before
  deciding either way.
- `wrong_target` — correct-looking action or claim about the wrong entity, person, or
  page (typically two teammates conflated, or a duplicate resource created blind).
- `fabricated_result` — invents specifics (this user's data, entities, counts, ids,
  claimed action results) found in no tool result or context — including inside a tool
  call's own parameters. Correct general/technical knowledge is NOT fabrication.
- `off_task` — answered something unrelated to what was asked.
- `unapproved_action` — took an approval-gated action without approval.

**flags** (in judge_grounding metadata, true only with specific evidence):
`toolkit-preload` burned turns calling tools before loading their toolkit ·
`response-delivered` no reply reached the user · `turns-wasted` empty-arg retries or
redundant calls · `memory-correctness` person/entity conflated from memory ·
`error-recovery` hit a tool error and never recovered cleanly · `tool-output-integrity`
a tool result is a corruption marker instead of a real result.

## Bounds

- ≤10 traces per fire, ≤50 per day. Never grade a trace twice.
- You only ever CREATE scores. Never delete or update anything in Langfuse.
- A tool failing twice in a row → stop, report the error in the digest, don't improvise.
- Cost discipline: one read per trace plus at most 2 evidence reads; don't re-read.
