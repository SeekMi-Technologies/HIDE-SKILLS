---
name: feishu-identity
description: Feishu bot-vs-user identity — act AS the speaker (their calendar/tasks/docs/mail), connect a member's personal identity. Use when a request is about the SPEAKER's personal data or a command errors as user-identity-only.
---
TWO identities on every feishu_cli call:
- identity="bot" (default) — the app's own view.
- identity="user" — act AS the speaker: their personal calendar, tasks, docs, mail.
  Use for the SPEAKER's personal data ("我的日程", "我的待办") or when a command
  errors "--as bot is not supported". Each person can only ever act as themselves.

Connecting an identity:
- When asked to connect (or user identity is needed but missing), call
  feishu_connect_user IMMEDIATELY — no clarifying questions — and send the returned
  link. When the user says they approved, call it AGAIN to complete.
- NEVER reuse a verification link from history — links expire; only send the one the
  tool JUST returned.
- A user-identity call failing with missing_scope → call feishu_connect_user with
  scope="<the missing scope>" and send the new link (one more approval tap).

If a command is user-identity-only and no identity is connected, check the relevant
lark skill for a bot-capable sibling (e.g. org-wide doc search is `drive +search` as
bot) before giving up.
