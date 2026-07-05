---
name: github-repos
description: Explore GitHub repositories — list or find repos, browse files and branches, read code and READMEs, search code, inspect pull-request details. Use when the user asks what repos exist, what's in a repo, or for PR/code specifics.
---
Target repository: a repository the user names always wins. Otherwise use the
default repository from your [Connected integrations] status. If none is set,
list repositories (GITHUB_LIST_REPOSITORIES_FOR_THE_AUTHENTICATED_USER) and ask
which one — never guess.

Discover repositories:
- GITHUB_LIST_REPOSITORIES_FOR_THE_AUTHENTICATED_USER — the connected account's
  repos (sort=pushed for the active ones). Use this to answer "what repos do we
  have?" and to offer choices when the target is unclear.
- GITHUB_LIST_ORGANIZATION_REPOSITORIES — an organization's repos (needs the org name).
- GITHUB_SEARCH_REPOSITORIES — find by name/topic/language across GitHub.

Read a repository:
- GITHUB_GET_A_REPOSITORY — metadata: default branch, description, visibility.
- GITHUB_GET_A_REPOSITORY_README — the front-door summary; read it first for
  "what is this repo?" questions.
- GITHUB_GET_A_TREE (recursive) — the file layout; GITHUB_GET_REPOSITORY_CONTENT —
  one file or directory's contents.
- GITHUB_GET_A_BRANCH / GITHUB_LIST_BRANCHES — branch heads.
- GITHUB_SEARCH_CODE — find code by content (qualify with repo:owner/name).

Pull-request depth (read-only):
- GITHUB_LIST_PULL_REQUESTS_FILES — what a PR changes.
- GITHUB_LIST_REVIEWS_FOR_A_PULL_REQUEST / GITHUB_LIST_REVIEW_COMMENTS_ON_A_PULL_REQUEST
  — review state and feedback.
- GITHUB_LIST_COMMITS_ON_A_PULL_REQUEST — the PR's commit trail.
- GITHUB_CHECK_IF_PULL_REQUEST_HAS_BEEN_MERGED — merged or not, definitively.

Rules:
- Everything here is READ-ONLY; issue writes belong to github-issues.
- Fetch only what the question needs — a targeted file read beats a recursive tree
  of a large repo; never dump raw file contents unless asked for the code itself.
- When several repos plausibly match, show the candidates and ask — one clarifying
  question beats a wrong-repo answer.
