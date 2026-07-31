---
name: feishu-wiki
description: Wiki (知识库) — move docs into a space, create pages, organize the node tree, read page content. Use for any 知识库/知识空间/wiki request or a /wiki/ link. Page CONTENT (writing and editing a doc's body) belongs to feishu-docs; this skill owns the space and its node tree.
scopes: ["wiki:wiki", "search:docs:read"]
commands: ["wiki +space-list", "wiki +node-list", "wiki +node-get", "wiki +node-create", "wiki +move", "wiki +member-list", "drive +search"]
---
Every command runs as the BOT and was verified live against this CLI. Values go through
flags only.

START HERE — the bot only sees spaces it belongs to:
  ["wiki", "+space-list"] → `space_id` per space. Everything else needs one.
  An EMPTY list means the bot is in no space, NOT that the company has none. Say this
  and stop: the space's member dialog accepts 用户/群组/部门/用户组 and has NO 应用
  option, so someone must add A GROUP CHAT THIS BOT IS IN — 知识库设置 → 成员设置 →
  角色与权限 → 添加成员 → search the group name. The bot inherits the space through the
  group — that inheritance is the whole path in.

FIND SOMETHING IN THE SPACE — the default for "知识库里有没有讲 X 的 / 关于 X 我们写过什么".
Full-text, not just titles:
  ["drive", "+search", "--query", "<keywords>", "--space-ids", "<space_id>"]
  Results come back as `entity_type: WIKI` with the node's `token` (a node_token, ready
  for +node-get or docs +fetch) and `summary_highlighted` — the matching sentence. Quote
  that snippet and read the page before answering.
  ALWAYS pass --space-ids for a knowledge-base question. Without it the search spans all
  of Drive and returns cross-tenant template docs that look plausible and are not theirs.
  It reaches nodes nested anywhere in the tree, which a top-level +node-list does not —
  so search first, browse second.

TWO TOKENS PER NODE — the single most expensive thing to get wrong. ["wiki", "+node-list",
"--space-id", "<id>"] returns, for every node:
  `node_token` — the node's place in the tree. Structure commands take THIS.
  `obj_token` + `obj_type` — the document it wraps. Content commands take THIS.
Add "--parent-node-token" "<node_token>" to drill into a subtree, "--page-all" for a big
space (default is one page). Unsure what a token is? ["wiki", "+node-get", "--node-token",
"<node_token | obj_token | a Lark URL>"] resolves all three and reports space_id/obj_type.

READ a page — hand the token to feishu-docs' reader; it accepts either token:
  ["docs", "+fetch", "--doc", "<obj_token>"]
  Going into a chat reply? Add "--doc-format" "im-markdown" (see feishu-docs).

WRITE a page into the space:
  ["wiki", "+node-create", "--space-id", "<id>", "--title", "<标题>"]
  Creates an empty docx node; nest it with "--parent-node-token" "<node_token>". Then fill
  it in through feishu-docs (+update on the returned `obj_token`) — this skill does not
  write document bodies.

MOVE AN EXISTING DOC IN — the main way a knowledge base gets built:
  ["wiki", "+move", "--obj-token", "<docx token>", "--obj-type", "docx",
   "--target-space-id", "<id>"]
  The doc leaves Drive and becomes a node. This one is ASYNC: the CLI polls the task and
  reports the result, so report only what it actually returned.
  Reorganising inside the wiki is the same command with "--node-token" "<tok>" plus
  "--target-parent-token" "<parent node_token>".

SHARING A PAGE'S LINK — copy the `url` field from a tool output in THIS turn
(+node-create, +node-get and +node-list all return it); never assemble
https://…/wiki/<token> from a token you remember. A /wiki/ URL carries the
node_token — built from an obj_token it 404s, and a 404'd wiki link means exactly
that mix-up: re-resolve with ["wiki", "+node-get", "--node-token", "<the full URL>"]
and send the url it returns. Content edits never change a node_token, so a dead
link is always the wrong token, not a "regenerated" one.

Traps and boundaries:
- CREATING A SPACE IS NOT POSSIBLE for the bot — the API takes a user token only, no
  permission changes that. A person must create the 知识库 first; say so and stop.
- DELETING a node or a space is not available: it needs a permission this app was
  deliberately not granted. Say the deletion has to be done by hand in Feishu; never
  claim you deleted something you did not.
- A "no permission" on one space WITHOUT code 99991672 means that space was never shared
  with the bot — ask for the group to be added (above). 99991672 is the other thing: a
  missing APP scope, so name it and say the admin has the grant link.
- Reading who can see a space: ["wiki", "+member-list", "--space-id", "<id>"]. Members
  come back as `openid` (a person) or `openchat` (a group) with role admin | member.
- 个人文档库 / my_library is a person's own surface; the bot's world is the spaces
  +space-list returns.
- Document CONTENT — writing, editing, searching bodies — is feishu-docs. Sending a page
  to someone is feishu-messaging. For a wiki need none of this covers, say what you
  cannot do and stop.
