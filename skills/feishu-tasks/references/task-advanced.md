# feishu-tasks — advanced surfaces (rare)

Read this only when a request needs something the main skill does not cover. Everything
here is bot-capable. Values go through flags/`--data` only; positional args are rejected.
For a command's exact flags, run its `--help` (always allowed) before composing it —
`["task", "sections", "create", "--help"]`.

## Sections (columns within a tasklist)
`task sections` = `create | delete | get | list | patch | tasks`. These are raw API
resources — the body goes through `--data`, there is no `--name` or `--tasklist-guid`
flag. Create takes `{"name":"<分组名>","resource_type":"tasklist","resource_id":"<tasklist
guid>"}`. `sections tasks --section-guid <guid>` lists one section's tasks.

## Subtasks
`task subtasks` = `create | list`, also raw resources: `subtasks create --task-guid
<parent guid> --data '{"summary":"…"}'`, `subtasks list --task-guid <guid>`.

## Custom fields
`task custom_fields` = `add | create | get | list | patch | remove`, and
`task custom_field_options` = `create | patch` (select-type options). A field is `create`d
on a resource — only `tasklist` is supported — then `add`ed to tasks. Read
`custom_fields list --resource-type tasklist --resource-id <tasklist guid>` first to learn
a field's guid and type before writing a value.

## Comments, followers
- `["task", "+comment", "--task-id", "<guid>", "--content", "<text>"]`.
- `["task", "+followers", "--task-id", "<guid>", "--add", "<ou_a,ou_b>"]` (`--remove` to drop).
  A follower sees the task without being an assignee.

## Hierarchy
`["task", "+set-ancestor", "--task-id", "<guid>", "--ancestor-id", "<parent guid>"]` nests
a task under a parent; OMIT `--ancestor-id` to make it independent again.

## Not available
`+upload-attachment` needs a file on disk and this bot has no way to receive one yet. Say
the file cannot be taken in — do not offer a workaround.

If a request needs a task surface none of this describes, say what you cannot do and
stop.
