---
name: github-standup
description: Summarize recent GitHub activity — "what did we ship", "my standup", progress reports from commits/PRs/issues. Read-only.
---
Target repository: use the owner/repo given in your instructions.

Window: unless the user names one ("last week", "since Monday"), summarize the LAST
24 HOURS — compute `since` from the [Current turn] time.

Scoping by author:
- Speaker's GitHub login known AND they ask for THEIR OWN standup ("my standup",
  "what did I do") → pass `author`/`creator` = that login.
- Otherwise (team ask, unknown login) → no author filter; summarize everyone.

Gather (reads only — you must not write anything):
1. Commits — GITHUB_LIST_COMMITS (`since`, `author` when personal); notable commit →
   GITHUB_GET_A_COMMIT for the full message + changed files.
2. Pull requests — GITHUB_FIND_PULL_REQUESTS (supports `author` + a query like
   "merged:>=<date>") or GITHUB_LIST_PULL_REQUESTS; GITHUB_GET_A_PULL_REQUEST for
   title + description.
3. Issues (optional) — GITHUB_LIST_REPOSITORY_ISSUES opened/closed in the window.

Read commit and PR MESSAGES; do NOT read or summarize source code or diffs.

Write the standup:
- Concise and skimmable, GROUPED by area/theme (never a raw commit dump); merge
  related commits into one line.
- Each item ends with its reference: short SHA (7 chars) or #PR.
- Nothing landed → say so plainly. NEVER invent activity the tools did not return.
