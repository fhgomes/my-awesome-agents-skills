# Frontend Testing Guide

**Best used when:** you own a React/TypeScript app built with Vite and it has no test runner at all, or it has one and nobody trusts the green.
**Read before:** installing a test library, writing the first `.test.ts`, or asking an AI agent to "add frontend tests".
**See also:** [testing-from-zero.md](./testing-from-zero.md) · [e2e-testing-guide.md](./e2e-testing-guide.md) · [enforcement/README.md](./enforcement/README.md)

Primary stack here is React + TypeScript + Vite + vitest + Testing Library, with Playwright next door. The last section maps the same ideas onto Vue, Svelte, Angular and plain Node.

---

## 1. Position: the trophy, and where its floor is

Frontend bugs do not live in functions. They live in what the user can reach: a disabled button that should be enabled, a form that submits the wrong body, an error state nobody renders. So the shape is a trophy — a thin base of unit tests, a fat middle of component tests, a few E2E specs — not a pyramid.

| Layer | Volume | What it buys |
|---|---|---|
| Unit (pure functions) | Small and sharp | Edge cases you would never click through: a 249-entry country list, a 70-year bound, a version gate |
| Component (Testing Library) | The bulk | Behaviour a user can describe: "an invalid postcode shows the error and keeps submit disabled" |
| E2E (Playwright) | Few, high-value | Real assembly: routing, session, layout, third parties |

Illustrative numbers from one of our projects: ~600 vitest tests running in ~6 s, ~700 Playwright tests running in ~14 min. The 6 s is the whole point. The moment the fast loop needs a server it becomes a second slow suite and people stop running it.

### The scope boundary

Write this table into your repo's testing doc. It is the part that decays if left implicit.

| Belongs in `npm test` (vitest) | Belongs in Playwright (`e2e/`) |
|---|---|
| Pure functions: formatting, validation, mapping, guards | Anything needing a real server, DB or session |
| API-client **request shape**, with the transport mocked | Whether the server **accepts** that request |
| Storage/blob parsing and version gates | Storage in a real browser (quota, private mode) |
| Component behaviour in jsdom: states, events, a11y roles | Rendering across routes, navigation, mobile layout |

A test that wants a live backend does not belong in the fast loop. That boundary is the only thing keeping it fast.

---

## 2. Toolchain

| Piece | Choice | Note |
|---|---|---|
| Runner + coverage | `vitest`, `@vitest/coverage-v8` | Same transform pipeline as Vite; v8 is the default provider |
| DOM | `jsdom` | Install it when the **first** component test needs it, not before |
| Component tests | `@testing-library/react`, `@testing-library/jest-dom`, `@testing-library/user-event` v14 | Semantic queries; `await user.click(...)`, not `fireEvent` |
| Network | `msw` v2, or an adapter override | Section 6 |

```bash
npm i -D vitest @vitest/coverage-v8
# only when the first component test arrives:
npm i -D jsdom @testing-library/react @testing-library/jest-dom @testing-library/user-event
```

Verified against https://vitest.dev/guide/coverage and https://testing-library.com/docs/queries/about/ on 2026-09-07.

**Scripts.** `"test": "vitest run"` and `"test:watch": "vitest"`. `vitest run` is the CI-safe, non-watching form; a bare `vitest` in CI hangs.

**Keep `vitest.config.ts` separate from `vite.config.ts`, on purpose.** Vitest prefers `vitest.config.ts` when it exists, and `vite build` never reads it — so nothing in your test config can reach the production bundle. We checked that rather than assumed it: the build output was byte-for-byte identical with the suite present and absent.

```ts
// vitest.config.ts — separate from vite.config.ts on purpose.
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    include: ['src/**/*.test.ts', 'src/**/*.test.tsx'],
    environment: 'node',        // node is the default; jsdom is opt-in per file
    css: true,                  // load-bearing, see below
    coverage: { provider: 'v8', reporter: ['text', 'lcov'] },
  },
});
```

