---
name: feishu-tasks
description: Create, update, remind, assign, complete Feishu tasks/待办. Use for any 任务/task/todo/提醒 request.
commands: ["task +create", "task +update", "task +assign", "task +reminder", "task +tasklist-create"]
---
Commands (grammar verified live against the pinned lark-cli 1.0.63; open_ids come
from the [Team directory] block — never guessed, never from im +chat-search):

- STEP 0 before EVERY create, including the second one in the same conversation —
  get the tasklist guid from ["task", "tasklists", "list"]. Reuse the list that is
  already there; only when the bot has none, create one:
  ["task", "+tasklist-create", "--name", "<short topic name>", "--member", "<ou_requester>"]
  Re-run the list rather than trusting memory of an earlier turn — a task created
  without the guid is the one failure this skill cannot recover from.
- Create: ["task", "+create", "--summary", "<title>", "--assignee", "<ou_requester>",
  "--tasklist-id", "<guid from STEP 0>", "--due", "2026-07-30",
  "--description", "<text>", "--idempotency-key", "<stable-key>"]
  HARD RULE 1: always pass --assignee with the requester's open_id (plus anyone they
  name). A bot-created task with no assignee is INVISIBLE in everyone's task app.
  HARD RULE 2: always pass --tasklist-id. A task created outside the list is
  unreadable by the bot afterwards, and the only way back to it is a user login —
  which is exactly what this skill exists to avoid.
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
  2. ["task", "tasklists", "tasks", "--tasklist-guid", "<guid>"] for each list — returns
     every task's summary, assignee, due and completion state. Filter by assignee
     yourself if the user asked about one person.
"我的 / 我有" does NOT mean switch to user identity: the bot owns the tasklist, so it
reads the human's tasks as bot. Never offer feishu_connect_user to read tasks.

TRAP — do NOT pick a read command from `task --help`. It advertises +get-my-tasks,
+get-related-tasks and +search, which LOOK perfect ("List tasks assigned to me") but
are ALL user-identity-only and error "only supports: user". Never call them. There is
no +list-my-tasks. ["task", "tasks", "list"] as bot lists only what the BOT is
responsible for — we always assign the human, so it is empty by construction.
If a task predates STEP 0 and is therefore outside the list, say it is not in the
list rather than asking anyone to log in.

Traps (each one observed live):
- +get-task, +delete, +list, +create-reminder do not exist. Deleting is
  ["task", "tasks", "delete", "--task-guid", "<guid>"].
  ISSUE THAT COMMAND. Its --help says high-risk-write / needs confirmation — that
  confirmation is handled for you once you call it; it is NOT an instruction to stop.
  Never add --yes yourself, and never report a deletion (or any change) you did not
  actually execute — reading --help is not doing the work.
- Values go through flags only — positional arguments are rejected.
- 待办 mentioned around a meeting minute (妙记/会议纪要/minute_token) is NOT this
  domain — that is lark-minutes' +todo; do not create a tasklist to hold it.
- Bot identity cannot add members across tenants (tenant_access_token scope).

Rare surfaces — sections, subtasks, custom fields, comments, followers, attachments,
task hierarchy — are in references/task-advanced.md; read it only when a request needs
one. For a task need neither here nor there covers, say what you cannot do and stop —
never guess a command or ask anyone to log in.
