---
name: feishu-docs
description: Search, read, or create Feishu docs / 云文档 / drive 文件. Use for any request about a document's CONTENT — writing one, finding one, reading one, sharing one. The 知识库 space and its node tree are feishu-wiki.
scopes: ["drive:drive", "docx:document"]
commands: ["drive +search", "drive +member-add", "drive files list", "docs +create", "docs +fetch", "docs +update"]
---
Every command runs as the BOT. Values go through flags only.

WHICH DOCUMENTS EXIST — always a Drive question, never memory:
- "有哪些文档 / 都创建了什么 / 有没有写过 / 我们没有吗" ⇒ ["drive", "files", "list"].
- Keyword search ("找找关于 X 的文档") ⇒ ["drive", "+search", "--query", "<keywords>"].
  Drop any hit whose `result_meta.is_cross_tenant` is true — Feishu mixes in its own
  template library (owner 云文档助手), and those read exactly like the company's own docs.
Reach for the CLI first and treat search_memory as a hint that still needs confirming,
never as the answer: memory only knows what you did and blurs a doc together with the
request that produced it — asked what it had created, the bot once listed four docs from
memory when Drive held three, inventing one by counting the same doc twice. An invented
item and a wrong "没找到" both look exactly like correct answers, so the person cannot
catch either. `drive files list` and `drive +search` are the whole surface — `--help`
also lists --mine, --created-by-me and docs +search, which the bot cannot use.

READ a doc: ["docs", "+fetch", "--doc", "<token or URL>"] — returns DocxXML. Get the
token from a search result or a pasted …/docx/<token> URL.
  When the content is headed into a CHAT REPLY, fetch it with ["--doc-format",
  "im-markdown"] instead: it unescapes entities (R&amp;D → R&D) and rewrites the doc's
  <cite type="user" …> into IM's own <at user_id="ou_…">Name</at>. Raw DocxXML pasted
  into a message renders literally — that is a bug we shipped once.

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

BIG content goes in CHUNKS — when the full body would run past roughly 2000 characters
of DocxXML, or a +create with everything inline just failed with Invalid JSON: one
oversized --content payload is the known trigger for the model's own empty-arguments
tool crash, and a failed giant call leaves a half-written doc that still reads as done.
(A short doc — a few brief sections — stays ONE +create call; chunking it only adds
calls.) The chunked path:
  1. +create with the title and the FIRST section only.
  2. Append each remaining section with its own call:
     ["docs", "+update", "--doc", "<token>", "--command", "block_insert_after",
      "--block-id", "<last block id from a fetch --detail with-ids>", "--content", "<one section>"]
  3. After the last write: ["docs", "+fetch", "--doc", "<token>"] and CHECK every
     section is present. The completion report describes what this fetch showed —
     nothing else. A "继续" follow-up starts with the same fetch, never from memory
     of what was supposedly written.

Flags: the document handle is always --doc (--doc-token and --doc-id do not exist);
block edits address ranges with --start-block-id/--end-block-id or --scope, never
--range or bare --start/--end.

SHARE — HARD RULE: a bot-created doc is invisible to the requester until you share it,
in the SAME turn as the create, before you report back:
  ["drive", "+member-add", "--token", "<doc_token>", "--type", "docx",
   "--member-id", "<ou_requester,ou_others>", "--member-type", "openid",
   "--perm", "full_access"]
  --type is REQUIRED with a bare token (a full URL infers it). Share first, then put the
  doc URL in your reply — the `url` field copied verbatim from the create/fetch response,
  never one assembled from a remembered token — so the link works the moment they click it.
  Batching 2+ ids takes a different API path needing docs:permission.member; if that
  99991672s, repeat +member-add ONCE PER PERSON — stay on +member-add rather than
  dropping to ["drive","permission.members","create"].
  Never add --yes yourself: the CLI marks this high-risk-write and the platform adds the
  flag after the confirmation it handles for you — that is not a cue to pass it or stop.

Permissions are TWO layers — diagnose precisely:
- Code 99991672 = a missing APP SCOPE: the admin was already DMed a grant link; say
  which permission is missing and ask them to grant + retry.
- "no permission / forbidden" on a SPECIFIC doc/folder/wiki WITHOUT 99991672 = the
  resource was never shared with the bot:
  · a doc: open it → "…" → 更多 → 添加文档应用 → pick this bot; or share the doc/folder
    to a group chat this bot is in;
  · a wiki space (知识库): read the feishu-wiki skill — getting the bot into a space has
    one correct answer and it is not the one people guess.
- The 知识库 itself — putting a doc into it, the node tree, who can see a space — is
  feishu-wiki. This skill stops at document content.
- Empty search/list results can mean the same thing — the bot only sees what it was given.

Meeting minutes (智能纪要 / 妙记) and forwarded docs:
- A forwarded doc arrives as "[The user sent a … message titled '…', link: …]" —
  extract the token (…/docx/<token> or …/minutes/<token>) and fetch it; with only a
  title, search ["drive", "+search", "--query", "<title>"].
- 智能纪要 are docx docs: ["docs", "+fetch", "--doc", "<token or URL>"]. A denied fetch
  means that doc was never shared with the bot — ask the owner to share it, the same
  添加文档应用 step as above.
- Extracting TODOs from minutes: quote each item VERBATIM with its owner; keep each
  owner's attribution (谁的 todo 归谁), never merge owners.

For a document-domain need none of the above covers, say what you cannot do and stop.