**`css: true` is load-bearing. Do not "simplify" it away.** Vite classifies an id as CSS by extension *before* it looks at the query string. With the default `css: false`, `import css from './anim.css?raw'` resolves to the **empty string**, silently. A test auditing that string ("every `animation:` sits under a state selector") then passes by reading nothing — the exact shape of a guard that has never failed. When we flipped it: 12,628 characters where there had been 0. It does not enable CSS Modules or component rendering; it makes `?raw` honest. Silently-missing must not read as green.

**Where tests live.** Colocated: `foo.ts` next to `foo.test.ts`, matched by `src/**/*.test.ts`. Keep them inside `tsconfig.json`'s `include`, so `npx tsc --noEmit` and `npm run lint` cover them like any other source file — a test that stops compiling fails the same checks the app does.

**Keep `node` the default environment; opt into jsdom per file** with a `// @vitest-environment jsdom` control comment on the first line. A jsdom global costs startup time on every pure-function file that does not need it. Verified against https://vitest.dev/guide/environment on 2026-09-07. Note: `environmentMatchGlobs` was deprecated in Vitest 3 and **removed in Vitest 4** — if you need per-directory environments, use `projects` in the config, not `environmentMatchGlobs` (verified against https://vitest.dev/guide/migration/ on 2026-09-07).

---

## 3. What to unit test

Five categories earn their place. Everything else is a component test.

| Category | Example assertions |
|---|---|
| Formatters / maskers | `mask('12345678')` -> `'12345-678'`; digits-only storage vs. the display mask |
| Validators | Required-field errors on both the domestic and foreign branches of an address form |
| Mappers / merge rules | Which side wins when an autofill result meets a value the user already typed |
| Storage/blob parsers | Version gate, unknown keys dropped, out-of-range values **discarded, never clamped** |
| API-client request shape | The exact `{ url, method, data }` the client sends |

```ts
// src/shared/utils/postcode.test.ts
import { describe, expect, it } from 'vitest';
import { digitsOf, isComplete, mask } from './postcode';

describe('postcode', () => {
  it('formats eight digits as 00000-000', () => expect(mask('12345678')).toBe('12345-678'));
  it('stores digits only, whatever the user typed', () => expect(digitsOf('12.345-678')).toBe('12345678'));
  it('rejects a partial code', () => expect(isComplete('1234')).toBe(false));
});
```

**Version gates deserve a test each.** A blob written by an older build is the one input you cannot reproduce by clicking.

```ts
it('discards an out-of-range value instead of clamping it', () => {
  expect(parseDraft({ version: 6, yearsExperience: 99 }).yearsExperience).toBeUndefined();
});
```

### The API-client request-shape test, without a mocking library

If your HTTP client exposes a transport adapter (axios does), override it and record what the client tried to send. No `vi.mock`, no module graph surgery.

```ts
// src/shared/api/plans.test.ts
// @vitest-environment jsdom   // the request interceptor reads localStorage
import { expect, it } from 'vitest';
import apiClient from './client';
import { confirmPlan } from './plans';

it('sends the plan id in the body, not the query string', async () => {
  const sent: Array<{ url?: string; method?: string; data?: unknown }> = [];
  apiClient.defaults.adapter = async (config) => {
    sent.push({ url: config.url, method: config.method, data: config.data });
    return { status: 200, statusText: 'OK', data: {}, headers: {}, config };
  };

  await confirmPlan('plan-42');
  expect(sent).toHaveLength(1);
  expect(sent[0].method).toBe('post');
  expect(sent[0].url).toBe('/plans/confirm');
  expect(JSON.parse(String(sent[0].data))).toEqual({ planId: 'plan-42' });
});
```

Restore the adapter in an `afterEach` if other tests in the file share the client. If your client does not expose an adapter (`fetch` wrappers usually do not), use MSW instead — section 7.

---

## 4. What NOT to unit test

