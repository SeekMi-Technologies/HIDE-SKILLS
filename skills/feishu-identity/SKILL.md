---
name: feishu-identity
description: Feishu bot-vs-user identity — when to act AS the speaker (their own calendar/tasks/docs/mail) and how to connect a member's personal identity. Use when a request is about the SPEAKER's personal data, or a command errors that it only supports user identity.
---
Every feishu_cli call runs as one of two identities:
- identity="bot" (the default) — the app's own view. This is the RIGHT identity for
  almost everything: the whole data plane (docs, tasks, calendar, base, messaging,
  contacts) works as the bot. Stay on bot.
- identity="user" — act AS the speaker on their OWN personal data ("我的日程", "我的待办",
  their own mail). A member can only ever act as themselves.

Switch to identity="user" ONLY when BOTH hold:
1. the request is about the SPEAKER's own personal data, AND
2. a bot attempt literally errored that the command is user-identity-only
   ("--as bot is not supported" / "only supports: user").

Do NOT switch identity for any of these — they are not user-identity problems:
- an empty result (the bot only sees what it was granted/shared — say so, don't log in);
- a parameter or validation error (fix the command);
- code 99991672 / missing_scope on a BOT call (a missing APP scope — the admin was
  DMed a grant link; ask them to grant, never send the user a login);
- "no permission" on a specific doc/folder/space (it was never shared with the bot —
  ask for it to be shared).
- an "only supports: user" error on a command a curated skill told you NOT to use. The
  domain skill is authoritative: feishu-tasks reads tasks as bot via `task tasklists
  tasks` and forbids +get-my-tasks/+get-related-tasks/+search. Hitting the user-only
  error on one of those means you picked the wrong command — go back to the skill's bot
  command; do NOT switch identity or send a login link.
Before reaching for user identity at all, use the matching curated skill's bot-capable
path: org-wide doc search is `drive +search` as bot (feishu-docs); names resolve from
the [Team directory] (feishu-contacts); tasks read as bot (feishu-tasks).

Connecting a personal identity (only once the two conditions above are met and the
speaker has none):
- Call feishu_connect_user and send the link it JUST returned. When the user says they
  approved, call it AGAIN to complete. Never reuse a link from history — links expire.
- A user-identity call that fails with missing_scope → call feishu_connect_user with
  scope="<the missing scope>" and send the new link (one more approval tap).
