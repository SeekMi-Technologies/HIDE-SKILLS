# feishu-tasks — advanced surfaces (rare)

Read this only when a request needs something the main skill does not cover. Everything
here is bot-capable. Values go through flags/`--data` only; positional args are rejected.
For a command's exact flags, run its `--help` (always allowed) before composing it —
`["task", "sections", "create", "--help"]`.

## Sections (columns within a tasklist)
`task sections` = `create | list | get | patch | delete | tasks`. A section lives under
a tasklist; `sections tasks --section-guid <guid>` lists its tasks. Create needs the
owning `--tasklist-guid` and a `--name`.

## Subtasks
`task subtasks` = `create | list`. These are raw-API resources: pass the parent
`--task-guid` and a `--data` JSON body (the Feishu task body — `{"summary": "…"}`, plus
the same optional fields as a top-level task). `subtasks list --task-guid <guid>`
returns the children.

## Custom fields
`task custom_fields` = `add | create | get | list | patch | remove`, and
`task custom_field_options` = `create | patch` (for select-type options). A field is
`create`d on a resource (tasklist), then `add`ed to tasks. Read `list` first to learn a
field's guid and type before writing a value.

## Comments, followers, attachments
- `["task", "+comment", "--task-id", "<guid>", "--content", "<text>"]`.
- `["task", "+followers", "--task-id", "<guid>", "--add", "<ou_a,ou_b>"]` (`--remove` to drop).
  A follower sees the task without being an assignee.
- `["task", "+upload-attachment", "--task-id", "<guid>", "--file", "<cwd-relative path>"]`.

## Hierarchy
`["task", "+set-ancestor", "--task-id", "<guid>", "--ancestor", "<parent guid>"]` nests a
task under a parent (clear it by passing an empty `--ancestor`).

## Still not covered
If a request needs a task surface none of this describes, say what you cannot do and
stop — never guess a command or ask anyone to log in.
