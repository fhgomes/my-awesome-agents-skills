# harness-engineer

Turn what your team already knows into an AI harness: structured Markdown context (router + guides) that makes any AI coding agent faster, safer, and higher-quality in your project.

## Purpose

AI coding agents get lost in repos without context: they hallucinate commands, break invariants nobody wrote down, and ignore team conventions that only live in people's heads. This skill deeply identifies a repository — stack, architecture, purpose, patterns, companion projects, incident history — and **harvests** that knowledge into a routed documentation layer any LLM can load on demand, exactly like skills and agents work: a router names what exists and when to read it; agents pull only what the task needs.

## What it produces

- **`AGENTS.md`** — the provider-neutral router (the agents.md standard: Codex, Cursor 1.6+, Copilot coding agent read it natively): verified commands, task routes, working rules, change workflow.
- **Vendor entry files** — thin pointers for the tools you use: `CLAUDE.md` (Claude Code), `.github/copilot-instructions.md` (Copilot), `.cursorrules` (Cursor), `GEMINI.md` (Gemini CLI).
- **Core docs** (`docs/` or `.ai/`) — `tech-info.md`, `architecture.md`, `business-context.md`, `conventions.md`, `guidelines.md`, `testing.md`, `extra-context.md`, plus a versioned `constitution.md` with Do-Not-Break rules.
- **Workflow docs and focused tech guides** — `repository-map.md`, `review-checklist.md`, `junit-testing-guide.md`, `spring-backend-guide.md`... created only when the project's size justifies them.

## Key ideas

- **Identify everything, create by need** — the full file catalog is classified for every repo (create now / later / n-a); creation is tiered by project size so the harness never bloats or rots.
- **Harvest, then ask, then propose** — the repo is the primary source; where it has no standard, the skill interviews you about team preferences (naming, code style, review rules); if there are none, it proposes defaults marked `Recommended`.
- **Verified or labeled** — every documented command is actually executed (`[verified]` / `[FAILED]` / `[verified in CI]` / `[unverified: reason]`); red-on-clean-checkout tests are documented as known-red.
- **Rules cite their scars** — Do-Not-Break rules reference the incidents that created them.
- **Anti-rot** — no hardcoded facts that expire; every file carries `Last verified` metadata.

## Quick start

Drop `SKILL.md` into your agent's skills folder and ask:

> "cria o harness desse projeto" / "make this repo AI-ready" / "monta o AGENTS.md"

The skill will identify the project, show you the harness plan, interview you about missing definitions, and build the harness sized to your repo.

**Using Claude** (claude.ai, Claude Desktop, or Claude Code)? Prefer the [Claude skill format variant](../../claude/skills/harness-engineer/) — same content, split into `SKILL.md` + on-demand `references/` to save context.
