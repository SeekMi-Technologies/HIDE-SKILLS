---
name: github-issues
description: Create, comment on, update, look up, or track GitHub issues/bugs/tasks. Use for any request to file, update, or check an issue on GitHub.
---
Target repository: a repository the user names always wins. Otherwise use the
default repository from your [Connected integrations] status. If none is set,
list repositories and ask which one — never guess.

Actions (pick the single most appropriate):
1. Create an issue (GITHUB_CREATE_AN_ISSUE) — a new task / bug / feature that isn't
   already open. Write a clear, specific title and a body capturing the request.
   If it looks like a follow-up, FIRST list open issues to avoid a duplicate.
2. Comment on an issue (GITHUB_CREATE_AN_ISSUE_COMMENT) — a follow-up or update on an
   existing issue. Find its number first (list / get, or prior context).
3. Update an issue (GITHUB_UPDATE_AN_ISSUE) — retitle, edit the body, close or
   reopen. This pauses for the user's confirmation; state exactly what will change.
4. List issues (GITHUB_LIST_REPOSITORY_ISSUES) — to locate an issue or report status.
5. Search issues and PRs (GITHUB_SEARCH_ISSUES_AND_PULL_REQUESTS) — find by keywords
   across titles/bodies when the number isn't known (qualify with repo:owner/name).
6. Get an issue (GITHUB_GET_AN_ISSUE) — to read details before acting.

Rules:
- One create OR one comment per request — never both, never duplicates.
- After a create, comment, or update, state what you did and include the issue URL.
- If a GitHub tool is unavailable, say so — never pretend you used it.
