---
name: grade-traces
description: "Check conversation quality: grade recent agent traces in Langfuse, write judge scores, report failures."
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
exactly those ids with this rubric, skipping discovery and quota.)

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

## No state — everything derives from the scores

This routine keeps NO saved state. The scores already written to Langfuse are the
only record, and every question answers itself with one read:

- **Graded already?** `listScores {"limit": 100, "name": ["judge_pass"],
  "traceId": [<candidate ids>]}` — any id that comes back is done. This also makes a
  quota-truncated batch resume by itself: what wasn't graded is still unscored, so
  the next fire picks it up.
- **Daily quota used?** `listScores {"limit": 100, "name": ["judge_pass"],
  "fromTimestamp": "<today 00:00:00Z>"}` — the number of scores returned is today's
  count. 50 or more → `report_nothing`, stop.
- **Freshly-written scores are NOT immediately readable** (the API lags creation by
  up to a couple of minutes) — never re-query to verify your own writes; a
  successful createScore response is the confirmation.

## Workflow per fire

1. Quota check (above). At or over 50 → `report_nothing`, stop.
2. Per environment named in the goal: `langfuse_find_traces(environment=<env>,
   minutes_back=180)`. Ignore traces started in the last 20 minutes — observation
   data lags ~15 min and young traces may still be growing.
3. Keep only real agent turns (names `commander_turn`, `task_run`); drop infra
   traces (`mem0.write`, `session.fold`, no user request), already-graded ids
   (dedup above), and this grading routine's own runs (a trace whose request is
   this very goal — drop without scoring).
4. Batch = up to 10 across all envs, oldest first. Empty → `report_nothing`, stop.
5. Per trace: `langfuse_read_trace(trace_id)`, walk the checklist, then write the
   verdict with ONE call:

   ```
   langfuse_write_judgement(trace_id="<id>", passed=false,
       failure_mode="incomplete",
       comment="<see below>", flags="turns-wasted")
   ```
   It writes both judge scores in the trace's own environment and returns the trace
   url. `passed=true` requires `failure_mode="none"`; any real mode requires
   `passed=false` — inconsistent verdicts are rejected, fix and retry once.

   The `comment` is the improvement signal the team (and automated prompt tuning)
   learns from — write it accordingly:
   - Passing trace: one sentence naming the deciding evidence.
   - Failing trace: two or three sentences — what concretely went wrong, the
     evidence, and what the correct behaviour would have been.
6. Digest (this reply is what the team reads, ≤15 lines): graded/passed counts per
   env, failure modes seen, each failed trace as `<mode>: <one-line why> — <url>`
   (createScore returns the url). No tables of passing traces, no rubric recitation,
   no trend analysis — that is `inspect-trace`'s job on demand.

## Bounds

- Trace content ONLY through `langfuse_find_traces` / `langfuse_read_trace` — never
  attempt raw observation pulls; full payloads run megabytes and will blow up the
  context.
- ≤10 traces per fire, ≤50 per day, ≤2 evidence reads per trace, no re-reads.
- You only ever CREATE scores. Never delete or update anything in Langfuse.
- A tool failing twice in a row → stop, report the error in the digest instead of
  improvising raw API calls.
