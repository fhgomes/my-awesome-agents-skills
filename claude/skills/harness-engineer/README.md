# harness-engineer (Claude skill format)

The same [harness-engineer](../../../skills/harness-engineer/) skill, packaged in the **Claude Agent Skills format**: a lean `SKILL.md` entry point plus `references/` files that Claude loads on demand per phase (progressive disclosure — the skill practices the same routing architecture it builds).

## Layout

```
harness-engineer/
  SKILL.md                        entry point: mission, principles, phases (always loaded)
  references/
    analysis-checklist.md         Phase 0 — full identification checklist + user interview
    constitution.md               Phase 1 — principles + Do-Not-Break derivation and template
    structure-and-router.md       Phase 2 — AGENTS.md router template + vendor entry files
    file-catalog.md               Phases 3-4 — full file menu with per-file specs and create-when triggers
```

## Install

- **claude.ai / Claude Desktop**: upload this folder (or a zip of it) as a Skill in Settings → Capabilities.
- **Claude Code (project)**: copy the folder to `.claude/skills/harness-engineer/` in your repo.
- **Claude Code (personal, all projects)**: copy to `~/.claude/skills/harness-engineer/`.

Then ask: *"cria o harness desse projeto"* / *"make this repo AI-ready"* / *"monta o AGENTS.md"*.

## Which format should I use?

- **`skills/harness-engineer/`** (single `SKILL.md`) — universal drop-in: works with any agent runtime that loads one instruction file (OpenClaw, custom agents, pasting as a system prompt).
- **`claude/skills/harness-engineer/`** (this one) — for Claude runtimes: keeps the always-loaded entry lean and pulls phase detail only when needed, saving context on every invocation.

Content is kept in sync between the two; the split is packaging, not substance.
