# Testing From Zero

**Best used when:** you own a codebase with no automated tests — greenfield or ten years old — and you want a first day and a first week that actually pay off, with or without an AI coding tool driving the keyboard.
**Read before:** writing your first test file, choosing a test runner, or asking an AI agent to "add tests".
**See also:** [backend-testing-guide.md](./backend-testing-guide.md) · [frontend-testing-guide.md](./frontend-testing-guide.md) · [mobile-testing-guide.md](./mobile-testing-guide.md) · [e2e-testing-guide.md](./e2e-testing-guide.md) · [enforcement/README.md](./enforcement/README.md) · [../../skills/test-engineer/SKILL.md](../../skills/test-engineer/SKILL.md)

This guide is language-agnostic. Every rule here holds in Java, TypeScript, Dart, Go, Python or Ruby. The stack guides above add the commands.

---

## 1. Why layers exist

A test layer is defined by what it can see. Pick the layer by the bug you are trying to catch, not by habit.

| Layer | What it can see | What it cannot see | Typical speed | Who runs it, when |
|---|---|---|---|---|
| Unit (no framework) | One function or class, all its branches, edge cases | Wiring, config, serialization, auth, SQL | 1-10 ms each | Every save, every commit, CI |
| Component / widget | One UI piece rendering and reacting to user events | Routing, real network, real session, layout on a device | 5-50 ms each | Every save, every commit, CI |
| Integration (real DB, real framework context) | Controllers, auth, ownership checks, transactions, ORM filters, exception-to-status mapping — together | The browser, the CDN, the deployed config, cross-service assembly | 20 ms-2 s each | Every commit locally, full run in CI |
| Contract / API-client | The exact request shape your client sends, the response shape it survives | Whether the real server accepts it | 1-10 ms each | With unit tests |
| E2E (browser or device) | The real assembly: navigation, session, layout, third parties | Anything below the UI it does not render; internal states | 2-60 s each | Pre-merge subset, full suite nightly or pre-release |

Two rules follow. **Test at the highest layer that is still fast, deterministic and local.** And: a layer that cannot see the bug class you keep shipping is the wrong place to add tests, no matter how green it gets.

---

## 2. Pyramid vs trophy: the shape is a budget statement

The pyramid and the testing trophy are both fine, and neither is doctrine. The shape you draw is a statement about where your bugs live and how much wall-clock you are willing to spend per commit. Copying someone else's shape imports their bug distribution, not yours.

| Stack | Shape we run | Why |
|---|---|---|
| Backend service owning a database | Pyramid with a **fat integration middle** | Most defects are wiring: auth, ownership, transactions, ORM filters, error mapping |
| Web frontend | **Trophy** — few unit, many component/integration, a few E2E | Rendering bugs are behavioural; pure logic is a thin slice of the code |
| Mobile | **Pyramid** — unit > widget > integration | Device and emulator runs are slow and flaky, so keep the top narrow |

Real numbers from our own repos, as illustration and nothing more:

| Suite | Size | Wall clock |
|---|---|---|
| Backend integration (real Postgres in containers) | ~1800 tests | ~10 min consolidated gate |
| Frontend unit (vitest, no browser, no server) | ~600 tests | ~6 s |
| E2E (Playwright, real stack) | ~700 tests | ~14 min |

Note the ratio of value to time: the 6-second suite runs on every save and catches typos in logic; the 10-minute suite is the one that actually blocks a bad merge. If your "fast" suite takes four minutes, people stop running it, and you have bought a slow suite with the fidelity of a fast one.

---

## 3. The unit-vs-integration position

We used to say "prefer unit tests over integration tests, they are cheaper to write and to run". That advice was right about authoring cost in 2025 and wrong about what a test is for. Here is the current position, stated as an evolution:

> Test at the highest layer that is still fast, deterministic and local. For an HTTP service that owns a database, that layer is the integration test: a real database in a container (one instance shared by the whole run), a real framework context, requests driven through the real HTTP layer with a real token. Unit tests with mocks are for pure logic: state machines, pricing, parsers, mappers, anything where a database adds nothing. Most backend bugs live in the wiring — auth, ownership checks, transaction boundaries, ORM filters, exception-to-status mapping — and a unit test with a mocked repository cannot see any of them. Two things changed the cost model: a shared container makes the second integration test cost seconds instead of a minute, and AI tools write test scaffolding for free. The expensive thing is no longer typing the test. It is trusting a green that asserted nothing.

