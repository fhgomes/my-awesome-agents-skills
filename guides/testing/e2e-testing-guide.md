# E2E Testing Guide

**Best used when:** you are adding a browser end-to-end suite to a web product, or you inherited one that is slow, flaky, or pointed at something it should never touch.
**Read before:** writing your first `.spec.ts`, wiring `playwright.config.ts`, or letting an AI agent "add E2E coverage".
**See also:** [testing-from-zero.md](./testing-from-zero.md) · [frontend-testing-guide.md](./frontend-testing-guide.md) · [backend-testing-guide.md](./backend-testing-guide.md) · [enforcement/README.md](./enforcement/README.md)

Playwright is the reference tool here; the architecture, selector rules, data markers and guards transfer to Cypress or WebdriverIO unchanged, only the API names differ. E2E is the only layer that sees the real assembly — routing, session, the deployed bundle, the gateway, the mail server. It is also the only layer that can do damage, which is why half of this guide is about refusing to run.

---
## 1. Where the suite lives

| Dimension | `e2e/` folder in the product repo | Separate E2E repo |
|---|---|---|
| Feature and spec in one PR | Yes, the reviewer sees both | No — two PRs, easy to forget the second |
| Version lockstep | Automatic | Manual; a stale spec repo lies about a shipped app |
| Playwright in the product bundle | Present in `devDependencies` | Absent — the product ships no test runtime |
| Product pre-commit hooks on spec edits | Fire on every spec edit | Do not fire; spec iteration stays cheap |
| Several deployables, or a post-deploy run from an ops box | Awkward: which repo owns it? | Natural: clone one small repo and run |

**Recommendation.** One product, one deployable: `e2e/` inside the product repo. Several deployables sharing journeys, or a suite that must run from an ops box after each deploy: give it its own repo. We run both, and the separation exists for three stated reasons — decouple the test runtime from the production bundle, run a full regression before every task close, and edit a spec without triggering the product's pre-commit hooks. Either way the layout is the same: `src/tests/` (one describe per feature, one test per acceptance bullet), `src/pages/`, `src/utils/`, `src/fixtures/`, plus `global-setup.ts` and `global-teardown.ts`.

## 2. Architecture

```
Tests (*.spec.ts) -> Page Objects (src/pages/) MANDATORY -> Helpers (src/utils/) -> Fixtures (src/fixtures/)
```

**Tests only interact through Page Objects, never the DOM.** A spec containing `page.locator(...)` is a spec that gets rewritten by hand the next time a designer renames a class. The Page Object knows what the page looks like; the test knows what the user is trying to do.

## 3. Page Object rules

- One class per page (or per stable region) in `src/pages/`, re-exported from `src/pages/index.ts`.
- Locators are typed `readonly Locator` properties, built in the constructor.
- Every class exposes `goto()`, `expectPageLoaded()` and action methods named for user intent.
- **150 lines maximum per class.** Past that, split by region — a 400-line Page Object is a second application.
- No assertions on internals: `expectPageLoaded()` asserts the one thing that proves the page rendered, the rest belongs in the test.

```typescript
// src/pages/ApplyPage.ts
import { expect, type Locator, type Page } from '@playwright/test';

export class ApplyPage {
  readonly heading: Locator;
  readonly emailInput: Locator;
  readonly submitButton: Locator;

  constructor(private readonly page: Page) {
    this.heading = page.getByRole('heading', { name: 'Apply' });
    this.emailInput = page.getByLabel('Email');
    this.submitButton = page.getByRole('button', { name: 'Submit application' });
  }
  /** Relative path on purpose — the app may be served on a subpath (section 10). */
  async goto(): Promise<void> { await this.page.goto('apply'); await this.expectPageLoaded(); }
  async expectPageLoaded(): Promise<void> { await expect(this.heading).toBeVisible(); }
  async applyWith(email: string): Promise<void> {
    await this.emailInput.fill(email);
    await this.submitButton.click();
  }
}

// src/fixtures/pages.ts — Page Objects arrive as fixtures, not as `new` calls in specs
export const test = base.extend<{ applyPage: ApplyPage }>({
  applyPage: async ({ page }, use) => { await use(new ApplyPage(page)); },
});
```

