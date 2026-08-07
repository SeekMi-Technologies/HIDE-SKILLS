---
name: feishu-digest
description: Message recap — summarize recent messages in a chat or DM. Use for any recap or catch-up request about a Feishu conversation (速览, 最近聊了啥, catch me up).
scopes: ["im:message"]
commands: ["im +chat-messages-list", "im +chat-search"]
summary:
  zh: "把一个群或私聊最近聊的内容汇总一下，告诉你错过了什么"
  en: "Summarize what was said recently in a chat or DM"
---
Default fetch — one call, no time window:
["im", "+chat-messages-list", "--chat-id", "<oc_xxx>", "--page-size", "50"]

"Recent" means the last 50 messages, NOT the last N hours. A quiet chat's newest
conversation may be days old — that conversation is the answer. Messages return
newest-first; take the span covered from their create_time values.

Add --start/--end only when the user names a period — ISO 8601 with an explicit
offset ("今天" = start of today in the requester's timezone).

Judge from what came back, never from the window you picked:
- Only the requester's own messages → this is NOT absence. Re-fetch without the
  window before saying anything about "no messages".
- has_more, and the 50 span only hours → busy chat; add --start/--end or take one
  more page (never more than one extra).
- has_more still true when you stop → you read only part of the chat. Say the digest
  is partial and name the span you did cover; never present it as the whole picture.
- Nothing even unbounded → the bot reads only messages sent after it joined the
  chat. Say so and stop.

A DM has its own oc_ chat id — pass it to --chat-id too (--user-id is a user-identity
path the bot cannot use). A group's id: ["im", "+chat-search", "--query", "<name>"].

Digest format:
- Group by TOPIC, not by message: what was discussed, who drove it, where it landed.
- Call out decisions, asks/todos (who → what), links/files shared, anything waiting
  on the reader.
- create_time is UTC — convert to the requester's timezone, and name both the span
  covered ("Jul 27 11:19–Jul 29 13:32, 6 messages") and the timezone used.
- ≤10 lines unless asked for more; write in the user's language.