Decision table — use it before you write a line:

| Code under test | Default layer | Why |
|---|---|---|
| Pure function / domain rule / state machine | Unit, no framework | Fast, exhaustive edge cases, no infra |
| Service that touches DB, security or transactions | Integration (real DB, real HTTP layer) | The bugs are in the wiring |
| Controller mapping only, no logic | Integration through the service, not a controller slice alone | A slice test cannot see authorization + service + ORM filter together |
| Outbound HTTP client | Unit with a stubbed transport (WireMock, MockWebServer, MSW) | Deterministic; the contract is asserted |
| UI component | Component test (Testing Library, widget test) | Behaviour through accessible queries |
| Cross-page user flow | E2E | Only layer that sees the real assembly |

Corollary on databases: an in-memory database is not "the real one when convenient". Use it only if your app has zero database-specific features, and write that decision down in the repo's `docs/testing.md`. The default is a real engine in a container.

---

## 4. What to test first

In order. Do not reorder this list because a coverage report told you to.

1. **The bug you just fixed.** The only test whose assertion is proven valuable — you watched it fail in production.
2. **Money, permissions and ownership paths.** Anything where being wrong costs cash or leaks another tenant's data. Test both directions: the owner succeeds, the stranger is refused. Ownership breach is 403, never 404 — a 404 leaks whether the resource exists.
3. **State machines.** Every legal transition, and at least one illegal one asserting the refusal with a machine-readable code.
4. **The happy path of your top three user flows, end to end.** One test each. Not twenty.
5. **Everything else**, as it changes.

Do **not** start with getters, DTO constructors, or a coverage percentage. A suite of 300 getter tests is a suite that has never failed for a good reason, and it teaches the team that green means nothing.

---

## 5. Day 1 / Week 1 — greenfield

| When | Do | Done means |
|---|---|---|
| Day 1, hour 1 | Pick the boring default runner for your stack (JUnit 5, vitest, `flutter_test`, `go test`, pytest). No custom harness. | `<test command>` runs and reports 0 tests |
| Day 1, hour 2 | Write **one smoke test that proves the harness**: assert something you know is true, then deliberately break it and watch it go red, then fix it. | You have seen the runner fail. "Prove the harness before you trust its verdict." |
| Day 1, hour 3 | Write the **single-test command** into the README and `docs/testing.md`, verbatim, copy-pasteable. | A teammate can run one test without asking |
| Day 1, hour 4 | Wire CI to run the suite on every push. Make it a required check on the default branch. | A red test blocks a merge |
| Day 2 | First real test: a domain rule at the unit layer. One scenario, given/when/then, named `should_X_when_Y`. | It fails when you invert the rule |
| Day 3-4 | First integration test: a real database in a container, one endpoint, asserting status plus one machine-readable field. | The second integration test costs seconds, not a minute |
| Day 5 | Ownership/permission probe: owner succeeds, other tenant gets 403. | Both directions asserted |
| Week 1, end | Write `docs/testing.md`: commands with labels, the layer table, the baseline counts and the date. Add the "bug -> test" rule to your agent instruction file. | Section 11 of this guide is satisfied |

Do not spend day 1 choosing between two assertion libraries. Pick the one your stack guide names and move.

---

## 6. Day 1 / Week 1 — legacy with zero tests

The failure mode here is the big-bang: a two-week "add tests" project that produces 400 shallow tests and no confidence. Do this instead.