## 4. Selector hierarchy

| Priority | Locator | Use for |
|---|---|---|
| 1 | `page.getByRole('button', { name: 'Submit' })` | Anything with a semantic role — buttons, links, headings, dialogs |
| 2 | `page.getByLabel('Email')` | Form fields |
| 3 | `page.getByText('Confirm')` | Static copy, when nothing above fits |
| 4 | `page.getByTestId('app-nav')` | Last resort: containers and regions with no accessible identity |
| — | `.MuiButton-root`, `#submit-btn`, `//button[contains(@class,'submit')]` | **Never.** CSS classes, arbitrary ids and XPath break on every restyle |

The first three double as accessibility pressure: if you cannot address a control by role or label, neither can a screen reader.

**The scar.** A responsive sweep asserted "the sidebar is not visible below the `md` breakpoint" using a loose `nav[aria-label]` locator plus `.first()`. A component library's pagination renders `<nav aria-label="pagination navigation">` inside `<main>`, earlier in the document than the portalled nav panel — so `.first()` picked the pager and reported it as a sidebar defect on four route names. Two rules came out of it: scope structural assertions to a `data-testid` you control, never to an attribute a dependency also emits; and **assert presence before asserting not-visible**, because a locator matching nothing satisfies "not visible" for the wrong reason and reports green forever.

## 5. Fixtures and test data

Every identifier a test persists goes through `src/fixtures/test-data.ts`. Never hand-roll an email, name or slug in a spec — an unmarked row is a row teardown cannot find.

```typescript
// src/fixtures/test-data.ts
export const E2E_EMAIL_DOMAIN = 'e2e.example.test';   // reserved for the suite
export const E2E_NAME_PREFIX = '[E2E] ';

export const uniqueSuffix = (): string =>
  `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`;

/** e2e-apply-l3k9x-8f2a1@e2e.example.test — the local part always starts `e2e-`. */
export const e2eEmail = (tag = ''): string =>
  `e2e-${tag ? `${tag}-` : ''}${uniqueSuffix()}@${E2E_EMAIL_DOMAIN}`;
export function e2eName(base: string): string { return `${E2E_NAME_PREFIX}${base}`; }
export function e2eSlug(): string { return `e2e-${uniqueSuffix()}`; }
```

**The domain is the marker.** Reserve one DNS name for the suite and teach the product to treat it as such: teardown, the mail guard and any audit then share one predicate. Seeded personas deliberately do *not* match the `e2e-` prefix, so they survive every sweep. **Marker columns cover rows with no name.** Some tables hold nothing human-identifiable — a calendar window, a scheduling exception, a rate-limit bucket. Give those an `e2e_marker` column, populated only through a development-gated optional create field. Real rows keep it `NULL`, so `DELETE ... WHERE e2e_marker IS NOT NULL` is crash-safe and cannot touch production data even in principle.

> **Never sweep a table by tenant plus time range.** One of our teardowns did exactly that — "delete everything in this tenant created in the last hour" — and deleted a real user's rows. A time window is a guess about who created a row; a marker is a fact.

## 6. Teardown

`global-teardown.ts` runs after the suite and deletes by marker. Four non-negotiable properties:

1. **Marker-based, not memory-based.** Do not accumulate "what I created" in a variable — a spec that crashes mid-run leaks every row it made. Query the markers.
2. **Refuses non-local databases.** The host must be loopback *and* the cluster must positively identify itself as a development database. `localhost:5432` is whatever is listening on that port, which an SSH tunnel decides, not your config file.
3. **Protects seeds explicitly**, by id or email, matched before any delete runs, and **classifies every table**: a `DELETIONS` list and a `NOT_SWEPT` list, with a reason per table. One audit against the live schema found thousands of orphaned notification rows in tables the teardown had never known about. A new table belongs in one of the two lists — there is no third option.
4. **Ships a `DRY_RUN=true` mode** that prints per-table match counts and deletes nothing — the only safe way to review a teardown change.

