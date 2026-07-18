# Structure, Router, and Entry Files

Best used when: creating the AGENTS.md router, vendor entry files, and the core docs skeleton.
Read before editing: `analysis-checklist.md` findings.
Related docs: `constitution.md`, `file-catalog.md`.

## Target structure produced in the repository

```
AGENTS.md                         <- router (canonical entry point, provider-neutral)
<vendor entry files>              <- thin pointers, per detected tooling (table below)
/docs   (or /.ai)
  tech-info.md                    <- stack, frameworks, versions, toolchain, env/config
  architecture.md                 <- style, modules, boundaries, deployment
  business-context.md             <- what it does/solves; entities, rules, glossary
  conventions.md                  <- code/design patterns as practiced + traps
  guidelines.md                   <- delivery: git, commits, PRs, versioning, agent git policy
  testing.md                      <- test strategy + verified commands + known-red baseline
  extra-context.md                <- companion repos, integrations, leftover load-bearing context
  constitution.md                 <- principles + Do Not Break (see constitution.md reference)
  repository-map.md ...           <- Tier-3 workflow docs: local-development, change-workflow,
                                     review-checklist, quality-standards, troubleshooting, prompting-guide
  /guides
    <topic>-guide.md              <- Tier-3 focused tech guides, lazy creation, one owner per topic
```

Not every file exists from day one. The Phase 0 harness plan decides what exists NOW; the structure is the growth convention, not a quota. Full menu, per-file content specs, and create-when triggers: `file-catalog.md`.

**Adopt before imposing.** If the repo or its sibling repos already keep AI docs in a convention of their own (`.ai/`, `docs/ai/`, `.specify/memory/`), extend that layout in place — same file names, same style — and make AGENTS.md route into it. Relocating a working harness to match this skill's preferred tree is churn, not improvement.

**Monorepos.** When sub-projects have different stacks/build tools (`src/` Gradle, `e2e/` Playwright, `mcp/` npm), give each its own small entry file (`src/AGENTS.md`, `e2e/CLAUDE.md`) holding ONLY that project's hard rules, and route to them from the root router. The root keeps cross-project facts (deploy order, version lockstep); the sub-entry keeps local ones.

## Vendor entry files

`AGENTS.md` is the canonical, provider-neutral entry — the agents.md cross-tool standard, read natively by OpenAI Codex, Cursor (1.6+), GitHub Copilot coding agent, Zed, Google Jules, and others. Tools that use their own file get a THIN pointer, never a duplicate. Detect vendors from repo signals (`.claude/`, existing `CLAUDE.md`, `.cursor/`, `.github/copilot-instructions.md`, CI hints) or ask which tools the team uses.

| Tool | Entry file | Action |
|---|---|---|
| OpenAI Codex | `AGENTS.md` | nothing extra — reads it natively |
| Claude Code | `CLAUDE.md` | thin pointer -> AGENTS.md |
| GitHub Copilot (chat/review) | `.github/copilot-instructions.md` | thin pointer -> AGENTS.md |
| Cursor | `.cursorrules` or `.cursor/rules/` | thin pointer -> AGENTS.md (1.6+ also reads AGENTS.md natively) |
| Gemini CLI | `GEMINI.md` | thin pointer -> AGENTS.md, or set `contextFileName: "AGENTS.md"` in settings |
| Windsurf | `.windsurfrules` | thin pointer -> AGENTS.md |

```markdown
# CLAUDE.md
This project uses a provider-neutral harness. Read `AGENTS.md` and follow its routes.
<Only genuinely vendor-specific config below this line (e.g., Claude Code hooks, Cursor globs).>
```

If a vendor file already exists with real content: merge the non-duplicated content into AGENTS.md/core docs, then reduce the vendor file to the pointer. Exception: team explicitly standardized on one vendor file and maintains it — improve in place and make AGENTS.md mirror-point to it instead.

## AGENTS.md: the router