| Do not | Because |
|---|---|
| Every prop combination of a component | You are testing the framework's render loop, not your logic. Test the states a user can reach. |
| Router internals | React Router is tested by React Router. Test that *your* guard redirects. |
| Whether the server accepts a request | Nothing in jsdom can know. That is E2E, or a backend integration test. |
| CSS: colors, spacing, layout | Snapshot the *rule*, not the pixels, and only when a rule is load-bearing (see `css: true`). |
| Third-party components | If a date picker is broken, file a bug upstream; do not enshrine its DOM in your suite. |
| Anything needing a live backend | The moment the fast loop needs a server it becomes a second slow suite and people stop running it. |

---

## 5. Component tests with Testing Library

**Query priority, in order.** Use the first one that fits.

| Rank | Query | Use for |
|---|---|---|
| 1 | `getByRole('button', { name: 'Submit' })` | Anything in the accessibility tree — buttons, links, headings, inputs by role |
| 2 | `getByLabelText('Email')` | Form fields with a label |
| 3 | `getByPlaceholderText('you@example.com')` | Fields with no label (fix the label instead when you can) |
| 4 | `getByText('Confirm')` | Non-interactive content |
| 5 | `getByDisplayValue` / `getByAltText` / `getByTitle` | Values, images, title attributes |
| 6 | `getByTestId('plan-card')` | Last resort, when nothing above can identify the element |
| — | CSS classes, XPath, arbitrary ids | **Never.** `.MuiButton-root` breaks on a library upgrade and tells you nothing about the user. |

Verified against https://testing-library.com/docs/queries/about/ on 2026-09-07. The same hierarchy applies to Playwright locators — one rule for the whole frontend, see [e2e-testing-guide.md](./e2e-testing-guide.md).

**`user-event` over `fireEvent`.** `fireEvent.click` dispatches one event; `user.click` does what a browser does — pointer events, focus, then click — which is how you catch a button that is visually clickable and actually `disabled`. v14 is async: build the instance before `render`, `await` every interaction. For anything asynchronous use **`findBy*`**, which retries until the element appears or the timeout hits; never `await new Promise(r => setTimeout(r, 500))`.

```tsx
// @vitest-environment jsdom
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it } from 'vitest';
import { PlanForm } from './PlanForm';

it('keeps submit disabled until a plan is chosen', async () => {
  const user = userEvent.setup();
  render(<PlanForm plans={[{ id: 'plan-42', name: 'Starter' }]} />);
  expect(screen.getByRole('button', { name: 'Confirm' })).toBeDisabled();
  await user.click(screen.getByRole('radio', { name: 'Starter' }));
  expect(await screen.findByRole('button', { name: 'Confirm' })).toBeEnabled();
});
```

**One behaviour per test**, named as a sentence a product person would recognise. Many asserts in one test is a design smell: when it goes red you learn "something in the form broke", which is not information.

**TanStack Query components need a wrapper**, with retries off so a failing fixture fails fast instead of retrying for 30 s — and a **new** `QueryClient` per test, because a shared one leaks cached data and produces order-dependent green.

```tsx
const wrapper = ({ children }: { children: React.ReactNode }) => {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
};
render(<PlanList />, { wrapper });
```

**Accessibility, cheaply.** `jest-axe` turns a component test into an a11y check: `expect(await axe(container)).toHaveNoViolations()`. Put it on the design-system components, not on every screen. **Storybook interaction tests** are a fine optional middle layer if you already maintain stories — `play` functions run the same queries — but do not adopt Storybook in order to get tests.

---

## 6. Mocking the network

Two options, and the choice is about where the seam is.

| Approach | Use when | Seam |
|---|---|---|
| Adapter override (section 3) | You are asserting the **request shape** of one client call | Inside your HTTP client |
| MSW `setupServer` | A component fetches, and you want realistic responses and error paths | At the network boundary |

