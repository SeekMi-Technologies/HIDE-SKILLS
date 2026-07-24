---
name: feishu-docs
description: Search, read, or create Feishu docs / 云文档 / wiki / 知识库 / drive files. Use for any request about Feishu documents or knowledge-base content.
scopes: ["drive:drive", "docx:document"]
commands: ["drive +search", "drive +member-add"]
---
Commands (feishu_cli; call read_skill("lark-doc") / ("lark-drive") /
("lark-wiki") for the full grammar and any required reference files BEFORE
composing unfamiliar commands):

- Org-wide file search (bot-capable): ["drive", "+search", "--query", "<keywords>"]
  (docs +search is the user-identity-only variant — prefer drive +search as bot).
- Read a doc: lark-doc skill's read commands with the doc token from search/URL.
- Create/edit docs: follow lark-doc's create/patch reference files EXACTLY — blind
  creates produce duplicates.
- ALWAYS write DocxXML, which is the default — never pass --doc-format markdown.
  DocxXML is the native representation (+fetch returns it, so fetch → edit → write
  round-trips losslessly) and reaches blocks Markdown has no syntax for, e.g.
  <callout emoji="🤝">. Markdown is a lossy one-way import; switching formats
  mid-document is how a doc ends up part rendered, part literal.
  Shape: <title>…</title><h2>…</h2><p>…</p><blockquote><p><b>…</b> …</p></blockquote>
  <ul><li>…</li></ul><hr/>. Read lark-doc's references/lark-doc-xml.md before using
  anything richer.
- HARD RULE — a bot-created doc is invisible to the requester until you share it, in
  the SAME turn as the create, before you report back:
  ["drive", "+member-add", "--token", "<doc_token>", "--type", "docx",
   "--member-id", "<ou_requester,ou_others>", "--member-type", "openid",
   "--perm", "full_access"]
  --type is REQUIRED with a bare token (a full URL infers it). Then put the doc URL
  in your reply. Never hand over a link the person cannot open and wait to be told.
  Batching 2+ ids in one call takes a different API path needing
  docs:permission.member; if that 99991672s, add people ONE call each — do not
  report failure, and never ask anyone to log in for it.

Permissions are TWO layers — diagnose precisely:
- Code 99991672 = a missing APP SCOPE: the admin was already DMed a grant link; say
  which permission is missing and ask them to grant + retry.
- "no permission / forbidden" on a SPECIFIC doc/folder/wiki WITHOUT 99991672 = the
  resource was never shared with the bot:
  · a doc: open it → "…" menu → 更多 → 添加文档应用 → pick this bot; or share the
    doc/folder to a group chat that has this bot in it;
  · a wiki space (知识库): space 设置 → 成员 → add this bot (member type 应用) or a
    group containing it.
- Putting a doc INTO the wiki is ["wiki", "+move", …] and works as bot. If
  ["wiki", "spaces", "list"] comes back empty the bot belongs to no space — ask to be
  added to the space (member type 应用). That is a space-owner action; user identity
  does not help, so never offer feishu_connect_user for it.
- Empty search/list results can mean the same thing — the bot only sees what it was
  given.

Meeting minutes (智能纪要 / 妙记) and forwarded docs:
- A forwarded doc arrives as "[The user sent a … message titled '…', link: …]" —
  extract the token from the link (…/docx/<token> or …/minutes/<token>) and fetch
  it; with only a title, search: ["drive", "+search", "--query", "<title>"].
- 智能纪要 documents are docx docs: ["docs", "+fetch", "--doc", "<token or URL>"].
  Reading another person's minutes usually needs identity="user" (the speaker's own
  access) — if a bot read is denied, retry as user or ask them to share the doc.
- Extracting TODOs from minutes: quote each item VERBATIM with its owner; keep the
  owner attribution from the minutes (谁的 todo 归谁), never merge owners.
