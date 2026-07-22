---
name: feishu-tasks
description: Create, update, remind, assign, complete Feishu tasks/待办. Use for any 任务/task/todo/提醒 request.
commands: ["task +create", "task +update", "task +assign", "task +reminder", "task +search"]
---
Commands (grammar verified against the pinned lark-cli; open_ids come from the
[Team directory] block — never guessed, never from im +chat-search):

- Create: ["task", "+create", "--summary", "<title>", "--assignee", "<ou_requester>",
  "--due", "date:YYYY-MM-DD", "--description", "<text>", "--idempotency-key", "<stable-key>"]
  HARD RULE: always pass --assignee with the requester's open_id (plus anyone they
  name). A bot-created task with no assignee is INVISIBLE in everyone's task app.
  --due also accepts ISO 8601 or relative (+2d).
- Update title/desc/due: ["task", "+update", "--task-id", "<guid>", "--due", "date:2026-07-27"]
  Members can NOT be updated here (the API rejects members as an update field) — use +assign.
- Members: ["task", "+assign", "--task-id", "<guid>", "--add", "<ou_a,ou_b>"] (--remove to drop).
- Reminder: ["task", "+reminder", "--task-id", "<guid>", "--set", "1d"]
  --set is RELATIVE TO THE DUE TIME (15m/1h/1d = that long BEFORE due), never an
  absolute moment. Ensure the task has a due first, then pick the offset
  (e.g. due Sunday + "周六晚上提醒我" → --set 1d).
- Complete / reopen: ["task", "+complete", "--task-id", "<guid>"] / ["task", "+reopen", ...]
- Read one task: ["task", "tasks", "get", "--task-guid", "<guid>"] — there is NO +get-task.

Identity:
- bot (default) handles create/update/assign/reminder/complete — the normal path.
- USER-ONLY (offer feishu_connect_user when no identity is connected): +search,
  +get-my-tasks, +get-related-tasks — anything answering "我的任务 / 我的待办".

Traps (each one observed live):
- +get-task, +delete, +list, +create-reminder do not exist. Deleting is
  ["task", "tasks", "delete", ...] and pauses for the user's confirmation.
- Values go through flags only — positional arguments are rejected.
- Tasklists, sections, subtasks, custom fields: read_skill("lark-task") and its
  references carry the full grammar.
