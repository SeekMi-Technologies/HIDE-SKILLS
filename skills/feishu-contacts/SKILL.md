---
name: feishu-contacts
description: Resolve a person (Chinese or English name) to their Feishu open_id, or look up a user's profile by id. Use whenever a request names a person you must message, invite, or act on.
scopes: ["contact:contact.base:readonly", "contact:user.base:readonly"]
commands: ["contact +get-user", "im +chat-search"]
---
Resolution ladder — stop at the first hit:
1. [Team directory] context block — one line per member:
   `- <name> — role: <role>, open_id: <ou_xxx>`. Names are stored as the workspace
   has them, usually Chinese only, so a romanized request ("ziyue") matches nothing
   literally.
   DO THE LOOKUP BEFORE YOU DECIDE. Read the block and quote the line you matched
   before using its open_id — deciding who someone is while restating the request,
   then never re-checking, is how "让 ziyue 讲" became a task for 朱宇程 with the
   directory sitting in the same prompt. Two candidates, or none clearly right → ASK,
   naming them.
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
- Keep the requester's wording. Never substitute the name you resolved into a task
  title, message or doc — "让 ziyue 讲一下" stays "ziyue", it does not become
  "朱宇程和大家讲". Writing your guess into the content hides the error from the
  person best placed to catch it.
- When told you picked the wrong person, re-resolve from the directory before
  answering. Do not defend the previous choice.
