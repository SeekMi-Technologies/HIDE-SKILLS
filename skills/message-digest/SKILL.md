---
name: message-digest
description: 消息速览 — summarize recent messages in a chat or DM ("这个群最近聊了啥", "catch me up", "速览"). Use for any recap/digest request about a Feishu conversation.
scopes: ["im:message"]
commands: ["im +chat-messages-list"]
---
Fetch — ONE time-boxed call, never open-ended paging:
["im", "+chat-messages-list", "--chat-id", "<oc_xxx>", "--page-size", "50",
 "--start", "2026-07-06T00:00:00-07:00", "--end", "2026-07-06T23:59:59-07:00"]
- --start/--end are ISO 8601 WITH an explicit UTC offset (exact format above,
  verified live). "今天" = start of today in the REQUESTER's local timezone.
- For a DM use --user-id <ou_xxx> instead of --chat-id (mutually exclusive).
- Messages return newest-first (--order asc to flip); reactions are included.
- To find the chat id: ["im", "+chat-search", "--query", "<群名>"].
- If one window returns too much, NARROW the --start/--end window and re-fetch;
  do not chase page tokens more than one extra page.
- The bot can only read messages sent AFTER it joined the chat. If the asked
  window may predate that, say so plainly and digest what IS readable — never
  keep re-fetching for history that cannot exist.
- Returned create_time values are UTC — convert to the requester's timezone
  before presenting, and name the timezone you used in the digest.

Digest format (the part users love — keep it tight):
- Group by TOPIC, not by message. One line per topic: what was discussed, who
  drove it, where it landed.
- Call out: decisions made, asks/todos (who → what), links/files shared, and
  anything waiting on the reader.
- Note the time span covered ("今天 09:00–14:30, 41条"). ≤10 lines unless asked
  for more; write in the user's language.
- If a message is a doc/card share, name the doc title rather than skipping it.
