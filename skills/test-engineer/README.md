# Test Engineer — Tests That Would Have Caught The Bug

**SKILL.md** — drop-in skill for any runtime that loads a SKILL.md.

## What it does

Turns "add tests" into a verifiable procedure instead of a promise. The skill makes the agent
(or the human using it) do the boring part:

- Pick the layer before writing a line — integration-first for services, mocks only for pure
  logic, component tests for UI, E2E only for cross-page flows.
- Write the failing test first, paste the red output, then the green, and state the test count
  before and after.
- Refuse the shortcuts: no weakened assertions, no `@Disabled` / `test.skip(true)` / `.only`, no
  narrowing the suite to hide a failure, no run pointed at a production host.
- Assert results rather than internal calls; assert failures by status plus machine-readable
  code; treat an ownership breach as 403, never 404.
- Read the repo's known-red baseline before calling a red a regression, and detect fake coverage
  with six greps.
- Give a first-day plan for a repo with no tests at all: prove the harness, write down the
  single-test command, put it in CI, then start testing behaviour.

## What's inside

- `SKILL.md` — the whole skill: identity, ten operating principles with the layer-decision table,
  routing, a 16-point review checklist, refusals with push-back wording, fake-coverage greps, and
  the standard response format.

No `references/` folder and no scripts — everything the skill needs is in the one file.

This folder is **self-contained** — copy it into any runtime that loads a SKILL.md (Claude,
OpenClaw, custom agents) and it works as-is. No other part of this repository is required.

## See also (optional)

Longer-form material lives in [../../guides/testing/](../../guides/testing/) (from-zero, backend,
frontend, mobile and E2E guides) and, for making the rules mandatory through instruction files,
tool hooks and CI gates, in [../../guides/testing/enforcement/](../../guides/testing/enforcement/).
They are alternatives and deeper reading, not prerequisites.

## Trigger keywords

`test`, `spec`, `coverage`, `flaky`, `red CI`, `TDD`, `unit vs integration`, `Testcontainers`,
`MockMvc`, `JUnit`, `Mockito`, `vitest`, `Testing Library`, `Playwright`, `Flutter widget test`,
`mock`, `fixture`, `teardown`, `golden test`, `mutation testing`, `single-test command`,
`known-red`, `skip-tests`, "is this tested?", "the AI says done but nothing is tested".

_Last reviewed: 2026-09-07._