## 7. Auth via API only

Never drive a login form, and never click a mock-login button in the UI.

- Expose `POST /api/auth/test-login` in the app, behind a flag that is off by default and impossible to enable in the production profile.
- Personas by role and tenant: `ADMIN`, `USER_A`, `USER_B`, `OTHER_TENANT_ADMIN`. The last one exists so ownership tests can assert the 403 direction — ownership breach is 403, never 404, because a 404 leaks whether the resource exists (see [backend-testing-guide.md](./backend-testing-guide.md)).
- Cache the token per worker; plant it with `page.addInitScript` **before the first navigation**, together with the UI language.

```typescript
// src/fixtures/auth.ts
export type Persona = 'ADMIN' | 'USER_A' | 'USER_B' | 'OTHER_TENANT_ADMIN';
const TOKEN_KEY = 'app_token';
const LNG_KEY = 'app_lng';
const tokenCache = new Map<string, string>();

export async function testLogin(request: APIRequestContext, who: Persona): Promise<string> {
  const cached = tokenCache.get(who);
  if (cached) return cached;
  const send = () => request.post('api/auth/test-login', { data: { persona: who } });
  // Retry on 429: a per-IP limiter often sits in front of the app, and parallel
  // suites can momentarily exhaust the shared bucket. Environmental, not a failure.
  let res = await send();
  for (let attempt = 0; res.status() === 429 && attempt < 4; attempt++) {
    const retryAfterMs = Number(res.headers()['retry-after'] ?? 0) * 1000;
    await new Promise((r) => setTimeout(r, Math.max(retryAfterMs, 1000 * (attempt + 1))));
    res = await send();
  }
  expect(res.status(), `test-login for ${who} (is test-login enabled on this stack?)`).toBe(200);
  const token = (await res.json()).accessToken as string;
  tokenCache.set(who, token);
  return token;
}
export async function loginAs(page: Page, request: APIRequestContext, who: Persona): Promise<void> {
  const token = await testLogin(request, who);
  await page.addInitScript(([k, v, lng]) => {
    window.localStorage.setItem(k, v);
    window.localStorage.setItem(lng, 'en');   // pin the language for text assertions
  }, [TOKEN_KEY, token, LNG_KEY] as const);
}
/** Unique X-Forwarded-For so rate-limit suites do not poison each other's buckets. */
export const uniqueIp = (): string =>
  `10.${[0, 0, 0].map(() => 1 + Math.floor(Math.random() * 253)).join('.')}`;
```

**Why not `storageState`?** It is Playwright's standard way to reuse a session and a good default for a single-origin app on a root path. We plant the token instead because the same init script has to pin the UI language, and because a saved state file bakes in an origin — on a subpath deploy that origin drifts from `baseURL` the first time someone changes the proxy. If neither applies to you, use `storageState`.

## 8. The prod guard

> In one of our projects a Playwright run was pointed at production by a default env value; it created real rows and sent roughly ten real booking notifications to real people before anyone noticed. The "fix" was to point it back at DEV — a convention, not a guarantee. The guard that exists now refuses to run.

| # | Check | Property |
|---|---|---|
| a | String gate on the **resolved** base URL, inside `baseUrl()` | `BASE_URL`, `TEST_ENV` and any future path funnel through one function; the throw happens at config load, before a single test is collected |
| b | Compare parsed **hostname**, exact or subdomain | Substring matching is how a guard gets deleted |
| c | Unparseable URL counts as production | Fail closed |
| d | No override flag | Enabling production is a reviewed edit to `PRODUCTION_HOSTS` |
| e | Destination check in `global-setup`, redirects followed **manually** | A development hostname can 302 into production |

