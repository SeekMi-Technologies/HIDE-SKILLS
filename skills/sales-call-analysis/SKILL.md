---
name: sales-call-analysis
description: Analyze stored call transcripts — one call in depth, one salesperson's calls over time, or a cross-person comparison. Use when someone asks how a call went, what a rep keeps doing on calls, coaching questions, or team-level call patterns.
summary:
  zh: "销售通话分析——单通复盘、按人批量、跨人对比"
  en: "Sales call analysis — single call, per-rep batch, cross-rep comparison"
---
Transcripts live as artifacts; RBAC already decides what the asker may see (a rep sees
their own calls, a supervisor sees everyone's). If a tool answers with a permission
refusal, relay it — never work around it.

Finding calls:
- list_artifacts() — everything the asker may read, newest first, one line per call
  with date, duration, speaker stats and a one-line summary.
- list_artifacts(person="me") / list_artifacts(person="<person id from the Team
  directory>") — one rep's calls. Resolve names via the directory; never guess ids.

Reading efficiently — the numbers come free, the words cost reads:
- Every artifact card and listing line already carries duration, per-speaker talk
  share and turn counts. Talk-ratio, who-dominates, call-length questions need ZERO
  read_artifact calls — answer from the cards.
- Content questions (objections raised, pricing discussion, next steps, how an
  objection was handled): read_artifact(id) for the outline, then read only the
  sections you need. Sections are ~5 minutes each; quote at most a few lines.

The three shapes:
1. Single call: outline first, then the sections that matter (opening, objection,
   close). Deliver: what went well / what to improve / concrete next step, each
   grounded in a quoted moment with its timestamp.
2. One rep, many calls: list their calls, compare the stats across cards (talk share
   trend, call length trend), then read 1–2 representative sections per call at most.
   Deliver a pattern, not a per-call retelling.
3. Cross-rep: needs supervisor-level access — list per person, compare the same
   metrics for everyone, and only then read sections from the outliers to explain WHY
   the numbers differ.

Delivering:
- A quick question → answer in chat, short, in the asker's language.
- A review someone will keep (coaching writeup, weekly call review) → write your
  analysis as the reply AND offer to publish the underlying transcript with
  attach_artifact; share the analysis doc only with the people the asker names.
- Never paste transcript bulk into chat or docs; reference sections ("s04, 15:00–20:00")
  so the reader can pull the source themselves with read_artifact.
- Speaker labels are diarization ids (speaker_0…speaker_N, sometimes more ids than
  people). Infer who is the rep from content (greetings, company name) and SAY which
  label you inferred as whom — never silently assume.
