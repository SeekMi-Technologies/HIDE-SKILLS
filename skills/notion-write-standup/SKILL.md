---

## name: write-standup description: Team Standup daily writing — collect data from GitHub activity \+ group chat messages, write into Notion's daily page using 3-section format \+ colored callouts. One callout per person with multi-level bullet points.

## Overview

Write daily Standup for the team into Notion. Each person gets one colored callout (fixed color) with 3 sections: **What I did today / What I plan to do tomorrow / Blockers or things to discuss**. Supports nested bullet points. Use Chinese as main language, but you can also use english sometimes

## Data Sources (3 inputs)

Collect the following in parallel before writing:

### ① GitHub Activity (via github-standup logic)

For each team member, read GitHub activity in the last 24h:

- **Commits** — `GITHUB_LIST_COMMITS` (since=24h ago, author=member's GitHub login)  
  - Notable commit → `GITHUB_GET_A_COMMIT` for message \+ changed files  
- **Pull Requests** — `GITHUB_FIND_PULL_REQUESTS` (author=member) filter updated/merged  
  - If merged → label `merged`  
  - Each with `#PR-number` \+ link  
- **Issues (optional)** — `GITHUB_LIST_REPOSITORY_ISSUES` handled by the member  
- **Do NOT read code diff**, only commit/PR messages

### ② Group Chat Messages (via message-digest logic)

Read recent messages in relevant groups over the last 24h:

- Which groups? User-specified, or default: OLA TEAM / dev / product group  
- Extract: **decisions, bug reports, design discussions, shared links, task assignments**  
- Tag each summary with the people involved

### ③ User Manual Input

If the user provides extra info in their request, append it to the corresponding person's section.

## Notion Page Targeting

1. Search for the current day's title `M/D Standup` (e.g. `7/15 Standup`, also supports `7.15 Standup` variants)  
2. If not found → create a new page with title `M/D Standup`, under the Notion Standup database or specified parent page  
3. Use `NOTION_GET_PAGE_MARKDOWN` to read page content and identify existing callout blocks  
4. **Critical: use `NOTION_FETCH_ALL_BLOCK_CONTENTS` to get each callout's block\_id** — required for writing

## Person ↔ Color Mapping (fixed, not configurable)

| Person | Callout Color | Identifier (first line inside callout) |
| :---- | :---- | :---- |
| ZYD / Yuandong | `brown_bg` | `ZYD：` or `Yuandong：` |
| Will | `green_bg` | `Will：` |
| YZY / 殷子越 | `blue_bg` | `YZY：` or `殷子越：` |
| Binghan | `yellow_bg` | `Binghan：` |
| Yucheng / 朱宇程 | `purple_bg` | `Yucheng：` or `朱宇程：` |

If a person's callout does not exist → append a new callout with the corresponding color at the end of the page.

## Content Writing Standards

### 3-Section Structure (fixed per person)

💡 ZYD：                          ← callout icon=💡, color=brown\_bg

What I did today

  • Level 1: Work topic (10-30 chars summary)

      • Level 2: Explanation / conclusion / data

          • Level 3: Technical details / sub-tasks / reference links (max 3 levels)

  • Another item

      • With GitHub reference \#PR-number or short commit SHA

      • With links (PR / doc / discussion)

What I plan to do tomorrow

  • Clear plan items (can have sub-levels)

  • Write \`-\` if nothing planned

Blockers / things to discuss tonight

  • Blockers / items to discuss (can leave empty with \`-\`)

### Multi-level Bullet Rules

- **Level 1 bullet**: Work topic / summary title  
- **Level 2 bullet**: Elaboration, reasoning, data, conclusions  
- **Level 3 bullet**: Technical details, sub-task breakdown, reference links

No more than 3 levels in principle.

### Language Style

- Concise bullet list, 10-30 chars per item  
- GitHub references with `#PR` or short SHA  
- Include important links (PR / doc / discussion)  
- Mix Chinese and English, keep technical terms untranslated (`PR merged` / `race condition` / `baseline`)  
- Tag people involved in discussion/decision items  
- No activity → write `-` (as placeholder, keep format clean)

## Write Operations

1. For each active member, find their callout block\_id  
2. If callout already has content → `NOTION_UPDATE_BLOCK` to update the callout's rich\_text  
   - **Preserve the 3 section headers** ("What I did today", "What I plan to do tomorrow", "Blockers / things to discuss")  
   - Only replace the content under each header  
3. If person has no callout → use `NOTION_APPEND_TASK_BLOCKS` or similar block creation to add a new callout at the end of the page  
   - Color according to the mapping table  
   - Icon uniform `💡`  
4. Empty field handling:  
   - 3 section headers are always preserved  
   - Empty content → write `-` as placeholder  
   - Headers are never removed

## Validation (required after every write)

**Must read back and verify** after every write operation:

1. Tool returns success → immediately call `NOTION_GET_PAGE_MARKDOWN`  
2. Confirm the content actually appears in the person's callout  
3. If readback shows content was NOT written → admit failure and show the raw error  
4. Report: write success/failure \+ which person's sections were written \+ item count per section

## Integration with Other Skills

- GitHub data collection → refer to `github-standup` skill  
- Group chat message collection → refer to `message-digest` skill  
- Notion writing → follow the write/verify pattern from `notion-write` skill