```typescript
// src/fixtures/prod-guard.ts + src/fixtures/env.ts
export const PRODUCTION_HOSTS: readonly string[] = ['app.example.com'];
const ENV_CONFIG = { dev: 'https://dev.example.com/app/', local: 'http://localhost:8080/' } as const;

const hostnameOf = (t: string): string | null => {
  try { return new URL(t).hostname.toLowerCase(); } catch { return null; }
};

/**
 * Fails CLOSED: an unparseable value counts as production — that is a
 * misconfiguration, and the safe answer to "is this real people's inbox?" is "yes".
 * Hostname, not substring: `url.includes('example.com')` matches `dev.example.com`
 * too, would refuse every DEV run, and is how a safety guard gets deleted.
 */
export function isProductionTarget(target: string): boolean {
  const host = hostnameOf(target);
  if (host === null) return true;
  return PRODUCTION_HOSTS.some((p) => host === p || host.endsWith(`.${p}`));
}
export function assertNotProductionTarget(t: string): void {
  if (isProductionTarget(t)) throw new ProductionTargetRefusedError(refusal(t));
}
/** Called from playwright.config.ts, so a production target aborts at config load. */
export function baseUrl(): string {
  const env = (process.env.TEST_ENV || 'dev') as keyof typeof ENV_CONFIG;
  const raw = process.env.BASE_URL || ENV_CONFIG[env] || ENV_CONFIG.dev;
  const resolved = raw.endsWith('/') ? raw : `${raw}/`;   // baseURL must end with /
  assertNotProductionTarget(resolved);
  return resolved;
}
```

**The hole the string gate does not close.** A non-production hostname can *deliver you* to production. One of our development vhosts was deliberately repointed and started answering `302 -> https://app.example.com/app/`. By string it is not a production host, so the cheap gate passes it — and then Playwright, like every HTTP client, follows the redirect into the live site. That was the default target, not an exotic one. So `global-setup.ts` resolves the destination before anything runs.

Follow the redirects **manually**. A plain `redirect: 'follow'` would learn the destination by *requesting* it — the guard itself would hit production before deciding production is forbidden. By hand, a `Location` pointing at a production host is refused on the spot and that request is never sent. Fail closed on DNS failure, timeout and redirect loop: an unreachable target is not a safe target, and a guard that degrades to "allow" on error is the same defect one layer down.

```typescript
export async function assertTargetDoesNotReachProduction(start: string): Promise<string> {
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), 5_000);      // total budget, all hops
  try {
    let url = start;
    for (let hop = 0; hop < 10; hop++) {                    // a longer chain is a loop
      const res = await fetch(url, { method: 'HEAD', redirect: 'manual', signal: ctl.signal });
      const location = res.headers.get('location');
      if (![301, 302, 303, 307, 308].includes(res.status) || !location) return url;
      url = new URL(location, url).toString();
      if (isProductionTarget(url)) throw new ProductionTargetRefusedError(refusal(url));
    }
    throw new TargetResolutionFailedError(`redirect loop resolving ${start}`);
  } catch (err) {
    if (err instanceof ProductionTargetRefusedError) throw err;
    throw new TargetResolutionFailedError(`could not resolve ${start}: ${String(err)}`);
  } finally { clearTimeout(timer); }
}
```

The refusal must teach, or someone will delete it:

```
  ┌───────────────────────────────────────────────────────────────────┐
  │  E2E RUN REFUSED — the target is PRODUCTION                       │
  └───────────────────────────────────────────────────────────────────┘
  target: https://app.example.com/app/   host: app.example.com
  known production hosts: app.example.com

  DELIBERATE, not a misconfiguration to work around: a run against this address
  once delivered ~10 [E2E] notifications to real people. The suite creates and
  deletes real rows and sends real mail; it may never touch production.
  There is NO override flag. Point it at a development target instead:
      TEST_ENV=dev (default)   |   TEST_ENV=local   http://localhost:8080/
  A genuine production check is a reviewed change to PRODUCTION_HOSTS — not an
  env var set at 2am while chasing a deploy.
```

## 9. SMTP and notification guards

The prod guard lives in the suite; the suite is not the only thing that can send mail from a mis-targeted run. The second guard lives **in the application**:

