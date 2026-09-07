# Testing

**Best used when:** a codebase has no automated tests, has tests nobody trusts, or has an AI coding tool that says "tests pass" without running anything — and you want a first day, a first week, and a way to make the rules stick.
**Read before:** picking a test runner, asking an agent to "add tests", or writing a testing section into `AGENTS.md` / `CLAUDE.md`.
**See also:** [../../skills/test-engineer/SKILL.md](../../skills/test-engineer/SKILL.md) (the agent skill that applies these rules) · [enforcement/README.md](./enforcement/README.md) (how to make them mandatory)

Five guides, one enforcement kit, one skill. The guides are opinionated and cite the incidents behind each rule; every file is readable on its own, so start with the one that matches your situation and ignore the rest until you need it.

---

## Start here

| Your situation | Read, in order | First thing to do today |
|---|---|---|
| **Greenfield** — new repo, no tests yet | [testing-from-zero.md](./testing-from-zero.md) section 5, then the stack guide for your code | One smoke test that you deliberately break and watch go red. Prove the harness before you trust its verdict. Then put the single-test command in the README and make CI a required check while the suite is one test and nobody can object |
| **Legacy** — existing repo, zero or untrusted tests | [testing-from-zero.md](./testing-from-zero.md) section 6, then the stack guide's legacy table | Get the runner to execute anything, record the known-red baseline in `docs/testing.md` with counts and a date, and write a characterization test on the scariest path. No big-bang coverage sprint |
| **"I use an AI tool and want it to actually run tests"** | [testing-from-zero.md](./testing-from-zero.md) section 9 (prompt template + fake-coverage greps), then [enforcement/README.md](./enforcement/README.md) | Put the 12-line testing block in `AGENTS.md`, install the two git hooks, add the CI required check. Instructions are context, not enforcement — the hook and the CI gate are what make "tests pass" a measured fact |
| **Adding a specific layer** | The stack guide: [backend](./backend-testing-guide.md), [frontend](./frontend-testing-guide.md), [mobile](./mobile-testing-guide.md), [e2e](./e2e-testing-guide.md) | Use the decision table in section 1 of any guide to pick the layer before writing a line |

The position all five guides share: **test at the highest layer that is still fast, deterministic and local.** For a service that owns a database that is the integration test with a real database in a container; for a web UI it is the component test; for a mobile app it is the widget test; mocks are for pure logic. If you fix a bug, write the test that would have caught it.

## Files

| File | One line |
|---|---|
| [testing-from-zero.md](./testing-from-zero.md) | Language-agnostic entry point: layers, pyramid vs trophy, unit-vs-integration position, what to test first, Day 1 / Week 1 for greenfield and legacy, the AI prompt template, the 12-smell catalogue, what `docs/testing.md` must contain |
| [backend-testing-guide.md](./backend-testing-guide.md) | Java/Spring: integration-first with Testcontainers, `AbstractIntegrationTest` with one schema per Spring context, seeding through the API, RFC 7807 assertions, ownership 403-never-404, Mockito for pure logic, `cleanTest` and the module-scoped single-test command; Node/Python/Go table |
| [frontend-testing-guide.md](./frontend-testing-guide.md) | React/TypeScript: the trophy, vitest with a separate config and `css: true`, the `npm test` vs Playwright scope boundary, request-shape tests without a mocking library, Testing Library query priority, MSW, coverage ratchet; Vue/Svelte/Angular table |
| [mobile-testing-guide.md](./mobile-testing-guide.md) | Flutter: pyramid with widget tests as the fat middle, MobX store tests, finder priority, `pump` vs `pumpAndSettle`, goldens for design-system components only, integration tests behind a prod guard, the device-matrix table; React Native notes |
| [e2e-testing-guide.md](./e2e-testing-guide.md) | Playwright: page objects, selector hierarchy, marker-based test data and teardown, auth via API, the production guard with manual redirect following, SMTP refusal in the app, subpath deploys, config hygiene, skips vs flake, fake and real lanes, post-deploy smoke |
| [enforcement/README.md](./enforcement/README.md) | The three layers (instructions, hooks, CI), what each can and cannot guarantee, the provider-agnostic recipe, the `[skip-tests] reason:` trailer, per-tool comparison matrix |
| [enforcement/claude-code.md](./enforcement/claude-code.md) | `CLAUDE.md` + `.claude/rules/`, `PostToolUse` and `Stop` hooks, `@AGENTS.md` import |
| [enforcement/codex.md](./enforcement/codex.md) | Native `AGENTS.md`, `.codex/config.toml` sandbox and approvals, `.codex/hooks.json` |
| [enforcement/gemini-cli.md](./enforcement/gemini-cli.md) | `GEMINI.md`, reading `AGENTS.md` via `context.fileName`, `AfterTool` / `AfterAgent` hooks and the stdout-only-JSON rule |
| [enforcement/copilot.md](./enforcement/copilot.md) | `.github/copilot-instructions.md`, `applyTo:` path rules, `.github/hooks/` with `preToolUse` and `agentStop`, why the cloud agent still needs CI |
| [enforcement/cursor-cline-aider.md](./enforcement/cursor-cline-aider.md) | Cursor rules and hooks, Cline rules, aider `auto-test`, Continue rules, and running DeepSeek or any model behind them |
| [enforcement/hooks/pre-commit-tests.sh](./enforcement/hooks/pre-commit-tests.sh) | Git `pre-commit`: maps staged files to the tests that cover them (Gradle module-scoped, vitest `related`, Flutter, Go, pytest) and runs only those |
| [enforcement/hooks/require-spec-for-feature.sh](./enforcement/hooks/require-spec-for-feature.sh) | Git `commit-msg` and CI `--range`: a `feat`/`fix` that touches code must touch a test or carry `[skip-tests] reason:` |
| [enforcement/hooks/claude-post-edit-test.sh](./enforcement/hooks/claude-post-edit-test.sh) | Agent post-edit hook: runs the affected test, records GREEN/RED/NOTEST and a content hash; works for Claude Code, Codex, Gemini CLI, Cursor, Copilot |
| [enforcement/hooks/claude-stop-gate.sh](./enforcement/hooks/claude-stop-gate.sh) | Agent finish gate: refuses "done" on red, on a stale green, or on a diff that adds `@Disabled` / `.only(` / `skip(true`; exit 2 or JSON |
| [enforcement/hooks/ci-required-check.yml](./enforcement/hooks/ci-required-check.yml) | GitHub Actions: backend, frontend, e2e, spec-guard, and the single `required` job to protect the branch with |
| [../../skills/test-engineer/SKILL.md](../../skills/test-engineer/SKILL.md) | The skill: layer table, red-then-green with pasted output, refusals, 16-point review checklist, fake-coverage greps, standard response format. Self-contained — install the folder alone |

## Recommendations vs enforcement

The guides recommend; nothing in them blocks anything, and an instruction file is read, not obeyed.
`enforcement/` is where a rule becomes a hook that refuses a commit or a finish, and a CI check that refuses a merge; those files reference the guides and never re-teach the practice.
Layers 1 (instructions) and 2 (hooks) are conveniences; layer 3 (a required CI check with admin bypass off) is the only guarantee, because it is the only one that does not care which tool, machine or human made the change.

## The skill

[skills/test-engineer/](../../skills/test-engineer/) packages the positions above as an agent skill: it decides the layer before writing, demands red-then-green with both outputs pasted and the test count delta, refuses to weaken assertions or narrow the suite, and ships a review checklist. Copy the folder into any runtime that loads a `SKILL.md`; it does not depend on this directory.

_Last reviewed: 2026-09-07._
