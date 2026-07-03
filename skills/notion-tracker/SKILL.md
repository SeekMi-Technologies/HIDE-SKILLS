---
name: notion-tracker
description: Log work items, meeting action items, or decisions into the team's Notion tracker (a database or page). Use when asked to record/log/track something in Notion.
---
You have Notion tools scoped for tracker work: search, read, and gated writes.

Workflow (a database tracker — the common case):
1. Locate the tracker: NOTION_SEARCH_NOTION_PAGE with the tracker's name (ask the
   user for the name if you have no hint; the integration only sees SHARED pages —
   if search finds nothing, say the page may not be shared with the integration).
2. Understand the schema: NOTION_FETCH_DATABASE with the database id — read the
   property names/types so a row insert matches the real columns.
3. Dedupe before writing: NOTION_QUERY_DATABASE — if an equivalent row already
   exists (same title/topic), UPDATE nothing, report it instead of duplicating.
4. Write one row per item: NOTION_INSERT_ROW_DATABASE. Fill the title property and
   whatever schema fields you have real values for; never invent values. Include a
   source link (e.g. the GitHub issue URL) when the item came from another system.

For a page-style tracker (a plain page, not a database):
- Read it first (NOTION_GET_PAGE_MARKDOWN) to match the page's existing structure,
  then append with NOTION_ADD_PAGE_CONTENT. Create a new page
  (NOTION_CREATE_NOTION_PAGE) only when explicitly asked.

Rules:
- Every write pauses for the user's confirmation — the platform sends the card.
  Batch related rows in one turn so the user reviews them as a unit.
- After the write executes, report exactly what landed (row titles + page).
- If Notion tools are not in your surface, say so — never claim a write happened.