- The mail service refuses any message whose subject carries `[E2E] `, or whose recipient domain is the test domain, when the configured SMTP host is not a local sink (mailpit, MailHog, loopback) — **in every environment, including production**.
- Refusals are logged as status `REFUSED`, never `FAILED`, with a reason prefixed `test_traffic_refused:`. `FAILED` sends people hunting an SMTP outage that does not exist.
- Non-production environments additionally refuse to **boot** against a real mail host. A startup guard is louder than a runtime one and cannot be forgotten.
- Same pattern for push, SMS and outbound webhooks — anything that reaches a human.

> If an e2e mail assertion goes quiet, look for `REFUSED` rows before suspecting the app: it means the target stack is pointed at a real SMTP server.

One gate run put 496 messages into the local mail sink. Against a mis-targeted run those 496 are real inboxes. That number is the whole argument.

## 10. Relative paths and the subpath trap

If the app is (or ever might be) served from a subpath such as `/app/`, use relative paths everywhere. `baseURL` must end with `/`, or the last segment is discarded when a relative URL is resolved.

```typescript
await page.goto('apply');              // yes
await request.get('actuator/health');  // yes
await page.goto('/apply');             // no — a leading slash escapes the subpath
await page.goto('https://dev.example.com/app/apply'); // no — hardcoded target
```

**The SPA-fallback trap.** A bundle built with a base of `/app/` asks for its assets under that prefix. Point the suite at the container root instead of the proxy and those requests hit the SPA fallback: `200 text/html` where the browser wanted JavaScript. The page renders blank, every UI test fails on a missing heading, and nothing in the output says "wrong base path". **A `200` is not proof the target is right — check `content-type`.**

## 11. Config hygiene

```typescript
export default defineConfig({
  testDir: './src/tests',
  forbidOnly: !!process.env.CI,        // a committed test.only silently shrinks the suite
  retries: process.env.CI ? 1 : 0,     // one retry, CI only; locally a flake must be visible
  workers: process.env.CI ? 1 : 2,     // size to the box, not to the laptop
  use: {
    baseURL: baseUrl(),                // throws here if the target is production
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    locale: 'en-US',                   // pin the UI language for text assertions
  },
  // Explicit testMatch per project — never let testDir glob a spec in (see below):
  projects: [{ name: 'smoke', testMatch: /\bsmoke\.spec\.ts/ }, /* … */],
});
```

- **No `test.only`, no `.fixme`.** `forbidOnly` in CI turns a leaked `.only` into a red build instead of a suite that quietly ran one test.
- **Explicit `testMatch` per project, plus a spec-coverage guard.** With `testDir` globbing, nothing tells you a spec is unregistered. With explicit `testMatch`, an unclaimed `.spec.ts` runs **zero** tests, reports nothing, leaves the total unchanged — indistinguishable from passing. It happened: a five-test spec sat silent after it landed. Write a guard spec that fails naming any unclaimed file, and the inverse (a project whose `testMatch` claims no file that exists). It needs no app, no browser and no rows.
- **Never a bare `npx playwright test`** when a project cannot run on the host. One bare run reported **372 failures** on a tree whose real count was 3, because it included a WebKit project the machine cannot launch. Name your projects, or filter them out.
- **`expect` auto-retry over `waitForTimeout`.** `await expect(locator).toBeVisible()` polls; a sleep is a guess that gets longer every time someone is in a hurry. Use `networkidle` sparingly — an app with polling or a websocket never goes idle.
- Tag a cheap subset `@smoke` and select it with `--grep @smoke`; shard the full suite with `--shard=1/4`. Visual assertions use `toHaveScreenshot` with `mask:` over clocks, avatars and CDN images; accessibility uses `@axe-core/playwright` in one spec per layout, not per route.

## 12. Environment-conditional skips vs flake

A skip is a statement, not noise, and it always carries its reason string.

