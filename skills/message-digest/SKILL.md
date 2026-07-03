---
name: message-digest
description: 消息速览 — summarize recent messages in a chat or DM ("这个群最近聊了啥", "catch me up", "速览"). Use for any recap/digest request about a Feishu conversation.
scopes: ["im:message"]
commands: ["im +chat-messages-list"]
---
Fetch: ["im", "+chat-messages-list", "--chat-id", "<oc_xxx>", "--page-size", "50"]
- For a DM use --user-id <ou_xxx> instead of --chat-id (mutually exclusive).
- Time-box with --start/--end (ISO 8601): "今天" = start of today local time.
- Messages return newest-first (--order asc to flip); reactions are included.
- To find the chat id: ["im", "+chat-search", "--query", "<群名>"].

Digest format (the part users love — keep it tight):
- Group by TOPIC, not by message. One line per topic: what was discussed, who
  drove it, where it landed.
- Call out: decisions made, asks/todos (who → what), links/files shared, and
  anything waiting on the reader.
- Note the time span covered ("今天 09:00–14:30, 41条"). ≤10 lines unless asked
  for more; write in the user's language.
- If a message is a doc/card share, name the doc title rather than skipping it.
