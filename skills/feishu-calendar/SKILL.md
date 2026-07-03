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
1. Resolve every attendee's open_id (feishu-contacts skill; the [Team directory]
   block carries Chinese + English names).
2. Determine each attendee's timezone. Try ["contact", "+get-user", "--user-id",
   "<ou_>"] — if the response carries no timezone field (current grants may hide
   it), use what the team directory / memory / the user said; if still unknown, ASK
   rather than assume.
3. +freebusy each attendee across the candidate window; on conflict use +suggestion
   or propose alternatives — never double-book silently.
4. Create ONE complete event (title, start/end WITH offset, all attendees). The
   create runs directly with no human review — triple-check date, offset, and ids
   BEFORE the call. For cross-timezone meetings compute the time in BOTH zones
   explicitly (mind the date line: LA evening = next-day Beijing morning) and state
   both in your report.

Identity: reading someone's PERSONAL calendar ("我的日程") needs identity="user"
(the speaker's own view — feishu-identity skill); +create as bot invites attendees
onto a bot-owned event, which is the normal booking path.
Destructive calendar changes (delete/update an existing event) pause for the
user's confirmation; creates run directly.