| When | Do | Done means |
|---|---|---|
| Day 1, hour 1 | Get the runner to execute **anything**. Often this is the whole day in a ten-year-old repo. | One trivial test runs |
| Day 1, hour 2 | Find and document the **single-test command**. In multi-module builds it is usually module-scoped, and the bare form fails with "no tests found". | It is in `docs/testing.md` with the exact flags |
| Day 1, hour 3 | Run the whole suite (if one exists) on a **clean checkout** and record the **known-red baseline**: `"<test> fails on clean checkout — not your regression"`, with counts and the date. | Nobody wastes an afternoon on someone else's red |
| Day 1, hour 4 | Write a **characterization test** on the scariest path — the one everyone is afraid to touch. It asserts what the code does today, not what it should do. It is a net under the refactor, not a specification. (Michael Feathers, *Working Effectively with Legacy Code*.) | You can change that code and know if behaviour moved |
| Day 2 | Adopt the **bug -> test** rule immediately. Every fix from today ships the test that would have caught it. No exceptions, no backlog ticket. | The next fix has a test in the same commit |
| Day 3 | Characterize the second and third scariest paths. For output-heavy code (reports, serializers, generated files), use **approval / golden tests**: capture the current output to a file, assert future runs match it, review diffs by eye. | Refactors become verifiable |
| Day 4 | Turn on a **coverage ratchet on new code only** — never a repo-wide threshold, which is unachievable and will be turned off within a week. | A PR that adds untested code is flagged |
| Day 5 | Make CI a required check with the known-red baseline encoded (allowlist, or fix them). | Red means new |
| Week 1, end | `docs/testing.md` exists with commands, baseline, and the layer table. | Section 11 is satisfied |

Never delete a legacy test to make the build green. Quarantine it explicitly (Section 8) and file the ticket.

---

## 7. The rule that pays for itself

> **If you fix a bug, write the test that would have caught it.**

Every fix or feature ships test coverage at the layer where the bug lives. Any change to production code has a corresponding change in tests; if it does not, the tests were wrong or superficial.

The reasoning is narrow and worth stating: a regression test is the only test whose assertion has already been proven valuable. Every other test is a guess about what might break. This one is a recording of what *did* break, in production, with real consequences. It is also the only way a test suite gets denser where your code is actually fragile, instead of uniformly thin everywhere.

Two practical notes. Write the test **before** the fix and watch it fail — a regression test that has never been red is not a regression test, it is a hope. And put it at the layer that would have caught it: if the bug was a missing ownership check, a unit test with a mocked repository would have passed happily, so it belongs at the integration layer.

---

## 8. Test hygiene: FIRST, naming, and flakes

**FIRST properties** (Fast, Isolated, Repeatable, Self-validating, Timely) are a useful checklist, and *Isolated* is the one people actually break: a test that depends on another test's leftovers is a time bomb. Every test states its own preconditions.

**Naming.** `should_X_when_Y` and `x_isY_whenZ` are both fine — `illegalTransition_is409_withFromTo` reads perfectly. Pick one per repo and stop discussing it. What matters is that a failure line in CI tells you the scenario without opening the file.

**Test behaviour, not implementation.** Assert the result, not the internal calls. Asserting that a repository method was called tells you the code still calls it, not that the outcome is right — and it breaks on every refactor that changes nothing users can see.

**Flaky-test quarantine policy.** Never delete a flaky test silently, and never add a blanket retry. Policy: label it `quarantine`, exclude it from the blocking gate, open a ticket with a **two-week expiry**, and if nobody fixes it by then, it gets deleted deliberately with a written reason. Count quarantined tests weekly. A growing number is a signal about the system, not the suite.

**Mutation testing, if you want an honest coverage number.** Line coverage says the line ran; it says nothing about whether an assertion would notice if it changed. Mutation testing (PIT for the JVM, Stryker for JS/TS) mutates your code and reports how many mutants your suite kills. It is slow, so scope it to your critical package and run it weekly, not per commit. Optional — but if your team is arguing about a coverage target, this is the metric that ends the argument.

---

## 9. Working with an AI coding tool

An AI agent will write tests faster than you can read them, and its default failure mode is a test that runs a lot of code and asserts nothing. Adjust for that.

| Rule | Why |
|---|---|
| Demand **red-then-green**, with the red output pasted in the report | Several guards in our repos passed by matching nothing until someone checked |
| **Never let it weaken an assertion to make a test pass** | A weakened guard is a deleted guard |
| Require it to run the **single-test command it names** and paste the real output | "Tests pass" without output is a prediction, not a result |
| Require the **test count before and after** | A refactor that silently drops 12 tests still reports green |
| **Tell it the layer** (Section 3 table) | Left alone it defaults to mock-everything unit tests, which cannot see wiring bugs |
| Forbid `@Disabled`, `test.skip(true)`, `xit`, `.only`, and narrowing the run to hide a failure | These turn a red into a green without changing anything |

### Copy-paste prompt template

