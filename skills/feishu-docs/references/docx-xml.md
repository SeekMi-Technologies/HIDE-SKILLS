# DocxXML — the native grammar for `docs +create` / `docs +update` content

DocxXML is an HTML subset. It is the default `--content` format and round-trips
losslessly (`docs +fetch` returns it). Never pass `--doc-format markdown` — that is a
lossy one-way import that renders half-literal.

## Standard HTML tags (unchanged semantics)
`p, h1-h9, ul, ol, li, table, thead, tbody, tr, th, td, blockquote, pre, code, hr,
img, b, em, u, del, a, br, span`.

## Extended tags

Block:
- `<title>…</title>` — the document title, exactly one per doc (`align`).
- `<checkbox done="true|false">…</checkbox>` — a to-do item.

Containers (a container wraps child blocks):
- `<callout emoji="💡" background-color="light-yellow" border-color="yellow">` — a
  highlight box; children are text / heading / list / checkbox / quote only.
- `<grid><column width-ratio="0.5">…</column>…</grid>` — columns; `width-ratio` sums to 1.
- `<pre lang="go" caption="…"><code>…</code></pre>` — a code block; the code MUST sit
  inside the inner `<code>`, never directly under `<pre>`.
- `<whiteboard type="svg">…self-contained SVG…</whiteboard>` — an embedded board (a
  simple diagram inline; complex boards are a separate flow).
- `<bookmark name="标题" href="https://…"></bookmark>` — both attributes required.

Inline:
- `<cite type="user" user-id="ou_xxx"></cite>` — a clickable @mention (see rule below).
- `<cite type="doc" doc-id="docx_token"></cite>` — a @document reference.
- `<latex>E = mc^2</latex>` — an inline formula.
- `<img href="https://…"/>` or `<img src="IMG_TOKEN" width="800" caption="…" name="图.png"/>`.
- `<a type="url-preview" href="…">标题</a>` — a preview card.

Text-block attributes: `align="left|center|right"` on `p / h1-h9 / li / checkbox`;
ordered-list items use `seq="auto"` for automatic numbering.

## Escaping — tags are NEVER escaped, only text content
- ❌ `&lt;p&gt;内容&lt;/p&gt;` (the tag was escaped)
- ✅ `<p>A &amp; B：1 &lt; 2</p>` (only the `&` and `<` in the TEXT are escaped)
- `<` → `&lt;`, `>` → `&gt;`, `&` → `&amp;`, a newline → `<br/>`.

## Rules that bite
- Inline styles nest in a fixed order (outer → inner), closing strictly reversed:
  `<a> → <b> → <em> → <del> → <u> → <code> → <span> → text`.
- Consecutive same-type list items auto-merge into one `<ul>`/`<ol>`; every new item
  must sit inside a `<ul>`/`<ol>`; nest a sub-list inside its parent `<li>`.
- Tables: `<colgroup><col span="2" width="120"/></colgroup>` right after `<table>` sets
  column widths; `<th>`/`<td>` take `background-color` and `vertical-align`; a header row
  goes in `<thead>` with `<th>`, the rest in `<tbody>` with `<td>`; merged cells emit
  `colspan`/`rowspan` only on the origin cell.

## Writing a person as a @mention
When you have a person's `open_id` (from the [Team directory], an IM event, a task,
etc.), write them as `<cite type="user" user-id="ou_xxx"></cite>` so the doc renders a
clickable @mention instead of plain text. Resolve a bare name to an `open_id` through
the feishu-contacts ladder FIRST; if it cannot be resolved, write the plain name rather
than guess an id.

## Colors and emoji
- Prefer named colors (or `rgb()` / `rgba()`). Base 7: `red, orange, yellow, green,
  blue, purple, gray`. Text/callout text and callout border take a base color; a text
  or cell `background-color` also takes `light-{color}` + `medium-gray`; a callout
  `background-color` takes `gray` + `light-{color}` + `medium-{color}`.
- Common emoji: 💡✅❌📝❓❗👍❤️📌🏁⭐.

## Editing an existing doc — block-id lifecycle
`docs +update` operates on block ids from a `docs +fetch --detail with-ids` read:
- `--command str_replace --pattern <inline text> --content <xml>` (empty content deletes).
- `--command block_insert_after|block_replace --block-id <id> --content <xml>`.
- `--command block_delete --block-id <id[,id2]>`.
- `--command block_move_after|block_copy_insert_after --block-id <anchor> --src-block-ids <ids>`.
After `overwrite` / `block_replace` / `block_delete`, the affected old ids are dead —
do NOT reuse them; after an insert/copy, re-`fetch` to learn the new ids before the next
edit. Skipping this corrupts the document.

## Full example
```xml
<title>文档标题</title>
<h1>一级标题</h1>
<p><b>加粗</b>，<span text-color="green">绿字</span></p>
<callout emoji="💡" background-color="light-yellow" border-color="yellow">
  <p>高亮框内容（子块仅支持文本/标题/列表/待办/引用）</p>
</callout>
<checkbox done="false">未完成事项</checkbox>
<grid>
  <column width-ratio="0.5"><p>左栏</p></column>
  <column width-ratio="0.5"><p>右栏</p></column>
</grid>
<table>
  <thead><tr><th background-color="light-gray">表头</th></tr></thead>
  <tbody><tr><td>单元格</td></tr></tbody>
</table>
<p><cite type="user" user-id="ou_xxx"></cite> 请看 <cite type="doc" doc-id="DOC_TOKEN"></cite></p>
<ol><li seq="auto">第一项</li><li seq="auto">第二项</li></ol>
<pre lang="go" caption="示例"><code>fmt.Println("hello")</code></pre>
<hr/>
```