| Skip | Verdict | Why |
|---|---|---|
| `test.skip(true, 'billing flag is off on this stack')` | Expected | The off-state assertion (403 `feature_disabled`, no nav entry) is what actually ran |
| `test.skip(!endpointPresent, 'endpoint absent on this build')` | Expected | Older deployable, documented |
| `test.skip(!backendUp, 'Backend unavailable')` | Expected locally, **never in CI** | See section 14 |
| A `429` read as "service unavailable" | **Defect** | See below |
| Any skip with no reason string | **Defect** | You cannot audit what a run declined to judge |

**The skip that was a defect.** Every AI suite gated itself with `aiUnavailable(status)` — true for `0`, `429` and `5xx` — and turned that into `test.skip`. But `429` is also what the monthly token cap returns. A stack that had spent its budget reported the entire AI surface as *skipped*, i.e. green, having asserted nothing, for about a month. Measured afterwards: the stack had burned twice its cap, and one full run with the cap raised made 124 real model calls that had all been silently skipping.

- A skip condition must distinguish "this feature is off here" from "this call failed" — different statuses, different verdicts. And **in a lane where the dependency is guaranteed, a skip is a FAILURE**: in the fake lane below the skip helpers fail loudly instead of skipping. Silently-missing must not read as green.
- Assertions deliberately deferred to another lane are **reported**, not skipped: emit a Playwright annotation plus a stdout line, so a run can state exactly how many judgements it did not make.
- **Genuine flake: none identified.** A failure without a skip reason is a regression — or the stack is down — not noise to retry away.

## 13. Fake and real lanes for external services

Anything metered or non-deterministic — an LLM, a payment provider, an SMS gateway — gets two lanes.

| | Fake lane (default) | Real lane (opt-in) |
|---|---|---|
| Enabled by | Default in the development profile | `REAL_LLM=1` / `REAL_PAYMENTS=1` |
| Determinism | Answers are pure functions of the input | None — the same prompt returns the draft verbatim about one run in three |
| Cost | Zero | Real money: thousands of calls per suite |
| Skips allowed | **No** — a skip here is a defect | Yes; budget and proxy really are environment conditions |
| Production | The fake **refuses to boot** under the production profile, pinned by a test | Never runs against production |

Put the fake **below** the recording seam, so everything above it still runs for real: prompt assembly, guards, budget reserve and reconcile, usage rows. The real lane must run before promoting a prompt, model or provider change, and you check the spend ledger **first** — a green real-lane run only means something if there was headroom. **Guard every spending call, not most of them:** a test that guards its second model call and not its first fails on an exhausted budget with an assertion message that reads like a contract violation.

## 14. The backend-unavailable skip

```typescript
const available = await backendAvailable(request);   // GET actuator/health, short timeout
test.skip(!available, 'Backend unavailable');
```

A local-development convenience so a developer with a stopped stack gets one readable message instead of forty timeouts. **It must not be reachable in CI** — there the stack is a precondition, and if it is down the run failed. Gate it on `!process.env.CI`, or the day the stack fails to start you get a green build that ran nothing.

## 15. Mobile projects

- Declare a **few named device projects**, not a phone mirror of every desktop project: one structural sweep over every route, plus one project per top flow. Mirroring everything doubles the project count and blows the suite's wall-clock budget on a shared CI box.
- The device supplies the engine, `isMobile`, `hasTouch` and the user agent; each spec's own `test.use({ viewport })` pins the geometry its assertions were written against.
- WebKit is the only engine that ships on iOS, so one WebKit project is not optional — and on many Linux hosts it needs the **official Playwright container**, because `playwright install-deps` targets one Ubuntu release and asks for libraries a newer one does not carry. Run natively, it produces ~50 failures that read like product defects.
- Use **soft assertions** per route so one run reports every problem a route has, and put the route and the width in the test title (`admin /admin/outcomes @ 320px`) — a failure you can read without opening the trace is worth several you cannot.
- A route can be measured, clean and empty — a feed with no items renders nothing to overflow. **Read a green sweep as "measured and clean", never as "covered".** Never weaken a sweep assertion to make a route pass; record the known-red instead. A green number you cannot trust is worse than an honest gap.

## 16. Running post-deploy

