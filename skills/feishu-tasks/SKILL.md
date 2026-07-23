---
name: feishu-tasks
description: Create, update, remind, assign, complete Feishu tasks/待办. Use for any 任务/task/todo/提醒 request.
commands: ["task +create", "task +update", "task +assign", "task +reminder", "task +tasklist-create"]
---
Commands (grammar verified live against the pinned lark-cli 1.0.63; open_ids come
from the [Team directory] block — never guessed, never from im +chat-search):

- Create: ["task", "+create", "--summary", "<title>", "--assignee", "<ou_requester>",
  "--tasklist-id", "<guid>", "--due", "2026-07-30", "--description", "<text>",
  "--idempotency-key", "<stable-key>"]
  HARD RULE: always pass --assignee with the requester's open_id (plus anyone they
  name). A bot-created task with no assignee is INVISIBLE in everyone's task app.
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

Reading tasks back — stay on bot identity:
- Put every task you create into a bot-owned tasklist, then read from that list:
  ["task", "+tasklist-create", "--name", "<name>", "--member", "<ou_requester>"] once,
  then ["task", "tasklists", "tasks", "--tasklist-guid", "<guid>"] to list them.
  This works as the bot and returns each task's assignee, due and completion state —
  no user authorization, nothing for the requester to approve.
- ["task", "tasks", "list"] as bot returns only tasks the BOT is responsible for.
  Since we assign the human, that list is empty — it is not the way to answer
  "我的待办".
- USER-ONLY, so prefer the tasklist route above and only offer feishu_connect_user
  when the user insists on their personal cross-app view: +search, +get-my-tasks,
  +get-related-tasks.

Traps (each one observed live):
- +get-task, +delete, +list, +create-reminder do not exist. Deleting is
  ["task", "tasks", "delete", ...] and pauses for the user's confirmation.
- Values go through flags only — positional arguments are rejected.
- 待办 mentioned around a meeting minute (妙记/会议纪要/minute_token) is NOT this
  domain — that is lark-minutes' +todo; do not create a tasklist to hold it.
- Bot identity cannot add members across tenants (tenant_access_token scope).

For anything not covered above — sections, subtasks, custom fields, agent
registration, identity/permission-error recovery, or any command whose behavior
surprises you — read_skill("lark-task") for the full manual before guessing; it is
the source of truth this skill was distilled from.
