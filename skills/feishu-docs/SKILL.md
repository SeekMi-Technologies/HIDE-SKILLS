---
name: feishu-docs
description: Search, read, or create Feishu docs / 云文档 / wiki / 知识库 / drive files. Use for any request about Feishu documents or knowledge-base content.
scopes: ["drive:drive", "docx:document"]
commands: ["drive +search", "drive +member-add", "drive files list", "docs +create", "docs +fetch", "docs +update", "wiki +move"]
---
The Feishu document domain runs entirely as the bot — never offer feishu_connect_user
for a doc task. Values go through flags only.

WHICH DOCUMENTS EXIST — always a Drive question, never memory:
- "有哪些文档 / 都创建了什么 / 有没有写过 / 我们没有吗" ⇒ ["drive", "files", "list"].
- Keyword search ("找找关于 X 的文档") ⇒ ["drive", "+search", "--query", "<keywords>"].
Reach for the CLI first and treat search_memory as a hint that still needs confirming,
never as the answer: memory only knows what you did and blurs a doc together with the
request that produced it — asked what it had created, the bot once listed four docs from
memory when Drive held three, inventing one by counting the same doc twice. An invented
item and a wrong "没找到" both look exactly like correct answers, so the person cannot
catch either. --mine / --created-by-me and docs +search are user-identity-only and
unavailable to the bot — never reach for them, and never offer a login to get them.

READ a doc: ["docs", "+fetch", "--doc", "<token or URL>"] — returns DocxXML. Get the
token from a search result or a pasted …/docx/<token> URL.

CREATE a doc — always DocxXML (the native format; +fetch returns it, so
fetch → edit → write round-trips losslessly, and it reaches blocks Markdown cannot
express). NEVER pass --doc-format markdown; it is a lossy one-way import and mixing
formats leaves a doc part-rendered, part-literal:
  ["docs", "+create", "--title", "<title>", "--content", "<DocxXML>"]
  Minimal shape: <p>…</p> <h2>…</h2> <ul><li>…</li></ul>
  <blockquote><p><b>…</b> …</p></blockquote> <callout emoji="🤝"><p>…</p></callout> <hr/>.
  For anything richer — tables, grids, checkboxes, @mentions, code, colors, images,
  or editing an existing doc's blocks — read references/docx-xml.md FIRST; a blind
  create or edit produces duplicates or corrupts the doc.
  Place it with --parent-token <folder-or-wiki-node-token>; omit for the default library.

SHARE — HARD RULE: a bot-created doc is invisible to the requester until you share it,
in the SAME turn as the create, before you report back:
  ["drive", "+member-add", "--token", "<doc_token>", "--type", "docx",
   "--member-id", "<ou_requester,ou_others>", "--member-type", "openid",
   "--perm", "full_access"]
  --type is REQUIRED with a bare token (a full URL infers it). Then put the doc URL in
  your reply — never hand over a link the person cannot open and wait to be told.
  Batching 2+ ids takes a different API path needing docs:permission.member; if that
  99991672s, repeat +member-add ONCE PER PERSON — stay on +member-add, do not drop to
  ["drive","permission.members","create"], and never ask anyone to log in for it.
  Never add --yes yourself: the CLI marks this high-risk-write and the platform adds the
  flag after the confirmation it handles for you — that is not a cue to pass it or stop.

Permissions are TWO layers — diagnose precisely:
- Code 99991672 = a missing APP SCOPE: the admin was already DMed a grant link; say
  which permission is missing and ask them to grant + retry.
- "no permission / forbidden" on a SPECIFIC doc/folder/wiki WITHOUT 99991672 = the
  resource was never shared with the bot:
  · a doc: open it → "…" → 更多 → 添加文档应用 → pick this bot; or share the doc/folder
    to a group chat this bot is in;
  · a wiki space (知识库): space 设置 → 成员 → add this bot (member type 应用) or a
    group containing it.
- Putting a doc INTO the wiki is ["wiki", "+move", …] and works as bot. If
  ["wiki", "spaces", "list"] is empty the bot belongs to no space — ask to be added
  (member type 应用). That is a space-owner action; user identity does not help, so
  never offer a login for it.
- Empty search/list results can mean the same thing — the bot only sees what it was given.

Meeting minutes (智能纪要 / 妙记) and forwarded docs:
- A forwarded doc arrives as "[The user sent a … message titled '…', link: …]" —
  extract the token (…/docx/<token> or …/minutes/<token>) and fetch it; with only a
  title, search ["drive", "+search", "--query", "<title>"].
- 智能纪要 are docx docs: ["docs", "+fetch", "--doc", "<token or URL>"]. If a bot fetch
  is denied because the doc was never shared with the bot, ask the owner to share it —
  only the SPEAKER's OWN private minutes justify identity="user" (see feishu-identity).
- Extracting TODOs from minutes: quote each item VERBATIM with its owner; keep each
  owner's attribution (谁的 todo 归谁), never merge owners.

For a document-domain need none of the above covers, say what you cannot do and stop —
never guess a command or send an OAuth link.
