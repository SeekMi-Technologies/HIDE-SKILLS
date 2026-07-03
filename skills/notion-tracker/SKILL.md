---
name: notion-tracker
description: Log work items, meeting action items, or decisions into Notion (a database or page, e.g. under a standup page). Use when asked to record/log/track/整理到 something in Notion.
---
You have Notion tools scoped for tracker work: search, read, and writes.

Locate the target:
1. NOTION_SEARCH_NOTION_PAGE with the page/database name (the integration only sees
   SHARED pages — if search finds nothing, say the page may not be shared).
2. NOTION_GET_PAGE_MARKDOWN to see the page's current structure BEFORE writing.

Database tracker: NOTION_FETCH_DATABASE (schema) → NOTION_QUERY_DATABASE (dedupe)
→ one NOTION_INSERT_ROW_DATABASE per item; never invent property values.

Append under a page (e.g. "放到 7/2 Standup 底下"):
- NOTION_ADD_PAGE_CONTENT with parent_block_id = the PAGE id appends at the page's
  end. Appending INSIDE a specific section/callout needs that block's id — if you
  only have the page markdown (no block ids), append at page end with a clear
  heading (e.g. "HIDE 对齐 07/03 — TODO") instead of guessing block ids.
- Batch related items into ONE content block so the page stays tidy.

VERIFY EVERY WRITE (writes run without human review):
- Tool result must show success; then READ BACK (NOTION_GET_PAGE_MARKDOWN /
  NOTION_QUERY_DATABASE) and confirm your content is actually present.
- Report exactly what the read-back shows — never what you intended to write.
  If the read-back lacks your content, say the write failed and show the error.

Destructive Notion changes (REPLACE/UPDATE existing content) pause for the user's
confirmation; searches, reads, inserts and appends run directly.
