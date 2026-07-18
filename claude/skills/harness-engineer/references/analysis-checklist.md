# Phase 0 Analysis Checklist

Best used when: Phase 0, before creating or editing any harness file.
Read before editing: nothing; this IS the investigation guide.
Related docs: `structure-and-router.md` (where findings land), `file-catalog.md` (the menu the harness plan classifies), `constitution.md`.

Do not assume the stack. Infer everything from actual files. Anything unclear gets documented as `To Confirm`, never invented.

## Repository fundamentals
- What the project does and the problem it solves, for whom (feeds `business-context.md`)
- Repository structure and directory purposes
- Tech stack, runtime versions (from lockfiles/build files, not guesses) (feeds `tech-info.md`)
- Frameworks and major libraries
- Build tools and package managers
- Local development workflow and required tooling

## Architecture
- Architecture style (layered, hexagonal, modular monolith, microservices...)
- Module boundaries and dependency direction
- Main business domains and how they map to code
- API patterns (REST, GraphQL, gRPC, messaging) and versioning
- Database usage: engines, migrations, ORM patterns, schema ownership
- External integrations and their failure modes
- Infrastructure and deployment assumptions
- Observability: logging, metrics, tracing patterns

## Code-level patterns
- Error handling patterns (exception hierarchy, result types, global handlers)
- Validation approach
- Transaction boundaries
- Naming conventions as practiced (not as documented)
- Common abstractions and shared utilities
- Anti-patterns and inconsistencies (note WHERE, with file paths — these become anti-examples)
- Divergence between stated conventions (docs, lint configs) and actual code

## Quality and process
- Testing strategy: what layers exist, coverage reality, flaky areas
- Baseline state on clean checkout: run the suite — anything already red becomes a documented known-red item ("not your regression"), not a silent landmine
- Existing quality tools (linters, static analysis, formatters) and whether CI enforces them
- CI/CD pipelines: what runs on PR, what gates merges — CI invocations are the source of truth for documented commands
- Delivery conventions: branch naming, commit message format, issue-tracker references (Jira/GitHub), semver bump rules, PR checklist
- Agent git policy: is the agent allowed to commit/push, or does the team handle all git operations manually?
- Existing documentation: what exists, what is stale, what is duplicated
- Existing agent files and their layout convention: `AGENTS.md`, `CLAUDE.md`, `.cursorrules`, `.github/copilot-instructions.md`, `.ai/`, `docs/ai/`, `.specify/`

## Ecosystem (multi-repo)
- Is this repo part of a larger system? Sibling repos (frontend, mobile, infra, commons) with URL + one-line purpose each
- Where siblings live on disk relative to this repo (parent-folder convention), and whether MCP/gh access exists
- Facts owned OUTSIDE this repo (e.g., DB schema in a separate migrations repo — then local `.sql` files are not the source of truth and the harness must say so)

## Traps and incident history
- Places where the obvious inference is wrong: intentional stubs, non-obvious file locations, `*.local.*` vs template precedence, toolchain version gates (project needs Java 11 but machine has 21 — what should an agent do?)
- Incidents behind existing hard rules: mine git history (hotfix commits, rollbacks), post-mortem notes, and the user. Each incident found becomes the cited rationale of a Do-Not-Break rule

## Sensitive areas (feeds Do Not Break)
- Security-sensitive code: auth, secrets handling, crypto, PII
- Money/financial calculation paths
- Public API contracts and consumers
- Database schema assumptions other systems depend on
- Background jobs and scheduled tasks
- Configuration and environment variables (which are load-bearing)
- Backward compatibility requirements
- Critical integrations where retries/idempotency matter

When the repo gives no explicit signal on sensitive areas, infer likely candidates from the categories above and mark every inferred item `To Confirm`. An empty Do-Not-Break section is worse than a fully-marked-uncertain one.

## Interview the user (whenever the repo doesn't answer)

Teams carry standards in their heads that the repo only hints at. Asking is a feature, not a fallback. Cover:
- Which AI tools does the team use? (drives vendor entry files)
- Are there coding guidelines written somewhere else (wiki, Notion, org handbook)?
- Naming conventions and code-style preferences? Review rituals? Testing philosophy?
- Who may commit/push — the agent or humans only? (the agent git policy)
- Declared principles for the constitution ("TDD sempre", "zero-downtime migrations"...)

Everything declared enters tagged `[declared]`. If the team has no preference on a point, propose a sensible default marked `Recommended` — never present an invention as an observed standard.

## Output of Phase 0
Before creating files, state:
1. Repo classification (small/medium/large; standalone or part of a multi-repo ecosystem) with reasoning
2. Stack summary with versions
3. Top 5 findings that will shape the harness (e.g., "no single-test command documented anywhere", "two conflicting error-handling patterns", "CI runs lint but devs don't locally", "1 test red on clean checkout")
4. List of sensitive areas found or inferred
5. Traps found and incidents mined (with the rule each one motivates)