The one case where a non-development host is allowed is a **separate, read-only smoke suite** run from an ops box after each deploy.

| Spec | Asserts |
|---|---|
| `health.spec.ts` | The app answers, and `content-type` is what the browser needs |
| `homepage.spec.ts` | Structure, nav, hero, footer, plus a language guard (no strings from the other locale) |
| `top-flows.spec.ts` | The three flows whose breakage would be an incident, read-only |
| `visual.spec.ts` | Screenshots: desktop, mobile, dark mode |

Non-negotiable: it creates nothing, it logs in as nobody or as a read-only account, it sends no mail, and it lives in its own project or repo. The full suite keeps its `PRODUCTION_HOSTS` refusal — do not "reuse" the smoke suite's permission by widening the guard.

## 17. Day 1 and Week 1

**New product, no E2E yet**

| When | Do |
|---|---|
| Day 1, first hour | `npm init playwright@latest`; write `prod-guard.ts` and `baseUrl()` **before the first spec**. Guards are cheap now and political later |
| Day 1 | One smoke spec: `goto('')`, assert the main heading, run it — prove the harness before you trust its verdict. Then `test-login` behind a flag, `auth.ts`, and a Page Object for login plus one real flow |
| Day 2 | `test-data.ts` markers and `global-teardown.ts` — on day two, not on the day you have 300 orphan rows |
| Week 1 | Three flows as specs (one describe per feature, one test per acceptance bullet); `forbidOnly` in CI, trace on first retry, an `@smoke` tag, and the written rule that every `feat`/`fix` touching UI or an endpoint ships a spec ([enforcement/README.md](./enforcement/README.md)) |

**Existing product, no E2E**

| When | Do |
|---|---|
| Day 1 | Prod guard first, again — a legacy product is exactly where a stale env default is waiting |
| Day 1 | Find a target you are allowed to break, and resolve where it actually lands (`curl -I`) before pointing anything at it. Then one spec: log in through the API, land on the main screen, assert one heading. If it will not go green, the arrangement is wrong, not the product |
| Day 2 | Record the baseline in `docs/testing.md`: suite, expected result on a clean checkout, count, date. A known-red nobody wrote down gets blamed on the next person |
| Week 1 | Page Objects for login plus the flow that generates the most support tickets; markers and teardown before the suite has written enough rows to matter; the app-side mail refusal in the same week; CI on the `@smoke` subset only — a 40-minute suite nobody can finish gets disabled, and then you have nothing |

---

## Sources & further reading

- Playwright — Page Object Model: https://playwright.dev/docs/pom · Locators and the recommended priority: https://playwright.dev/docs/locators
- Playwright — Test fixtures (`test.extend`): https://playwright.dev/docs/test-fixtures · Authentication and `storageState`: https://playwright.dev/docs/auth
- Playwright — Configuration (`forbidOnly`, `retries`, `workers`, `trace`): https://playwright.dev/docs/test-configuration · Sharding and CI: https://playwright.dev/docs/test-sharding
- Playwright — Visual comparisons: https://playwright.dev/docs/test-snapshots (the `mask` option is on `toHaveScreenshot`: https://playwright.dev/docs/api/class-pageassertions) · Accessibility: https://playwright.dev/docs/accessibility-testing
- Cypress, "Best Practices" — the same selector and waiting rules in a different API: https://docs.cypress.io/app/core-concepts/best-practices. On Cucumber/Gherkin over an E2E suite: adopt it only when non-developers actually write the scenarios, otherwise it is a second parser between you and the failure message.

## Related

- [testing-from-zero.md](./testing-from-zero.md) — layers, the first-week plan, the test-smell catalogue
- [frontend-testing-guide.md](./frontend-testing-guide.md) — what stays in the fast unit loop instead of coming here
- [backend-testing-guide.md](./backend-testing-guide.md) — ownership breach is 403, never 404, and the integration layer behind these flows
- [enforcement/README.md](./enforcement/README.md) — turning these recommendations into instruction files, hooks and CI gates

_Last reviewed: 2026-09-07._
