---
name: automations
description: Create, list or cancel an automation — something happens and instructions run once. Use for ANY 自动化/定时/每天/提醒/recurring request, "when X happens notify/do Y", GitHub or Base (多维表格) events starting a routine, or an external system that should trigger work by webhook.
summary:
  zh: "把一句话变成自动化：定时跑、GitHub 事件、多维表格新增记录、外部 webhook 都能触发"
  en: "Turn a sentence into an automation — schedules, GitHub events, Base records and webhooks all fire it"
---
An automation = TRIGGERS (ANY one fires it) + INSTRUCTIONS (one run per fire).
Create with `create_automation`; the person always sees a confirm card carrying the
whole configuration first — nothing exists until they approve, so never announce
success before the tool answers.

PICK THE KIND from what the person described — never ask them to name a "type":
- A time ("每天早上", "monthly", "at 5pm once") → schedule.
- Something happening in a GitHub repository → github.
- A new record in a Feishu Base (多维表格) — a pasted /base/ link, "新增…就…" →
  feishu_base. READ the feishu-base-automation skill BEFORE creating one.
- Any other system that can POST (CI, an internal tool, a SaaS webhook) → custom.
Several conditions = several triggers on ONE automation, never several copies.

TRIGGER shapes (`triggers` is a JSON array; each object carries its own `type`):
- `{"type": "schedule", "rrule": "DTSTART;TZID=<zone>:19700101T000000\nRRULE:<rule>"}`
  — repeating (the DTSTART stamp is a placeholder). One-time run: a real DTSTART
  moment plus `COUNT=1`.
- `{"type": "github", "repo": "owner/name", "event": "issues", "action": "opened"}` —
  `event` is REQUIRED (a GitHub webhook event name), `action` optional. The repo must
  be one the connected account administers; ask rather than guess either.
- `{"type": "feishu_base", …}` — the shape, the required watched_field and the
  prerequisites are in the feishu-base-automation skill; read it first.
- `{"type": "custom"}` — no other fields. The address exists only after approval.

INSTRUCTIONS discipline — the most common way an automation goes wrong:
- Describe ONE execution: what to read, what to compare, what to send, and WHERE.
- Name the destination INSIDE instructions (the chat id when you have it). No
  destination named = the run's reply lands on the task board only — say so.
- Never restate the trigger or the recurrence; the platform owns firing.
- The run starts fresh with no memory of this conversation. Write instructions
  self-contained enough for a stranger: real ids, real field names, no "as above".

CAPS AND FILTERS:
- `max_runs_per_hour` 0 = uncapped for schedule-only, a default ceiling otherwise.
  Pass a number only when the person named one.
- `webhook_filter` only when the person said what to filter on, written loosely
  (`"status":\s*"failed"`) — the body is matched as re-rendered JSON. A filter
  nobody asked for is an automation that silently never fires.

AFTER the tool answers:
- custom: say the address EXACTLY as written; the key is not yours and is never
  in the reply — the automation's console page reveals it.
- feishu_base: both ends are already built and enabled; nothing to hand over.
- `list_automations` / `cancel_automation` answer "what do we have" and "stop it";
  their returns explain next_fire/stalled/missed — relay those words, don't guess.
  An event-triggered automation has NO next fire time; that is normal, not broken.

READING one automation in full is `read_automation` — its verbatim instructions,
triggers, cap and filter. `list_automations` is only a summary and does NOT carry
the instructions, so read the automation before you quote what it does or edit its
wording: rewriting instructions you have not read invents the parts nobody named.

EDITING an existing automation is `update_automation`, NEVER cancel-and-recreate
(that loses the id and, for custom, the address every producer holds). Send only
the fields that change — an omitted field stays as it is — and the card shows
exactly that. To reword instructions, `read_automation` first. Changing triggers
re-provisions the outside world on the same address and key; changing wording
touches nothing outside.
