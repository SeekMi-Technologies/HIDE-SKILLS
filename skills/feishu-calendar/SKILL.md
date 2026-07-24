---
name: feishu-calendar
description: Feishu calendar — check schedules, find free slots, book meetings (incl. cross-timezone). Use for any 日程/会议/约时间/schedule/meeting request.
scopes: ["calendar:calendar"]
commands: ["calendar +agenda", "calendar +freebusy", "calendar +suggestion", "calendar +create"]
---
Commands (grammar from the pinned lark-cli — pass ISO 8601 times WITH an explicit
offset, e.g. 2026-07-06T18:00:00-07:00):

- Agenda:    ["calendar", "+agenda", "--start", "<ISO>", "--end", "<ISO>"]
  (NO --date flag exists; --end defaults to end of the start day)
- Busy/free: ["calendar", "+freebusy", "--user-id", "<ou_xxx>", "--start", "<ISO>", "--end", "<ISO>"]
- Slot suggestions when busy times conflict:
  ["calendar", "+suggestion", "--attendee-ids", "<ou_a,ou_b>", "--duration-minutes", "30", "--start", "<ISO>", "--end", "<ISO>"]
- Create:    ["calendar", "+create", "--summary", "<title>", "--start", "<ISO>",
              "--end", "<ISO>", "--attendee-ids", "<ou_a,ou_b>", "--description", "<text>"]
  (attendees accept user ou_, chat oc_, room omm_ ids; --rrule rfc5545 for recurring)

Booking recipe (follow in order):
1. Resolve every attendee's open_id (feishu-contacts skill). HARD RULE — the
   requester is ALWAYS an attendee, even when they only named other people: the
   event lives on the bot's calendar, so anyone left off cannot see it at all.
2. Determine each attendee's timezone from the team directory / memory / what the
   user said; if still unknown, ASK rather than assume. Do NOT expect
   ["contact", "+get-user"] to help — as bot it returns only ids, no timezone.
3. +freebusy each attendee across the candidate window; on conflict use +suggestion
   or propose alternatives — never double-book silently. An EMPTY result means that
   person is free, not that you are blind — proceed.
4. Create ONE complete event (title, start/end WITH offset, all attendees), as bot.
   The create runs directly with no human review — triple-check date, offset, and
   ids BEFORE the call. For cross-timezone meetings compute the time in BOTH zones
   explicitly (mind the date line: LA evening = next-day Beijing morning) and state
   both in your report. Attendees then accept or decline in Feishu.

IDENTITY — the whole booking path is bot. Never switch to identity="user" to book:
- +create, +update, +freebusy and attendee invites all work as bot. `+create` on a
  bot-owned calendar with attendees IS the normal booking flow.
- An empty +freebusy is NEVER a reason to switch identity or to offer
  feishu_connect_user. If availability genuinely cannot be read the app is missing
  `calendar:calendar.free_busy:read` — that is an ADMIN grant, not a user login, so
  say so and book anyway rather than sending anyone an OAuth link.
- Only reading the SPEAKER's own personal calendar ("我的日程") justifies
  identity="user", and only when they already have a connected identity.

Destructive calendar changes (delete/update an existing event) pause for the
user's confirmation; creates run directly.
