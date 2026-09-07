# Frontend Performance Guide (React / TypeScript)

**Best used when:** you own a React + TypeScript app — a fresh Vite project or a legacy one — with no performance practice, and you want numbers instead of opinions.
**Read before:** shipping a dashboard, accepting an AI-written "production-ready" frontend, or "optimizing" by wrapping components in `React.memo`.
**See also:** [performance-from-zero.md](./performance-from-zero.md) · [enforcement/README.md](./enforcement/README.md) · [../../skills/perf-engineer/SKILL.md](../../skills/perf-engineer/SKILL.md)

The standing review question for every frontend PR is the same one the backend uses: **"Can this change hurt performance? Query inside a loop, load without pagination, objects piling up in memory."** On the web it reads as: request inside a render, list without a page, state holding the whole dataset. The companion rule keeps you honest in the other direction — **maintainable > fast, optimize only when measured**. This guide separates the two: *structural hygiene* you apply always (pagination, virtualized lists, explicit cache TTLs, code splitting per route), and *optimization* you apply only after a profiler names a hotspot. Everything here is recommendation; the gates that enforce it live in [enforcement/](./enforcement/README.md).

> Three AI agents built two web apps and a shared component library in parallel in one night. Build green, zero TypeScript errors, "production-ready" in the summary. Nobody had run Lighthouse, nobody knew the bundle size, and the one list page that would grow (a conversions history) had pagination in the spec and no measurement of what happened when it was ignored.

---

## 1. Core Web Vitals — the three numbers you owe your users

| Metric | What it measures | Good (p75) | Lab proxy |
|---|---|---|---|
| **LCP** — Largest Contentful Paint | When the main content became visible | <= 2.5 s | LCP in Lighthouse |
| **INP** — Interaction to Next Paint | Responsiveness across all interactions on the page | <= 200 ms | Total Blocking Time (TBT) |
| **CLS** — Cumulative Layout Shift | Visual stability (content jumping) | <= 0.1 | CLS in Lighthouse |

