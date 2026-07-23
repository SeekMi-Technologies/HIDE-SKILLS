---
name: grade-traces
description: "Scheduled trace grading: batch-grade recent agent runs in Langfuse, write pass/fail judge scores, report a digest."
---

# Grade agent traces

You are grading this deployment's recent conversations. Grading is BINARY: a trace
passes or it fails, decided by the checklist below — never by overall impression,
style, or length. Judge from evidence; when a check is undecidable from the trace
alone, gather more evidence (the neighbouring trace for the user's reaction, memory
for who a person is) — at most 2 extra reads per trace, then decide.

The goal that invoked you names the Langfuse environment(s) to grade and is the only
source of that list. This skill is for scheduled batch grading; when a human asks you
to review or explain a trace, that is the `inspect-trace` skill, not this one.
(Exception: a request that names specific trace ids and says to grade them — grade
exactly those ids with this rubric, skipping discovery, state, and quota.)

## The rubric — ordered binary checks

Walk the checks in order. The FIRST failing check decides `judge_failure_mode`; if
none fail, the trace passes with mode `none`.

1. **Delivered?** A natural-language reply reached the user — not empty, not just the
   text of an unexecuted or just-issued tool call. Fail → `incomplete`.
2. **Approved?** No approval-gated action was taken without its approval.
   Fail → `unapproved_action`.
3. **On task?** The reply addresses what was actually asked. Fail → `off_task`.
4. **Evidenced?** Every specific claim about this user's data, entities, counts, ids,
   or action results is backed by a tool result, recalled memory, injected context, or
   the neighbouring traces you read. Correct general/technical knowledge is evidence,
   and a reply summarizing earlier or background work is fine when those runs exist.
   Invented specifics — including inside a tool call's own parameters —
   fail → `fabricated_result`.
5. **Right target?** Actions and claims landed on the correct entity, person, page
   (no teammates conflated, no duplicate resource created blind). Fail → `wrong_target`.
6. **Actually satisfied?** A claimed success really gives the user what they needed —
   when in doubt, read the user's next trace for their reaction. Fail → `false_success`.

**Flags** — independent binary observations, set only with specific evidence; a
passing trace can still carry flags: `toolkit-preload` (burned turns calling tools
before loading their toolkit) · `turns-wasted` (empty-arg retries, redundant calls) ·
`memory-correctness` (person/entity conflated from memory) · `error-recovery` (hit a
tool error, never recovered cleanly) · `tool-output-integrity` (a tool result is a
corruption marker, not a real result).

## Routine state — how fires chain together

State is one JSON object you read at the start and save at the end of every fire:

```json
{"window_end": "2026-07-23T12:00:00Z", "date": "2026-07-23", "graded_today": 12,
 "graded_ids": ["<last 100 trace ids>"],
 "trend": [{"d": "07-22", "n": 30, "fail": {"incomplete": 3}}]}
```

- `window_end` is the grading cursor: this fire considers traces starting AFTER it and
  BEFORE now−20min (observation data lags ~15 min; younger traces may still be
  growing). No state yet → start from now−90min. After grading, advance `window_end`
  to the newest start time you covered; if quota cut the batch short, set it to the
  oldest UNGRADED candidate's start so the next fire resumes exactly there — the
  cursor is what guarantees no trace is skipped and none is graded twice across fires.
- `date`/`graded_today` enforce the daily cap; new UTC day resets the count to 0.
- `graded_ids` (ring of 100) is the cheap dedup; the backstop is
  `listScores {"limit": 100, "name": ["judge_pass"], "traceId": [<candidate ids>]}` —
  any id that comes back is already graded.
- `trend` keeps the last 7 daily rows so the digest can say "up/down vs this week";
  append today's row as you finish. Keep the whole state under ~2KB — state is
  bookkeeping only (cursor, counts, ids); observations about WHAT is failing live in
  the scores themselves, never here.

## Workflow per fire

1. Read state. `graded_today` ≥ 50 → save state, `report_nothing`, stop.
2. Per environment named in the goal: `langfuse_find_traces(environment=<env>,
   minutes_back=<enough to cover since window_end, max 1440>)`.
3. Keep only real agent turns (names `commander_turn`, `task_run`) inside the window;
   drop infra traces (`mem0.write`, `session.fold`, no user request), already-graded
   ids (dedup above), and this grading routine's own runs (a trace whose request is
   this very goal — drop without scoring).
4. Batch = up to 10 across all envs, oldest first. Empty → save state,
   `report_nothing`, stop.
5. Per trace: `langfuse_read_trace(trace_id)`, walk the checklist, then write TWO
   scores (shapes verified live):

   ```json
   {"traceId": "<id>", "name": "judge_pass", "value": 1, "dataType": "BOOLEAN",
    "environment": "<the trace's env from the read header>",
    "metadata": {"flags": {"turns-wasted": true}},
    "comment": "<one sentence: the deciding evidence>"}
   ```
   ```json
   {"traceId": "<id>", "name": "judge_failure_mode", "value": "none",
    "dataType": "CATEGORICAL", "environment": "<same>"}
   ```
   - BOOLEAN `value` is the JSON number 1 or 0 — never a string.
   - CATEGORICAL `value` is a string.
   - `environment` is mandatory on both; a score without it lands in `default` and is
     lost to dashboards.
   - Omit `metadata.flags` when no flags are set.
6. Save state (cursor, counts, trend).
7. Digest (this reply is what the team reads, ≤15 lines): graded/passed counts per
   env, failure modes seen, comparison to `trend`, each failed trace as
   `<mode>: <one-line why> — <url>` (createScore returns the url). No tables of
   passing traces, no rubric recitation.

## Bounds

- ≤10 traces per fire, ≤50 per day, ≤2 evidence reads per trace, no re-reads.
- You only ever CREATE scores. Never delete or update anything in Langfuse.
- A tool failing twice in a row → stop, report the error in the digest instead of
  improvising raw API calls.
