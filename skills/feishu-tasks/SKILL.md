---
name: feishu-tasks
description: Create, update, remind, assign, complete Feishu tasks/待办. Use for any 任务/task/todo/提醒 request.
commands: ["task +create", "task +update", "task +assign", "task +reminder", "task +tasklist-create", "task +tasklist-members", "task +complete"]
summary:
  zh: "建待办、指派给人、设提醒、标记完成"
  en: "Create Feishu tasks, assign them, set reminders, and close them"
---
Commands (grammar verified live against the pinned lark-cli 1.0.63; open_ids come
from the [Team directory] block — never guessed, never from im +chat-search):

- STEP 0 before EVERY create, including the second one in the same conversation —
  get the tasklist guid from ["task", "tasklists", "list"]. Reuse the list that is
  already there; only when the bot has none, create one:
  ["task", "+tasklist-create", "--name", "<short topic name>", "--member", "<ou_requester>"]
  Re-run the list rather than trusting memory of an earlier turn — a task created
  without the guid is the one failure this skill cannot recover from.
  When REUSING a list: ["task", "tasklists", "get", "--tasklist-guid", "<guid>"] and
  check the requester's open_id is in `members`; if not,
  ["task", "+tasklist-members", "--tasklist-id", "<guid>", "--add", "<ou_requester>"] —
  someone outside the list cannot see its tasks.
- Create: ["task", "+create", "--summary", "<title>", "--assignee", "<ou_requester>",
  "--tasklist-id", "<guid from STEP 0>", "--due", "2026-07-30",
  "--description", "<text>", "--idempotency-key", "<stable-key>"]
  HARD RULE 1: always pass --assignee with the requester's open_id (plus anyone they
  name). A bot-created task with no assignee is INVISIBLE in everyone's task app.
  HARD RULE 2: always pass --tasklist-id. The list is the only handle the bot keeps on
  a task; one created outside it is unreadable afterwards.
  HARD RULE 3: ok:true is NOT proof the person got the task. An open_id the API does
  not recognize is SILENTLY DROPPED (worst case the assignee becomes the app itself,
  invisible to every human). After create/assign/member changes, read back —
  ["task", "tasks", "get", "--task-guid", "<guid>"] — and confirm the requester's
  open_id really appears in `members` before reporting success.
- Update title/desc/due: ["task", "+update", "--task-id", "<guid>", "--due", "2026-07-27"]
  Members can NOT be updated here (the API rejects members as an update field) — use +assign.
- Members: ["task", "+assign", "--task-id", "<guid>", "--add", "<ou_a,ou_b>"] (--remove to drop).
- Reminder: ["task", "+reminder", "--task-id", "<guid>", "--set", "1d"]
  --set is RELATIVE TO THE DUE TIME (15m/1h/1d = that long BEFORE due), never an
  absolute moment. Ensure the task has a due first, then pick the offset
  (e.g. due Sunday + "周六晚上提醒我" → --set 1d).
- Complete / reopen: ["task", "+complete", "--task-id", "<guid>"] / ["task", "+reopen", ...]
- Read one task: ["task", "tasks", "get", "--task-guid", "<guid>"] — there is NO +get-task.

--due takes ISO 8601 ("2026-07-30" or "2026-07-30T15:04:05+08:00") or a ms timestamp.
The --help ALSO advertises "date:YYYY-MM-DD" and "relative:+2d"; both are rejected at
runtime by this CLI version ("failed to parse due time"). Do not use them.

Reading tasks back ("我的待办 / 有哪些任务 / 我有哪些待办") — ALWAYS bot, TWO steps:
  1. ["task", "tasklists", "list"] → the tasklist guid(s). Note the PLURAL `tasklists`;
     `tasklist list` (singular) is not a command and errors.
  2. ["task", "tasklists", "tasks", "--tasklist-guid", "<guid>"] for each list. The list
     is SHARED across the whole team, so this returns EVERYONE's tasks — you MUST filter
     client-side by assignee. Each task carries a `members` array; an assignee is an
     entry with role "assignee" whose `id` is that person's open_id:
       · "我的待办 / 我有哪些待办" → keep only tasks assigned to the REQUESTER (match the
         speaker's own open_id). Do NOT report other people's tasks as theirs.
       · "<某人>的待办" → filter by that person's open_id instead.
       · no person named ("清单里有哪些任务") → list them all.
     Report each kept task's summary, assignee, due and completion state.
Those two steps are the whole read path — the bot owns the tasklist, so "我的 / 我有"
is answered by filtering it on the speaker's open_id. `task --help` also advertises
+get-my-tasks, +get-related-tasks and +search, which read like a shortcut and the bot
cannot use; ["task", "tasks", "list"] returns only what the BOT is responsible for, and
every task here is assigned to a human, so it comes back empty. A task that predates
STEP 0 sits outside the list — say it is not in the list.

Traps (each one observed live):
- +get-task, +delete, +list, +create-reminder, +delete-tasklist, +tasklist-delete do
  not exist. Deleting a task is ["task", "tasks", "delete", "--task-guid", "<guid>"];
  deleting a whole tasklist is ["task", "tasklists", "delete", "--tasklist-guid",
  "<guid>"] (plural `tasklists`, raw command — no + prefix).
  ISSUE THAT COMMAND. Its --help says high-risk-write / needs confirmation — that
  confirmation is handled for you once you call it; it is NOT an instruction to stop.
  Never add --yes yourself, and never report a deletion (or any change) you did not
  actually execute — reading --help is not doing the work.
- Every guid you pass came verbatim from a `tasklists list` / `tasks get` response in
  THIS conversation — a UUID like 9c70…-…-…. Applink URLs and base64 blobs are not
  guids; the API rejects them ("Correct format: a valid uuid format").
- +tasklist-search is user-identity-only and its error suggests --as user, which is
  also unavailable — the whole search path is a dead end; find lists via
  ["task", "tasklists", "list"].
- Values go through flags only — positional arguments are rejected.
- Bot identity cannot add members across tenants (tenant_access_token scope).

Rare surfaces — sections, subtasks, custom fields, comments, followers, attachments,
task hierarchy — are in references/task-advanced.md; read it only when a request needs
one. For a task need neither here nor there covers, say what you cannot do and stop.