```ts
// src/test/server.ts
import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';

export const server = setupServer(
  http.get('/api/plans', () => HttpResponse.json([{ id: 'plan-42', name: 'Starter' }])),
);

// vitest setupFiles
beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

Verified against https://mswjs.io/docs/api/setup-server/ and https://mswjs.io/docs/api/setup-server/listen/ on 2026-09-07. `onUnhandledRequest: 'error'` is the setting that matters: without it an unmatched request goes out for real and the test passes for the wrong reason.

**Override per test, do not build a second backend:** `server.use(http.get('/api/plans', () => new HttpResponse(null, { status: 500 })))` inside the one test that needs the error path, and let `resetHandlers()` clean it up. And **never mock the module that contains the logic you are testing** — if `plans.ts` is under test, mocking `plans.ts` leaves you asserting your own mock. Mock the transport, never the subject.

**Know what a request-shape test proves.** It proves your client sends the right body. It does not prove the server accepts it — field names, required headers, and content types are a contract only E2E or a backend integration test can check. One of our projects had a green frontend suite that was read in review as "request bodies are correct". Nothing in that suite touched an API client. The defect it was supposed to have caught shipped. Write the boundary into the repo doc so the next reader cannot make the same inference.

---

## 7. Playwright hand-off

Everything in the right column of the scope-boundary table goes to Playwright: rendering across routes, navigation, real session and auth, mobile layout, a11y of the assembled page, anything touching a real server. The mandate that keeps the two suites honest: **every UI feature or fix ships a spec at the layer where the bug lives.** If you fix a bug, write the test that would have caught it — a rendering bug gets a component test, a routing bug gets a Playwright spec, a formatter bug gets a unit test. See [e2e-testing-guide.md](./e2e-testing-guide.md) for page objects, test data, teardown and the production guard, and [enforcement/README.md](./enforcement/README.md) to make the mandate a gate rather than a wish.

---

## 8. Coverage that means something

Coverage is a floor on new code with a ratchet, never a target. `npm test -- --coverage` with the v8 provider; thresholds live in the config so the number is enforced, not admired.

```ts
coverage: {
  provider: 'v8',
  include: ['src/**/*.{ts,tsx}'],
  thresholds: { lines: 60, functions: 60, branches: 50, autoUpdate: true },
}
```

Verified against https://vitest.dev/config/coverage on 2026-09-07. `thresholds.autoUpdate` writes the new, higher numbers back into the config when coverage improves — that is the ratchet, and it means the threshold can only go up.

**What a fake coverage test looks like.** An AI asked for "more coverage" produces `it('renders', () => { render(<PlanForm plans={[]} />); })` — no assertion, covers lines, proves nothing. It is worse than no test, because it converts an honest gap into a green number. Detection, in one pass: `grep -rn "expect(true)\|expect(1)\.toBe(1)\|toMatchSnapshot()" src` and count `it(` versus `expect(` per file. A file where those two counts diverge sharply is coverage theatre. A green number you cannot trust is worse than an honest gap.

**Mutation testing is the honest check.** Stryker (`npx stryker run`) mutates your source and reports which mutants your suite failed to kill. Run it once on the module you care most about; it will tell you in one afternoon which of your tests assert nothing. Optional, and slow — do not put it in the per-commit gate.

---

## 9. Lint and types are not tests

Until one of our frontends got a runner, `npm run lint` and `tsc --noEmit` were the entire safety net, and neither can tell whether a value is *right*. `tsc` is happy with a mask function that returns `'87654-321'`. ESLint is happy with a request that posts to the wrong endpoint. They catch a different bug class, they are cheap, keep them in the gate — and do not let anyone count them as test coverage.

---

## 10. Day 1 / Week 1 — greenfield

| When | Do |
|---|---|
| Day 1 | `npm i -D vitest`; create `vitest.config.ts` (separate from `vite.config.ts`, `css: true`, `environment: 'node'`); add `"test": "vitest run"` and `"test:watch": "vitest"` |
| Day 1 | Write one trivially true test, run it, then break it on purpose and confirm you see red. Prove the harness before you trust its verdict |
| Day 1 | Put the single-test command in the README (`npx vitest run src/shared/utils/postcode.test.ts`), and the test globs in `tsconfig.json`'s `include` and the lint config |
| Day 2-4 | First real tests on the formatters and validators you already have; then install jsdom + Testing Library + user-event and write the first component test on the form with the most states |
| Week 1 | CI job running `npm ci && npm test`; add `--coverage` with a low threshold and `autoUpdate: true`; write the scope-boundary table into `docs/testing.md` and adopt "fix a bug, write the test" from commit one |

## 11. Day 1 / Week 1 — legacy app with no tests

| When | Do |
|---|---|
| Day 1 | Add vitest **without touching `vite.config.ts`**. A new `vitest.config.ts` cannot change the production bundle; verify by diffing the build output before and after |
| Day 1 | One trivially true test, run it, see it green; then see it red. Do not skip this on an unfamiliar build |
| Day 1 | Record the honest baseline in `docs/testing.md`: how many tests exist, how long they take, what is known-red on a clean checkout |
| Day 2 | First real test on the gnarliest formatter or validator in the codebase — the one everyone edits nervously. Characterize current behaviour first, even the parts that look wrong; fix afterwards, with the test as the record |
| Day 3 | Write the API-client request-shape test for the **last production defect** you shipped. That test has a proven-valuable assertion; a test for a bug you never had does not |
| Week 1 | jsdom + Testing Library only when a component test is actually next; do not install them "to be ready". Coverage threshold set to today's number with `autoUpdate: true` — ratchet on new code, never a big-bang push |
| Week 1 | Put the scope-boundary table and the single-test command in the repo's AI instruction file, so agents stop writing backend-dependent tests into the fast loop |

---

## 12. Same idea in other frontends

| Stack | Runner | Component library | Network mock | Notes |
|---|---|---|---|---|
| Vue 3 | vitest | `@vue/test-utils` + `@testing-library/vue` | MSW | Same query priority; prefer the Testing Library wrapper for behaviour tests |
| Svelte | vitest | `@testing-library/svelte` | MSW | `vitest-browser-svelte` if you want a real browser instead of jsdom |
| Angular | Jest or vitest (via `@analogjs/vite-plugin-angular`) | `@testing-library/angular` over raw `TestBed` | MSW | `TestBed` tests drift into implementation detail fast |
| Plain Node / no framework | vitest or `node --test` | — | MSW (`msw/node`) or `undici` MockAgent | Keep `environment: 'node'`; there is nothing to render |
| React Native | Jest | `@testing-library/react-native` | MSW | Same query priority; E2E via Detox or Maestro |

---

## Sources & further reading

- Vitest — config, environments, coverage: https://vitest.dev/config/ · https://vitest.dev/guide/environment · https://vitest.dev/guide/coverage
- Testing Library, "About Queries" (the official priority order): https://testing-library.com/docs/queries/about/ · `user-event` v14: https://testing-library.com/docs/user-event/intro
- Kent C. Dodds, "The Testing Trophy" and "Testing Implementation Details": https://kentcdodds.com/blog/the-testing-trophy-and-testing-classifications
- MSW v2 — `setupServer`: https://mswjs.io/docs/api/setup-server/ · Stryker Mutator: https://stryker-mutator.io/
- TanStack Query testing guide: https://tanstack.com/query/latest/docs/framework/react/guides/testing

## Related

- [testing-from-zero.md](./testing-from-zero.md) — layers, the first-week plan, the test-smell catalogue
- [e2e-testing-guide.md](./e2e-testing-guide.md) — where the right column of the scope-boundary table goes
- [enforcement/README.md](./enforcement/README.md) — turning these recommendations into instruction files, hooks and CI gates

_Last reviewed: 2026-09-07._
