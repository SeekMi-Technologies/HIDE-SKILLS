---
name: feishu-messaging
description: Send Feishu/Lark messages — DM a person, post to a group chat, reply in thread. Use when asked to message, notify, remind, or share something with someone on Feishu.
scopes: ["im:message"]
---
Send with feishu_cli (grammar from the pinned lark-cli; add --dry-run to preview):

- DM a person:   ["im", "+messages-send", "--user-id", "<ou_xxx>", "--markdown", "<text>"]
- Post to chat:  ["im", "+messages-send", "--chat-id", "<oc_xxx>", "--markdown", "<text>"]
- Plain text: use --text instead of --markdown.
- Reply in thread: ["im", "+messages-reply", ...] (read the lark-im reference via
  feishu_skill for reply/thread flags).
- Always pass --idempotency-key <a-stable-key-you-derive-from-the-task> on sends when
  retrying is conceivable — it makes a duplicate send impossible.

Resolving targets:
- A person's open_id (ou_…) comes from the [Team directory] block; if they are not
  listed, say so — never guess an id.
- A group's chat_id (oc_…): search by name with
  ["im", "+chat-search", "--query", "<group name>"].

Rules:
- Message content should be complete and self-contained (the recipient lacks your
  context). Match the recipient's language.
- One send per request; the platform pauses every send for the user's confirmation.
- For the full im command surface, read feishu_skill(name="lark-im").