Rules that come with the numbers ([web.dev/articles/vitals](https://web.dev/articles/vitals)):

- Thresholds apply at the **75th percentile of real page loads**, segmented by mobile and desktop. Your laptop on office wifi is not the percentile.
- **FID is retired.** It was replaced by INP as a Core Web Vital in March 2024. If a dashboard still shows FID, it is stale.
- A "good" score means p75 in the good bucket — not an average, and not one lucky run.

### Lab vs field: you need both

| | Lab (synthetic) | Field (real users) |
|---|---|---|
| Tools | Lighthouse, Lighthouse CI, WebPageTest | Chrome UX Report (CrUX), your own RUM via the `web-vitals` library |
| Answers | "Did this PR regress?" | "Are users actually suffering?" |
| Strength | Reproducible, gateable in CI | Real devices, real networks, real INP |
| Weakness | One synthetic device, no real interactions (INP is not measurable) | Slow feedback, needs traffic |

Ship both: lab catches the regression before merge, field tells you which page to fix first.

### Run it locally, today

```bash
# One-off audit of any URL, performance category only
npx lighthouse https://your-app.example --only-categories=performance --view

# Full CI-shaped run against a built dist/ (see section 7); in the browser, use the DevTools Lighthouse panel
npx lhci autorun
```

### Field measurement in ~10 lines

```ts
// src/rum.ts — import once from your app entry point
import { onCLS, onINP, onLCP } from 'web-vitals';

function report(metric: { name: string; value: number; id: string }) {
  navigator.sendBeacon('/api/rum', JSON.stringify(metric)); // or your analytics SDK
}

onLCP(report);
onINP(report);
onCLS(report);
```

<!-- Verified against https://github.com/GoogleChrome/web-vitals on 2026-09-07 -->
`web-vitals/attribution` exports the same functions with an extra `attribution` field naming the element or script responsible — use it when a number is bad and you cannot reproduce it locally.

---

## 2. Budgets: a number in a file, checked by CI

| Signal | Budget | Where measured | Gate |
|---|---|---|---|
| LCP / INP / CLS (p75) | <= 2.5 s / <= 200 ms / <= 0.1 | Lighthouse CI (lab), RUM (field) | CI assertion |
| Lighthouse performance score | >= 0.9 | Lighthouse CI | CI assertion |
| Total Blocking Time (INP's lab proxy) | < 300 ms | Lighthouse CI | CI assertion (warn first) |
| JS shipped on the first route | < 200 KB gzip | Lighthouse `resource-summary` or a bundle analyzer | CI assertion |
| API p95 latency behind the screen | < 300 ms read / < 500 ms write | backend load test | backend CI |

**200 KB gzip is a starting point, not a law.** Own it: set the number your team can defend, write it in the repo, and lower it when you beat it. A budget nobody chose is a budget nobody defends.

Two traps worth memorizing. `resource-summary:script:size` in a Lighthouse CI assertion is in **bytes** (`204800` = 200 KB), while the same limit in a `budget.json` file is in **kilobytes** — mixing them silently gives you a 200-byte or a 200-MB budget. And Lighthouse reports **transfer size** while your bundler reports raw size: compare like with like.

### See what you actually ship

```bash
npm i -D rollup-plugin-visualizer   # plugin, part of every build
npx vite-bundle-visualizer          # or one-off, no config change
```

```ts
// vite.config.ts
import { visualizer } from 'rollup-plugin-visualizer';

export default defineConfig({
  plugins: [react(), visualizer({ gzipSize: true, brotliSize: true })],
});
```

Open the generated `stats.html` and look for: a date library shipped in full, an icon set imported as a barrel (`import { X } from 'lucide-react'` is fine; `import * as Icons` is not), a chart library on a route that has no chart, two versions of the same package. `[check exact package name and options for your version]` — both packages are actively maintained but their option names move.

The component library is not your performance problem. Third-party scripts are.

---

## 3. Code splitting and loading

**Route-level splitting is hygiene, not optimization.** A user opening the login page should not download the analytics dashboard.

```tsx
import { lazy, Suspense } from 'react';
const Dashboard = lazy(() => import('./routes/Dashboard'));

<Suspense fallback={<PageSkeleton />}>
  <Dashboard />
</Suspense>
```

Vite splits on every dynamic `import()` automatically. Manual chunking is the next lever, and both its config path and its option name moved when Vite switched to Rolldown:

```ts
// vite.config.ts — Vite on Rolldown: one vendor chunk for React, everything else split per route
export default defineConfig({
  build: {
    rolldownOptions: {
      output: {
        advancedChunks: { groups: [{ name: 'vendor', test: /\/react(?:-dom)?/ }] },
      },
    },
  },
});
```

<!-- Verified on 2026-09-07:
     - https://v7.vite.dev/guide/rolldown documents the replacement for manualChunks as
       output.advancedChunks: { groups: [{ name: 'vendor', test: /\/react(?:-dom)?/ }] } (shown there under
       build.rollupOptions).
     - https://vite.dev/config/build-options says build.rollupOptions is "an alias of build.rolldownOptions ...
       use build.rolldownOptions instead", so the same object goes under rolldownOptions on current Vite.
     - Rolldown has since renamed advancedChunks to codeSplitting with the same groups shape (advancedChunks is
       ignored when both are set) — [check] against https://rolldown.rs before relying on either name; the rename
       was seen in search results, not fetched from the reference page. -->

Old blog snippets show `build.rollupOptions.output.manualChunks(id) { ... }`; on a Vite that still accepts it the alias keeps it working, but write the `groups` form for new config.

Loading rules that cost nothing and buy LCP:

| Do | Why |
|---|---|
| Preload the LCP image: `<link rel="preload" as="image" href="/hero.webp" fetchpriority="high">` | The LCP element is usually an image the parser finds late |
| `loading="lazy"` on **below-the-fold** images only | Lazy-loading the hero image makes LCP worse |
| Always set `width`/`height` (or `aspect-ratio`) on images and ad slots | This is most of your CLS |
| Self-host fonts, `font-display: swap`, preload the one face above the fold | Blocking font fetches delay text paint |
| Audit every third-party script; `defer` it, or load it after first interaction | Tag managers, chat widgets and session recorders are the usual LCP killers |

Third-party scripts deserve a line of their own: they are code you did not write, running on your main thread, changing size without a PR. Put them in the budget or keep them out.

---

## 4. React render discipline

**Measure first.** Install React DevTools, open the Profiler tab, record the interaction that feels slow, and read which components rendered and why. Without that recording, every `memo` you add is decoration. Hygiene, applied always:

- **Colocate state.** State used by one subtree lives in that subtree. A `useState` at the app root re-renders the app.
- **Derive, don't store.** `const total = items.reduce(...)` during render beats a `useState` + `useEffect` that mirrors it — and cannot go stale.
- **Stable keys.** `key={item.id}`, never the array index for a list that reorders, filters or paginates.
- **Virtualize long lists.** Past a few hundred rows, render only what is on screen with [`@tanstack/react-virtual`](https://tanstack.com/virtual/latest/docs/framework/react/react-virtual) (`npm i @tanstack/react-virtual`, `useVirtualizer({ count, getScrollElement, estimateSize })`). This is the web twin of Flutter's `ListView.builder`: build items lazily, never all at once.
- **Avoid layout thrash.** Batch all DOM reads (`getBoundingClientRect`, `offsetHeight`), then all writes. Read-write-read-write inside a loop forces a reflow per iteration.

Optimization (only after a measured re-render):

```tsx
// BAD — the AI asked for "performant code" and wrapped everything
const Row = React.memo(({ item }) => <li>{item.name}</li>);
const onClick = useCallback(() => setOpen(true), []);
const label = useMemo(() => `${user.first} ${user.last}`, [user]);

// GOOD — memo the one subtree the Profiler showed rendering 400x per keystroke;
// leave the rest plain until a recording says otherwise.
```

React's own docs are blunt about it: *"You should only rely on useMemo as a performance optimization"* — [react.dev/reference/react/useMemo](https://react.dev/reference/react/useMemo). Memoizing a cheap render adds allocation, dependency arrays and bugs. Wrapping everything is the frontend face of overengineering: implement it simple, refactor when a number says to.

### The fetch waterfall

```tsx
// BAD — one request per row, N+1 over HTTP, and a render loop to go with it
{rows.map((row) => <RowDetail key={row.id} id={row.id} />)}
// where RowDetail does useEffect(() => { fetch(`/api/items/${id}`) }, [id])

// GOOD — one request, the list endpoint returns what the list renders
const { data } = useQuery({ queryKey: ['items', page], queryFn: () => api.listItems(page) });
```

Same failure mode as a backend N+1, with network latency instead of SQL. Grep diffs for `fetch(` or `axios.` inside a `.map(`.

---

## 5. Server state with TanStack Query

The team rule is short: **TanStack Query owns server state.** Once it is in the project, `useEffect` + `useState` fetching is a bug, not a style choice — it re-fetches on every mount, races, and has no cache, no dedupe, no retry.

```ts
const { data, isPending } = useQuery({
  queryKey: ['orders', { page, size }],
  queryFn: () => api.listOrders({ page, size }),
  staleTime: 60_000,   // 1 min: how long the data is considered fresh
  gcTime: 5 * 60_000,  // 5 min: how long unused data stays in cache
});
```

Defaults you must know before you tune anything ([TanStack Query — Important Defaults](https://tanstack.com/query/latest/docs/framework/react/guides/important-defaults)): queries are **stale immediately** (`staleTime: 0`), so they refetch on mount, window focus and reconnect; inactive queries are garbage collected after **5 minutes** (`gcTime`); results are structurally shared so unchanged data keeps its reference.

**No TTL, no cache** — the same rule the backend applies to every Redis key. `staleTime` is the client's TTL. Leaving it at 0 for a list that changes hourly means you pay for the request on every focus change; setting it to `Infinity` means users stare at yesterday.

| Need | Use |
|---|---|
| Paginated list that must not flash empty between pages | `placeholderData: keepPreviousData` (imported from `@tanstack/react-query`) |
| Infinite feed | `useInfiniteQuery` with `getNextPageParam` |
| Instant navigation on hover | `queryClient.prefetchQuery({ queryKey, queryFn })` on `onMouseEnter` |
| Two components asking for the same thing | Nothing — identical `queryKey`s dedupe into one request |
| Data invalid after a write | `queryClient.invalidateQueries({ queryKey: ['orders'] })` in the mutation's `onSuccess` |

**Pagination contract with the backend**: `page` + `size`, `size` clamped server-side to a maximum of 100. The frontend sends it on every list call, from the first screen, before anyone knows how big the table gets. "The list is small today" is not a bound.

---

## 6. Network

| Rule | Concretely |
|---|---|
| Cache static assets hard, HTML never | Hashed filenames get `Cache-Control: public, max-age=31536000, immutable`; `index.html` gets `no-cache` |
| Use ETags for API GETs | A 304 costs a round trip, not a payload |
| Compress at the proxy | Brotli for text (HTML/JS/CSS/JSON), gzip as fallback; never compress already-compressed images |
| Send the fields the screen needs | The frontend twin of a DTO projection: a list of 50 rows should not carry 50 full aggregates with nested relations |
| No N+1 over HTTP | List endpoint returns what the list renders; add a batch endpoint (`GET /items?ids=1,2,3`) before writing a request per row |
| Fewer, larger requests on the critical path | A waterfall is latency multiplied by round trips |

One deployment note: serving the React build from the same origin as the API (for example, a Spring Boot jar serving `dist/` as static resources) removes CORS preflight `OPTIONS` requests from every non-simple call — one fewer round trip before your data starts moving.

---

## 7. Lighthouse CI as a gate

Budgets that live only in a doc drift within a sprint. Put them in `lighthouserc.json` at the repo root:

```json
{
  "ci": {
    "collect": {
      "staticDistDir": "./dist",
      "numberOfRuns": 3
    },
    "assert": {
      "assertions": {
        "categories:performance": ["error", { "minScore": 0.9 }],
        "largest-contentful-paint": ["error", { "maxNumericValue": 2500 }],
        "cumulative-layout-shift": ["error", { "maxNumericValue": 0.1 }],
        "total-blocking-time": ["warn", { "maxNumericValue": 300 }],
        "resource-summary:script:size": ["error", { "maxNumericValue": 204800 }]
      }
    },
    "upload": {
      "target": "temporary-public-storage"
    }
  }
}
```

<!-- Verified against https://github.com/GoogleChrome/lighthouse-ci/blob/main/docs/configuration.md on 2026-09-07 -->

```yaml
# .github/workflows/perf.yml — inside a job that has already run npm ci && npm run build
- run: |
    npm install -g @lhci/cli@0.15.x
    lhci autorun
  env:
    LHCI_GITHUB_APP_TOKEN: ${{ secrets.LHCI_GITHUB_APP_TOKEN }}
```

<!-- Verified against https://github.com/GoogleChrome/lighthouse-ci/blob/main/docs/getting-started.md on 2026-09-07 -->

Reading the config:

- `staticDistDir: "./dist"` is the Vite output; Lighthouse CI serves it itself. For an app that needs a live API, use `startServerCommand` + `url` instead.
- `numberOfRuns: 3` because **Lighthouse is noisy** — a single run swings several points on shared CI hardware.
- `total-blocking-time` is `warn`, not `error`: it is the **lab proxy for INP**, and INP itself only exists in the field. Treat a TBT regression as a signal to look, not a merge blocker, until your numbers are stable.
- `resource-summary:script:size` is in **bytes** here.

The runnable copy of this file lives in [enforcement/hooks/lighthouserc.json](./enforcement/hooks/lighthouserc.json), with the CI workflow beside it.

---

## 8. Playwright as a perf probe

You already run Playwright for E2E. One extra test turns it into a regression alarm on the route that matters.

```ts
import { test, expect } from '@playwright/test';

test('main route paints its largest content under 2.5 s', async ({ page }) => {
  await page.goto('/', { waitUntil: 'load' });
  const nav = await page.evaluate(() =>
    JSON.parse(JSON.stringify(performance.getEntriesByType('navigation')[0])),
  );
  // domContentLoadedEventEnd and loadEventEnd are relative to navigationStart
  expect(nav.loadEventEnd).toBeLessThan(2500);
});
```

`page.evaluate()` returning a JSON-serializable value is documented at [playwright.dev/docs/evaluating](https://playwright.dev/docs/evaluating). Everything else here is browser API, not Playwright API: `performance.getEntriesByType('navigation')` gives you load timings, **not LCP**. For real LCP inside Playwright you inject `web-vitals` (or a `PerformanceObserver` on `largest-contentful-paint`) and wait for the callback — `[unverified — check API]` for that wiring; verify against playwright.dev and the web-vitals README before trusting the number. And keep this probe on staging or a local build: a Playwright run once pointed at production in one of our projects sent about 10 real notifications to real users.

---

## 9. Review checklist (frontend)

Copy into your PR template.

- [ ] Every list screen sends `page` + `size` (size <= 100) and the UI has a next/prev or infinite control.
- [ ] No `fetch`/`axios` call inside a `.map()`, and no `useEffect` fetch per row.
- [ ] Server state goes through TanStack Query; no `useEffect` + `useState` fetching.
- [ ] Every query sets `staleTime` (and `gcTime` when it differs from the 5-minute default) deliberately.
- [ ] New route is lazy-loaded (`React.lazy` + `Suspense`) unless it is the entry route.
- [ ] Images have explicit `width`/`height`; below-the-fold ones use `loading="lazy"`; the LCP image is not lazy.
- [ ] No new third-party script without a named owner and a size number.
- [ ] Lists longer than ~200 rows are virtualized.
- [ ] Any `memo`/`useMemo`/`useCallback` added in this PR names the Profiler recording that justified it.
- [ ] `lhci autorun` passed, or the PR states which budget moved and why.

---

## 10. Same idea in Next.js / Vue / Angular

| Concern | Next.js (App Router) | Vue 3 | Angular |
|---|---|---|---|
| Route-level splitting | Automatic per route; `next/dynamic` for components | `defineAsyncComponent` + router `component: () => import(...)` | `loadComponent` / `loadChildren` lazy routes |
| Image discipline | `next/image` (sizing, formats, `priority` for LCP) | `<img>` + explicit dimensions, or `@unhead` preload | `NgOptimizedImage` (`ngSrc`, `priority`) |
| Render on the server | Server Components / streaming SSR by default | Nuxt SSR / `<Suspense>` | Angular SSR (hydration, `@defer` blocks) |
| Profiler | React DevTools Profiler + `next build` output sizes | Vue DevTools performance timeline | Angular DevTools profiler |

The measurement layer does not change: Lighthouse for the lab, `web-vitals` for the field, a budget in CI.

---

## 11. Day 1 / Week 1

### Greenfield (new Vite + React + TypeScript app)

| When | Do | Command / change |
|---|---|---|
| Day 1 | TypeScript `strict: true`, ESLint + Prettier | `"strict": true` in `tsconfig.json` |
| Day 1 | Baseline the empty app | `npm run build && npx lighthouse http://localhost:4173 --only-categories=performance --view` (after `npm run preview`) |
| Day 1 | Write the budget table (section 2) into `perf-budgets.md` | one file, five rows, the team's numbers |
| Day 1 | TanStack Query for server state, with an explicit default | `new QueryClient({ defaultOptions: { queries: { staleTime: 30_000 } } })` |
| Week 1 | Lighthouse CI in the pipeline | `npm i -D @lhci/cli@0.15.x`, add `lighthouserc.json` (section 7), `npx lhci autorun` |
| Week 1 | Bundle visibility | `npm i -D rollup-plugin-visualizer`, add to `vite.config.ts`, look at `stats.html` |
| Week 1 | Field RUM | `npm i web-vitals`, wire `onLCP/onINP/onCLS` to your analytics |
| Week 1 | Lazy-load every non-entry route | `React.lazy` + `Suspense` |

### Legacy (existing app, no practice)

| When | Do | Command / change |
|---|---|---|
| Day 1 | Pick the one screen users complain about; measure it and write the number down | `npx lighthouse <url> --only-categories=performance --view` |
| Day 1 | See the bundle before touching code | `npx vite-bundle-visualizer` (or the plugin) |
| Day 1 | Grep for fetch-in-render and per-row requests | `grep -rn "useEffect" src` then search those files for `fetch(` / `axios.`, and for `fetch(` near `.map(` |
| Day 1 | List the third-party scripts in `index.html`, name an owner for each | a table in the PR description |
| Week 1 | Fix the top three by user impact — usually: unpaginated list, unsplit route, an unoptimized hero image | one PR each, with a before/after Lighthouse number |
| Week 1 | Add `staleTime` to the noisiest queries, or introduce TanStack Query on one screen | do not migrate the whole app at once |
| Week 1 | Add `lighthouserc.json` with today's numbers as the ceiling, then tighten | `numberOfRuns: 3`, start assertions at `warn` |
| Week 1 | Add the review checklist (section 9) to the PR template | one commit |

**Working with an AI coding tool?** Give it the constraints up front and demand evidence:

```text
Context: React 19 + TypeScript + Vite, TanStack Query. This list can reach ~200k rows in two years.
Task: <the feature>.
Constraints:
- Every list call is paginated (page + size, size max 100).
- No fetch/axios inside a loop or per row; one request for the list.
- Server state via TanStack Query with an explicit staleTime; no useEffect+useState fetching.
- New routes are lazy-loaded; images carry width/height.
- Do NOT add memo/useMemo/useCallback, caching or workers unless I ask.
Verification: show the network requests for the main path and the built chunk sizes,
and the command you ran to get them. Do not claim a Lighthouse score you did not run.
```

Reject "production-ready" without an attached `lighthouse` or `lhci autorun` output. A number nobody measured is a hope.

---

## Sources & further reading

- web.dev, "Core Web Vitals" — LCP <= 2.5 s, INP <= 200 ms, CLS <= 0.1 at p75; FID retired: https://web.dev/articles/vitals
- web.dev, "Measure performance with the RAIL model" — 100 ms response, 10 ms per frame, 50 ms idle chunks: https://web.dev/articles/rail
- GoogleChrome/web-vitals — the library for field measurement, plus the attribution build: https://github.com/GoogleChrome/web-vitals
- Lighthouse CI configuration and getting started — assertion shapes, `staticDistDir`, GitHub Actions: https://github.com/GoogleChrome/lighthouse-ci/blob/main/docs/configuration.md
- React docs, `useMemo` — "You should only rely on useMemo as a performance optimization": https://react.dev/reference/react/useMemo
- TanStack Query, "Important Defaults" — stale-by-default, 5-minute `gcTime`, structural sharing: https://tanstack.com/query/latest/docs/framework/react/guides/important-defaults
- TanStack Virtual (React) — `useVirtualizer` for long lists: https://tanstack.com/virtual/latest/docs/framework/react/react-virtual
- Vite build options — `build.rolldownOptions`, and `build.rollupOptions` as its alias: https://vite.dev/config/build-options
- Vite 7 Rolldown integration guide — `output.advancedChunks.groups` as the `manualChunks` replacement: https://v7.vite.dev/guide/rolldown
- Playwright, "Evaluating JavaScript" — `page.evaluate()` and `addInitScript()`: https://playwright.dev/docs/evaluating

## Related

- [performance-from-zero.md](./performance-from-zero.md) — the language-agnostic entry point: golden signals, budgets, the eight ways an AI writes slow code
- [backend-performance-guide.md](./backend-performance-guide.md) — the API behind these screens: N+1, indexes, pagination contract, caching ladder
- [mobile-performance-guide.md](./mobile-performance-guide.md) — the same discipline on a frame budget
- [enforcement/README.md](./enforcement/README.md) — instructions, hooks and CI gates that make these rules stick
- [enforcement/hooks/lighthouserc.json](./enforcement/hooks/lighthouserc.json) — the runnable copy of section 7
- [../../skills/perf-engineer/SKILL.md](../../skills/perf-engineer/SKILL.md) — the agent skill that reviews for all of this

_Last reviewed: 2026-09-07._
