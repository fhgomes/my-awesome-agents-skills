# Harness File Catalog

Best used when: planning which files to create (the Phase 0 harness plan) and writing them (Phases 2-4).
Read before editing: `structure-and-router.md` (every file created gets a route, same commit).
Related docs: `constitution.md`.

## Identify everything, create by need

This catalog is the full menu of harness files. The discipline mirrors how skills and agents work: **the router names what exists and when to load it; agents pull files on demand**. So the job splits in two:

1. **Identification is total.** In Phase 0, classify EVERY catalog entry for this repo: `create now` / `create later` (topic exists, content below threshold — record it) / `n/a` (technology absent). The classified list is the **harness plan**, shown to the user before writing anything.
2. **Creation is tiered by repo size.** A file is created only when it has real repo-specific content NOW (~30+ lines after removing everything findable in official docs). Until then its content lives in the closest existing owner (usually the router or a core doc), and the split happens later via the "Adding new guides" convention. Never create empty placeholders; a "later" entry in the report is worth more than a hollow file.

| Tier | Repo profile | What gets created |
|---|---|---|
| 1 | Every repo, even tiny | `AGENTS.md` router + vendor pointers. Small repos stop here: compressed tech-info, commands, rules, and Do-Not-Break live inline in the router. |
| 2 | Real codebase with patterns worth writing down | Core docs menu — router sections move out to owner files as they outgrow it. |
| 3 | Large / multi-module / team-scale | Workflow docs + focused tech guides, split per topic as content accumulates. |

## Shared format (all files)

- Header: `Best used when / Read before editing / Related docs` (3 lines) — this is what makes routing work.
- Golden example: at least one real repo file cited per pattern; verify it compiles/passes lint today.
- Anti-patterns actually found in the repo, with file paths ("do not follow `legacy/OldClient`, phased out").
- Observed standards vs proposals: where the repo has no standard, propose one marked `Recommended`, visually distinct.
- Budget: ~150 lines per file. Footer: `Last verified: <date> (<short git sha>)`.
- No facts that rot: never hardcode current versions or "PROD is at X" — point at the live source file.
- One owner per fact: a rule lives in exactly one file; other files link to it.

## Tier 2 — core docs (`docs/*.md` or `.ai/*.md`)

`tech-info.md` — what kind of project this is: languages and runtime versions (from lockfiles/build files, never guessed); frameworks and major libraries; build tools and package managers; database, messaging, testing and quality tools; auth approach and API style; deployment model in 2 lines; important directories and config files; required local tooling and the **preflight check** when the toolchain is version-gated ("requires Java 11 — check `java -version` first; on mismatch ask, don't improvise"); load-bearing env vars; config precedence (`*.local.*` overrides its committed template twin, gitignored, holds real credentials); known assumptions and `To Confirm` list.

`architecture.md` — style (layered, hexagonal, modular monolith, microservices...); module map with one-line responsibility each and dependency direction; request/data/persistence flow; integration flow; infrastructure assumptions; architectural risks; one Mermaid diagram only if it reflects real structure.

`business-context.md` — problem solved and for whom; users; main capabilities and workflows; core entities and **domain glossary** using the terms the code actually uses; business rules each citing their implementing code path (`Implementation: RecEmailMessageFactory.createCodeRedemptionMessage()`) or marked `To Confirm`; 2-3 real scenarios end to end; areas where technically-valid changes are business-invalid (money math, permissions, compliance). Split `business-<module>.md` (~80 lines) when a module's rules exceed ~40 lines or have a distinct owner; critical invariants get promoted to the constitution, which links back.

`conventions.md` — how code is written HERE: naming as practiced (not as documented); package/folder organization; DTO/entity/domain separation; error-handling standards and exception hierarchy; validation approach; transaction boundaries; logging standards; null-handling; API response conventions; formatting beyond the linter; and the repo's **traps** — intentional stubs, non-obvious locations, anywhere the obvious inference is wrong. When one framework's section outgrows this file, split a focused guide and leave the link.

`guidelines.md` — how work ships: branch naming with real examples (`feat/HN-1071_dark_mode`); commit format with the issue-tracker reference syntax exactly (brackets or not; `refs`/`fixes`/`closes`); semver bump rules and every file the version touches (lockstep list); PR checklist and review process; the **agent git policy** (may the agent commit/push, or user-only?). Absence of a doc is not absence of a convention — infer from recent `git log`, mark `[inferred]`.

`testing.md` — philosophy and pyramid for THIS repo; naming/structure via examples copied from real tests; assertion style; mocking rules (what gets mocked, what never); fixtures/data builders; DB and API testing (Testcontainers vs in-memory, slice tests); negative-scenario expectations; subset commands all `[verified]`; known flaky/slow areas; **known-red baseline** ("X fails on clean checkout — not your regression").

