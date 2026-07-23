---
name: feishu-contacts
description: Resolve a person (Chinese or English name) to their Feishu open_id, or look up a user's profile by id. Use whenever a request names a person you must message, invite, or act on.
scopes: ["contact:contact.base:readonly", "contact:user.base:readonly"]
commands: ["contact +get-user", "im +chat-search"]
---
Resolution ladder — stop at the first hit:
1. [Team directory] context block — it lists members with BOTH Chinese and English
   names (e.g. "王梓珩 (Will Wang)") and their open_id. Match loosely across both.
2. search_memory("<name> open_id") — the org memory carries an identity map.
3. Verify/enrich a known id: ["contact", "+get-user", "--user-id", "<ou_xxx>"]
   (bot-capable, read; --user-id-type open_id|union_id|user_id). If it returns 200
   with ids but NO name, the app is missing contact:user.base:readonly — that is an
   admin grant, so report it; do not retry and do not ask anyone to log in.
4. LAST resort for an unknown person: ["im", "+chat-search", "--query", "<name>"]
   to find a shared chat, then the chat's members.

Hard rules:
- ["contact", "+search-user", ...] is USER-IDENTITY-ONLY — as the bot it always
  fails with a policy error. Do not call it unless identity="user" is available.
- NEVER guess an open_id. If the ladder fails, say who you could not resolve and
  ask — a message or invite to the wrong person is worse than a question.