Budget: 120 lines. It routes; it does not explain. The only content that lives IN it (because every task needs it): commands, working rules, change workflow. Everything else is a route.

```markdown
# <Project Name>

<One paragraph: what this system does and for whom.>
Stack & versions: `docs/tech-info.md` · Principles: `docs/constitution.md`

## Commands
<Labels: [verified] ran clean · [FAILED] ran and failed · [verified in CI] env-only local failure, green in CI (name the workflow) · [unverified: <reason>]. Mirror CI invocations — never invent flags. Anything red on clean checkout stays documented here as known-red: "<test> fails on clean checkout — not your regression".>
- build: `<cmd>` [verified]
- test (all): `<cmd>` [verified]
- test (single): `<cmd>` [verified]
- lint/format: `<cmd>` [verified]
- run locally: `<cmd>` [verified | unverified: <reason>]
<If the toolchain is version-gated (e.g. requires Java 11), state the preflight check and what to do on mismatch.>

## Related repositories
<Only when part of a multi-repo ecosystem. One line each: URL/local path + purpose. Name explicitly any fact owned by another repo (e.g. "DB schema lives in <migrations-repo>; local .sql files are NOT the source of truth").>

## Routes
Read the file matching your task before touching code. Like skills: load only what the task needs.
| Topic | File | Read when |
|---|---|---|
| Stack & toolchain | docs/tech-info.md | Setup, versions, env vars, config precedence |
| Architecture | docs/architecture.md | First contact; moving module boundaries |
| Principles & Do Not Break | docs/constitution.md | ANY change (always) |
| Business context | docs/business-context.md | Changing domain logic |
| Conventions | docs/conventions.md | Writing any code |
| Delivery workflow | docs/guidelines.md | Branching, committing, PRs, releasing |
| Testing | docs/testing.md | Writing or running tests |
| Ecosystem | docs/extra-context.md | Touching integrations / companion repos |
| <topic> | docs/guides/<topic>-guide.md | <trigger> |
<Every route points to a file that EXISTS. No dead routes. New file -> new route, same commit.>

## Working rules
- Read the routed files and golden examples before changing code.
- Do not invent APIs, dependencies, environment variables, or business rules.
- Follow existing patterns; prefer minimal, safe, reviewable changes.
- Update tests with every behavior change; run the relevant subset before finishing.
- Avoid broad refactors unless explicitly requested.
- Preserve backward compatibility unless explicitly instructed otherwise.
- When a doc contradicts the code, trust the code and note the drift.
- Git policy: <who commits/pushes — the agent following docs/guidelines.md, or the user only? State it; agents default wrong in both directions.>
- Ask only when blocked; otherwise document assumptions inline.
<Adapt to the repo; zero-adaptation copies are a smell.>

## Change workflow
1. Route: load the docs matching the task (table above). Constitution always.
2. Locate relevant files; anchor on the golden examples in the routed docs.
3. Plan the minimal change; note blast radius.
4. Implement following observed patterns.
5. Tests: add/update, run `<single-test cmd>` then the affected suite.
6. Lint/format.
7. Self-review against `docs/constitution.md` (compliance check).
8. Summarize: files changed, tests, risks, assumptions.

## Adding new guides
When a topic accumulates repo-specific rules with no home: create `docs/guides/<topic>-guide.md`
(spec in the harness), add the route here, same commit. One topic, one owner file.

Last verified: <date> (<short git sha>)
```

**Anti-rot rule for the router (and every harness file):** never hardcode a fact that changes every release — current version, "PROD is at X", dependency patch levels. Point at the live source instead ("version: `gradle.properties:appVersion` — read it live, never trust a doc"). Facts that rot silently are how a harness loses the agent's trust.

## Quality bar

- Commands: executed during creation; exact working invocation with flags. Single-test command is mandatory.
- Routes: every route resolves; every doc has a route. Orphan docs and dead routes fail validation.
- Golden examples cited in docs compile/pass lint today.
- Stack versions: from files, or `To Confirm`.
