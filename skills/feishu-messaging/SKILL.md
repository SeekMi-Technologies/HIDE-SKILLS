---
name: feishu-messaging
description: Send Feishu/Lark messages — DM a person, post to a group chat, reply in thread. Use when asked to message, notify, remind, or share something with someone on Feishu.
scopes: ["im:message"]
commands: ["im +messages-send", "im +messages-reply", "im +chat-search"]
---
Send with feishu_cli as the bot (add --dry-run to any command to preview it first):

- DM a person:   ["im", "+messages-send", "--user-id", "<ou_xxx>", "--markdown", "<text>"]
- Post to chat:  ["im", "+messages-send", "--chat-id", "<oc_xxx>", "--markdown", "<text>"]
- Plain text: swap --markdown for --text.
- Reply to a message: ["im", "+messages-reply", "--message-id", "<om_xxx>", "--markdown", "<text>"]
  Add --reply-in-thread to keep the reply inside the thread stream instead of the main
  chat. The om_ id is the message being replied to (from the incoming event or a
  chat-messages-list result), NOT a chat or user id.
- Always add --idempotency-key <a-stable-key-you-derive-from-the-task> when a retry is
  conceivable — it makes a duplicate send impossible.

Message content is PLAIN text / Feishu markdown — an IM message, NOT a document:
- Write &, <, > literally. NEVER HTML-escape them: "R&D" stays "R&D", never "R&amp;D".
  The &amp;/&lt; escaping and <cite>/<callout> tags belong to docs (DocxXML) only; using
  them here renders as literal garbage in the chat.
- @-mention a person: <at user_id="ou_xxx"></at> (underscore user_id; an optional display
  name may go between the tags). @everyone: <at user_id="all"></at>. Use this EXACT form —
  not the DocxXML <cite type="user"> tag, and not a hyphenated user-id.

Resolving targets:
- A person's open_id (ou_…) comes from the [Team directory] block; if they are not
  listed, resolve the name with the feishu-contacts skill — never guess an id.
- A group's chat_id (oc_…): ["im", "+chat-search", "--query", "<group name>"].

Rules:
- Message content is complete and self-contained (the recipient lacks your context);
  match the recipient's language.
- One send per request; the platform pauses every send for the user's confirmation.
- This skill covers send, reply, and chat-search only. For a messaging surface it does
  not describe — editing an already-sent message, interactive cards, pinning, reactions
  — say what you cannot do and stop. Never guess a command or send an OAuth link.
