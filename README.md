# HIDE-SKILLS

Central skills for the HIDE (Hidden Internal Dispatch Engine) general agent.

Each skill is one `skills/<name>/SKILL.md` — YAML frontmatter (`name`, `description`,
optional `scopes`) + a lean markdown body. The agent sees an always-on index of every
skill's name + description, and reads a skill's full body on demand (`read_skill`).

**Editing a skill here changes the agent's behaviour on its next turn — no redeploy**
(the core caches by commit SHA with a short TTL).

Rules:
- `description` must say what the skill does AND when to reach for it (it is the
  index line the agent routes by).
- Keep bodies lean (< ~5k tokens). Exact command templates over prose.
- Feishu command grammar is derived from the pinned lark-cli (`--help` is the source
  of truth); the skill adds curation: recipes, scopes, discipline.
- English only.