`extra-context.md` — the ecosystem: **companion repos** (UI, mobile, BE, e2e, infra, commons) with URL + one-line purpose + disk location relative to this repo; facts owned by another repo ("DB schema lives in <migrations-repo>; local `.sql` files are NOT the source of truth"); external integrations and auth in practical detail; anything load-bearing that fits no other file.

`constitution.md` — versioned principles + non-negotiables + Do Not Break. See the `constitution.md` reference.

## Tier 3 — workflow docs (`docs/*.md`)

- `repository-map.md` — directory tree with purpose per folder; entry points; files agents should inspect first; files to avoid editing unless necessary; generated/build folders to ignore. Create when: the repo is big enough that agents waste context finding things.
- `local-development.md` — environment setup end to end: tools, env vars, starting dependencies (Compose, DB, broker), running app/tests/lint/build/migrations, troubleshooting, known local pitfalls ("works in CI but not locally"). Create when: setup is more than install-and-run; below that it lives in `tech-info.md`.
- `change-workflow.md` — the repo's change lifecycle when it has gates beyond the router's generic 8 steps: DEV-first deploy gating, spec-driven workflows, worktree/parallel-agent discipline, release promotion rules. Create when: those gates exist.
- `review-checklist.md` — repo-specific review gate: correctness, business-rule preservation, security, performance, error handling, logging, tests, naming, architecture boundaries, backward compatibility, config/migration/API contract impact. Create when: AI output gets reviewed against repo rules, or agents self-review before finishing.
- `quality-standards.md` — definition of done, coverage expectations, static analysis, migration safety, API compatibility, dependency-update rules. Create when: real gates exist (CI thresholds, release rules) worth centralizing; otherwise fold into `guidelines.md`.
- `troubleshooting.md` — known failure modes with symptoms and fixes. Create when: recurring pitfalls are observed or documented in issues/incidents.
- `prompting-guide.md` — reusable prompt patterns per task type (implement feature, fix bug, write tests, refactor safely, review, investigate perf/security). Every pattern must instruct: read the routed harness docs first, inspect existing patterns, propose a short plan, minimal safe change, update tests, summarize risks. Create when: the team asks for it or is already sharing prompts ad hoc.

## Tier 3 — focused tech guides (`docs/guides/<topic>-guide.md`)

Only for technologies actually present. One-line content spec each; all follow the shared format.

**Java / Spring:**
- `java-guide.md` — version features in use vs avoided (records, sealed, virtual threads), idioms, null-handling.
- `spring-backend-guide.md` — component patterns as structured HERE: controllers, services, repositories, DI style, where `@Transactional` goes and where it must not, bean validation, configuration properties, profiles.
- `junit-testing-guide.md` — JUnit 5 specifics: nested, parameterized, assertion style, Mockito rules, testing exceptions/transactions/controllers/repositories, avoiding brittle tests — with real test files as golden examples.
- `database-guide.md` (or `jpa-hibernate-guide.md`) — engines, migration tool and naming, rollback policy, which schema changes need review, ORM patterns and known traps (N+1, fetch strategies), seed/test data.
- `rest-api-guide.md` — style and versioning, response envelope and error contract, pagination, idempotency, deprecation policy, contract source of truth.
- `messaging-guide.md` — broker patterns, producer/consumer conventions, retry/DLQ/idempotency rules.

**Frontend:**
- `frontend-guide.md` — component structure and colocation, styling approach and what is banned, accessibility expectations.
- `state-management-guide.md` — what state goes where (server cache vs UI state vs URL).
- `api-client-guide.md` — the canonical client ("always import `api/client.ts` — never create ad-hoc axios instances"), auth/interceptors, error and loading conventions.
- `frontend-testing-guide.md` — unit/integration/E2E split, selector strategy, page-object rules.

**Node / TypeScript:**
- `typescript-guide.md` — strictness level and `any` policy, shared type location, contract source of truth (OpenAPI, zod).
- `node-guide.md` — error handling (exceptions vs result types), async patterns, dependency management.

**Cross-cutting (any stack):**
- `security-guide.md` — auth/authz, secrets handling, input validation baseline, sensitive paths. Overlap rule: WHAT must hold → constitution; HOW to implement → here.
- `logging-observability-guide.md` — levels and structure, correlation IDs, what NEVER gets logged (PII, secrets), metrics/tracing patterns.
- `error-handling-guide.md` — hierarchy, global handlers, retry/idempotency conventions (combine with logging while small).
- `performance-guide.md` — only if real performance-sensitive paths exist; name them, state budgets, cite measurement tooling. Generic performance advice in a CRUD is filler — skip and record.

## Never create

- Files for technologies the repo does not use.
- Guides restating official documentation.
- Duplicate summaries of other harness files.
- Empty placeholders "for later" — a recorded `create later` entry beats a hollow file.