```
Write tests for <change>. Follow these rules exactly:
1. Layer: <unit | component | integration | e2e>. Do not mock what this layer is meant to exercise.
2. Write the test FIRST, run it, and paste the RED output verbatim.
3. Then make it pass and paste the GREEN output verbatim.
4. Name the single-test command you used and paste its exact invocation.
5. Report test counts before and after (N -> M).
6. Do not weaken or delete any existing assertion. If one blocks you, stop and tell me why.
7. Do not add @Disabled, skip(true), xit, .only, or narrow the run to a passing subset.
8. One scenario per test, named should_X_when_Y, asserting the result — not internal calls.
9. Assert failures by status code plus a machine-readable code, never by message text.
10. End with an honest "not covered" list.
```

### How to detect faked coverage

Run these before believing a green report. They take five seconds.

```sh
# assertions that assert nothing
grep -rnE 'assertTrue\(true\)|assertThat\(true\)\.isTrue\(\)|expect\(1\)\.toBe\(1\)|assert True$' .

# empty test bodies (JS/TS)
grep -rnE "(it|test)\(.*, *(async *)?\(\) *=> *\{ *\}\)" .

# disabled or narrowed tests
grep -rnE '@Disabled|@Ignore|\.only\(|\bxit\(|\bxdescribe\(|skip\(true|test\.skip\(|@pytest\.mark\.skip|t\.Skip\(' .

# a test file that nothing runs (check your runner's include patterns against reality)
```

Then count: how many assertions did the new tests add, and how many of them would fail if you inverted the production logic? If the answer is "none", you have coverage without confidence. A green number you cannot trust is worse than an honest gap.

---

## 10. Test-smell catalogue

| Smell | Why it hurts | Instead | Detection |
|---|---|---|---|
| 1. `verify()`-heavy tests | Asserts the code still calls a method, not that the result is right; breaks on every harmless refactor | Assert the returned value or the persisted state | `grep -rn 'verify(' --include='*Test.java' \| wc -l` vs assert count |
| 2. CSS class / XPath / arbitrary id selectors | Break on every styling change; match the wrong element silently | Role, label, text, then test id as a last resort | `grep -rnE "locator\('(\.\|#\|//)" e2e/ src/` |
| 3. `sleep` / `waitForTimeout` | Slow when it works, flaky when it does not | Condition waits and auto-retrying assertions | `grep -rnE 'waitForTimeout\|Thread\.sleep\|time\.sleep' .` |
| 4. Shared mutable fixtures / order-dependent tests | One class leaves state, another fails. Our scar: 106 red across 23 classes from one shared schema plus a framework context-cache eviction — every class green when run alone | Every test states its own preconditions; isolate per-context state | Run the suite in reverse or randomized order |
| 5. `test.only` / `.fixme` committed | The suite silently runs one test and reports green | Fail the run when `only` is present in CI | `grep -rnE '\.only\(\|\.fixme\(' .` |
| 6. Asserting on message text or i18n keys | Copy edits break the suite; the assertion never proved the behaviour | Assert status plus a stable machine-readable code | `grep -rn 'getMessage()\|toHaveText(' .` |
| 7. Skips that hide an environment failure as green | Our scar: a rate-limit `429` from an exhausted budget was read as "service unavailable" and skipped an entire feature surface for a month, green, asserting nothing | A skip must state its reason; in a lane where the dependency is guaranteed, a skip is a FAILURE. Silently-missing must not read as green | Count skips per run and alert on growth |
| 8. A spec file no project claims | Runs zero tests, reports green, indistinguishable from passing. It happened to us: a 5-test file sat silent after it landed | A coverage-guard test that fails when a spec file matches no project, and when a project matches no file | Compare file count to the runner's collected count |
| 9. Multiple unrelated asserts in one test | You only see the first failure; the test name cannot describe what it checks. Many asserts is a design smell | One scenario per test, given/when/then | Assert count per test method |
| 10. Test constants imported from production code | The test passes even when the constant is wrong, because both sides changed together | Assert on literals written in the test | `grep -rn 'import .*Constants' --include='*Test*'` |
| 11. Coverage-only tests written by an AI | Exercise lines, assert nothing meaningful; the number goes up and the safety net does not | Require an assertion that fails when the logic is inverted | Section 9 greps; mutation testing |
| 12. Seeding data through repository writes instead of the API | The ownership and tenant wiring you care about is never exercised | Seed through the public API with a real token | `grep -rn 'repository.save' --include='*IntegrationTest*'` |

