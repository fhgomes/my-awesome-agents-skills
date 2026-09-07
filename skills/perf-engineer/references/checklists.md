# Perf Engineer — Ready Checklists

Bundled with the `perf-engineer` skill. Self-contained: everything needed to run a performance
review or a first week is on this page.

## Review checklist — backend

- [ ] Every list endpoint is paginated and the page size is clamped (max 100). No `findAll()` from a service.
- [ ] No repository, HTTP or file call inside a `for` / `forEach` / `map`. Batch or join instead.
- [ ] Known associations fetched with `JOIN FETCH`, `@EntityGraph` or `@BatchSize`; `@ManyToOne` set to LAZY.
- [ ] Read endpoints use DTO projections and `@Transactional(readOnly = true)`.
- [ ] Every new WHERE / JOIN / ORDER BY column has an index created in the same migration.
- [ ] `EXPLAIN (ANALYZE, BUFFERS)` attached for every new query; rows examined vs returned is sane (< 10x).
- [ ] Every outbound call has a connect timeout and a read timeout.
- [ ] Every cache key has a TTL, and the write path evicts it.
- [ ] Thread pools, queues and the connection pool are bounded; retries capped (backoff, max 3) with a dead letter.
- [ ] Aggregation happens in the database (`COUNT`, `SUM`, materialized view), not in a loop in the service.

## Review checklist — web frontend

- [ ] A Lighthouse run exists for the route this PR changes, and the score/metrics are in the PR.
- [ ] JS shipped on the first route is inside the budget (set one; 200 KB gzip is a defensible start).
- [ ] Route-level code splitting is in place; no single vendor mega-chunk.
- [ ] Long lists are virtualized.
- [ ] Every query sets `staleTime` and `gcTime` explicitly.
- [ ] No fetch waterfall — no request per rendered row, no `useEffect` chain to load one screen.
- [ ] `memo` / `useMemo` / `useCallback` appear only where the Profiler showed the re-render.
- [ ] Images are sized, lazy below the fold, and the LCP image is preloaded.

## Review checklist — mobile (Flutter)

- [ ] `build()` does no I/O, no `await`, no heavy compute; big widgets are split.
- [ ] Lists use `ListView.builder` / `GridView.builder` / slivers — never a materialized children list.
- [ ] `const` constructors used wherever the analyzer allows.
- [ ] Images decoded at display size (`cacheWidth`) and cached; server-side resizing where possible.
- [ ] No `Opacity`, `saveLayer` or shadow-heavy widgets inside animations.
- [ ] Big JSON decoding runs off the UI isolate (`compute` / `Isolate.run`).
- [ ] Frame times measured in profile mode on a physical device, not debug, not an emulator.
- [ ] App size delta measured and inside the budget.

## Budgets (starting points — tune to the product, then gate them)

| Signal | Budget | Measured with |
|---|---|---|
| API p95 latency, read | < 300 ms | k6 or Gatling against staging |
| API p95 latency, write | < 500 ms | same |
| Error rate under load | < 1% | same |
| Rows examined per row returned | < 10 | `EXPLAIN (ANALYZE, BUFFERS)` in review |
| LCP / INP / CLS at p75 | <= 2.5 s / <= 200 ms / <= 0.1 | Lighthouse CI, field RUM |
| JS on first route | < 200 KB gzip | Lighthouse `resource-summary`, bundle analyzer |
| Frame time | < 16 ms at 60 Hz, < 8 ms at 120 Hz | profile mode overlay, `integration_test` traces |
| App size delta per PR | < +500 KB unless justified | `flutter build ... --analyze-size` |

CWV thresholds: https://web.dev/articles/vitals . Frame budget: https://docs.flutter.dev/perf/best-practices .
API latency rows are practical defaults, not a standard.

## Day 1 / Week 1 — new project

| When | Do |
|---|---|
| Day 1 | Turn on SQL logging in dev: `logging.level.org.hibernate.SQL=DEBUG`, `spring.jpa.properties.hibernate.generate_statistics=true`, `spring.jpa.open-in-view=false` |
| Day 1 | Expose metrics: `management.endpoints.web.exposure.include=health,info,metrics,prometheus` (protected), then read `http.server.requests` and `hikaricp.connections.pending` |
| Day 1 | Write the budget table above into the repo with your numbers |
| Day 1 | Pagination contract fixed on day one: `page`, `size`, max size 100, same names on client and server |
| Week 1 | `k6 run --env BASE_URL=<staging> perf/k6-smoke.js` with `http_req_duration: ['p(95)<300']` and `http_req_failed: ['rate<0.01']`, wired into CI (a failed threshold exits non-zero) |
| Week 1 | `npx lighthouse <url> --only-categories=performance` on the main route, then `lhci autorun` in CI |
| Week 1 | PR template line: "EXPLAIN (ANALYZE, BUFFERS) attached for every new query" |
| Week 1 | Mobile: one `flutter run --profile` session on a physical device with the overlay on |

## Day 1 / Week 1 — existing project with no practice

| When | Do |
|---|---|
| Day 1 | Pick the one endpoint or screen users complain about. Measure it. Write the number down with the date |
| Day 1 | Grep the codebase: `findAll()` without `Pageable`, `.findAll().stream()`, repository calls inside loops, `ListView(` with `children:`, `SELECT *` |
| Day 1 | Turn on SQL logging in dev and load the slowest screen once. Count the statements |
| Week 1 | Fix the top 3 by user impact — hygiene only (pagination, index, N+1). No caching yet |
| Week 1 | Add the threshold that would have caught each one: a k6 threshold, a Lighthouse assertion, a statement-count test |
| Week 1 | Re-measure the day-1 number and put both numbers side by side in the PR |
| Week 1 | Only now consider caching, and only with a TTL on every key |

## Asking an AI for performant code

```text
Context: <stack, expected data volume in 2 years, current p95 if known>.
Task: <the feature>.
Constraints:
- Every list endpoint / query is paginated (page + size, max size 100).
- No repository/DB/HTTP call inside a loop; batch or join instead.
- New columns used in WHERE/JOIN/ORDER BY get an index in the same migration.
- Outbound calls have explicit timeouts.
- Do NOT add caching, memoization or async unless I ask.
Verification: show me the SQL generated for the main path (or the bundle size / frame time)
and the command you ran to get it. Do not claim a latency you did not measure.
```

Acceptance rule: no number, no merge.

_Last reviewed: 2026-09-07._
