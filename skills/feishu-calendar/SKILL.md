---
name: feishu-calendar
description: Feishu calendar — check schedules/agendas, create or update calendar events, book meetings. Use for any 日程/schedule/meeting-time request.
scopes: ["calendar:calendar"]
commands: ["calendar +agenda"]
---
Commands (feishu_cli; read feishu_skill(name="lark-calendar") for full grammar and
required reference files BEFORE composing unfamiliar commands):

- Today's agenda: ["calendar", "+agenda"]
- Personal calendars ("我的日程") need identity="user" (the speaker's own view) —
  see the feishu-identity skill; the bot identity sees only the bot's calendar.

Rules:
- Times: resolve relative dates ("明天下午3点") against the [Current turn] UTC time,
  in the user's timezone (Asia/Shanghai unless told otherwise).
- Event creation pauses for the user's confirmation — compose the full event (title,
  start/end, attendees) in ONE call rather than piecemeal.
- CREATE ONCE: to fix a created event, update it by its id — never create again.
