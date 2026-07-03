---
name: github-issues
description: Create, comment on, look up, or track GitHub issues/bugs/tasks. Use for any request to file, update, or check an issue on GitHub.
---
Target repository: use the owner/repo given in your instructions. NEVER any other
repository.

Actions (pick the single most appropriate):
1. Create an issue (GITHUB_CREATE_AN_ISSUE) — a new task / bug / feature that isn't
   already open. Write a clear, specific title and a body capturing the request.
   If it looks like a follow-up, FIRST list open issues to avoid a duplicate.
2. Comment on an issue (GITHUB_CREATE_AN_ISSUE_COMMENT) — a follow-up or update on an
   existing issue. Find its number first (list / get, or prior context).
3. List issues (GITHUB_LIST_REPOSITORY_ISSUES) — to locate an issue or report status.
4. Get an issue (GITHUB_GET_AN_ISSUE) — to read details before acting.

Rules:
- One create OR one comment per request — never both, never duplicates.
- After a create or comment, state what you did and include the issue URL.
- If a GitHub tool is unavailable, say so — never pretend you used it.
