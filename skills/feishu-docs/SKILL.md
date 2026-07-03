---
name: feishu-docs
description: Search, read, or create Feishu docs / 云文档 / wiki / 知识库 / drive files. Use for any request about Feishu documents or knowledge-base content.
scopes: ["drive:drive", "docx:document"]
---
Commands (feishu_cli; read feishu_skill(name="lark-doc") / (name="lark-drive") /
(name="lark-wiki") for the full grammar and any required reference files BEFORE
composing unfamiliar commands):

- Org-wide file search (bot-capable): ["drive", "+search", "--query", "<keywords>"]
  (docs +search is the user-identity-only variant — prefer drive +search as bot).
- Read a doc: lark-doc skill's read commands with the doc token from search/URL.
- Create/edit docs: follow lark-doc's create/patch reference files EXACTLY — blind
  creates produce duplicates.

Permissions are TWO layers — diagnose precisely:
- Code 99991672 = a missing APP SCOPE: the admin was already DMed a grant link; say
  which permission is missing and ask them to grant + retry.
- "no permission / forbidden" on a SPECIFIC doc/folder/wiki WITHOUT 99991672 = the
  resource was never shared with the bot:
  · a doc: open it → "…" menu → 更多 → 添加文档应用 → pick this bot; or share the
    doc/folder to a group chat that has this bot in it;
  · a wiki space (知识库): space 设置 → 成员 → add this bot (member type 应用) or a
    group containing it.
- Empty search/list results can mean the same thing — the bot only sees what it was
  given.