---

## 11. What a repo's `docs/testing.md` must contain

This file is the difference between an agent (or a new hire) that trusts the suite and one that guesses. Five required parts:

1. **Commands with honesty labels.** Every command carries one: `[verified]` ran clean · `[FAILED]` ran and failed · `[verified in CI]` fails locally for environment reasons, green in CI (name the workflow) · `[unverified: <reason>]`. Mirror the CI invocation exactly; never invent flags.
2. **The single-test command is mandatory.** Not the suite command. The one that runs one test. In multi-module builds, module-scoped — the bare form typically fails with "no tests found" in sibling modules, and that error reads like a broken repo to anyone who has not been told.
3. **The known-red baseline**, with counts and a date: `"<test> fails on a clean checkout — not your regression"`. Update the counts whenever the suite moves. Then the hard part: **do not turn "ignore one known red" into guidance.** A checklist that teaches people to skip a red is how a real one hides. Baselines are a dated fact, not a policy.
4. **Caveats that make the gate honest.** One afternoon our consolidated gate reported `BUILD SUCCESSFUL in 1m12s`. Two modules were `UP-TO-DATE` — never executed, because the build tool judged their inputs unchanged. The same command with the clean-test task took **10m6s** and actually ran. **A gate that finishes suspiciously fast has not passed, it has abstained.** Read the task list, never just the exit code. Write your stack's version of that caveat down.
5. **Measured baseline counts with a date**, per suite, so anyone can tell a real regression from a suite that quietly stopped collecting tests.

```
## Suites, measured <date>
| Suite            | Expectation on a clean tree | Count            |
|------------------|-----------------------------|------------------|
| unit             | 0 red                       | 595 / 25 files   |
| integration      | 0 red                       | 1815 / 267 classes |
| e2e (smoke)      | 0 red                       | 42               |
```

---

## 12. Same idea in Node / Python / Go

| | Node / TypeScript | Python | Go |
|---|---|---|---|
| Runner | `vitest` or `jest` | `pytest` | `go test` |
| Whole suite | `npx vitest run` | `pytest` | `go test ./...` |
| Single test | `npx vitest run path/to/f.test.ts -t 'name'` | `pytest path/to/test_f.py::test_name` | `go test ./pkg -run '^TestName$'` |
| Container DB | `testcontainers` (npm) | `testcontainers` (pypi) | `testcontainers-go` |
| HTTP-level test | `supertest` | `httpx` + ASGI transport, or `TestClient` | `net/http/httptest` |
| Coverage | `vitest run --coverage` | `pytest --cov` | `go test -cover ./...` |
| Mutation testing | `stryker` | `mutmut` | `go-mutesting` |

The layer table in Section 3 does not change with the language. Only the spelling does.

---

## Sources & further reading

- Michael Feathers, *Working Effectively with Legacy Code* — characterization tests, seams, breaking dependencies.
- Kent Beck, *Test-Driven Development: By Example* — red-green-refactor, and why the red matters.
- Martin Fowler, "Test Pyramid" and "Unit Test" — https://martinfowler.com/bliki/TestPyramid.html
- Kent C. Dodds, "The Testing Trophy" and "Testing Implementation Details" — https://kentcdodds.com/blog/the-testing-trophy-and-testing-classifications
- Testcontainers documentation — https://testcontainers.com/
- PIT mutation testing — https://pitest.org/ · Stryker Mutator — https://stryker-mutator.io/
- Google Testing Blog, "Test Sizes" and the flaky-test posts — https://testing.googleblog.com/

## Related

- [backend-testing-guide.md](./backend-testing-guide.md) — integration-first with a real database, ownership probes, failure assertions
- [frontend-testing-guide.md](./frontend-testing-guide.md) — the trophy in practice, component tests, the fast loop's scope boundary
- [mobile-testing-guide.md](./mobile-testing-guide.md) — unit, widget, golden and device-integration layers
- [e2e-testing-guide.md](./e2e-testing-guide.md) — page objects, test data, teardown, and the production guard
- [enforcement/README.md](./enforcement/README.md) — turning these recommendations into instructions, hooks and CI gates
- [../../skills/test-engineer/SKILL.md](../../skills/test-engineer/SKILL.md) — the agent skill that applies all of the above

_Last reviewed: 2026-09-07._
