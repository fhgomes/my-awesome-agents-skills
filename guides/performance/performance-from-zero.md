# Performance From Zero

**Best used when:** you own a codebase with no performance practice — greenfield or ten years old — and you want a first day and a first week that pay off, with or without an AI coding tool driving the keyboard.
**Read before:** shipping your first list endpoint, accepting an AI-written "production-ready, sub-100 ms" claim, or opening a profiler because something "feels slow".
**See also:** [backend-performance-guide.md](./backend-performance-guide.md) · [frontend-performance-guide.md](./frontend-performance-guide.md) · [mobile-performance-guide.md](./mobile-performance-guide.md) · [enforcement/README.md](./enforcement/README.md) · [../../skills/perf-engineer/SKILL.md](../../skills/perf-engineer/SKILL.md)

Two lines carry this whole guide. The first is a standing code-review question: **"Can this change hurt performance? Query inside a loop, load without pagination, objects piling up in memory."** The second is the rule that keeps you from wasting a week: **"Maintainable > fast — optimize only when measured."** They look contradictory. They are not, and resolving them is section 1.

This guide is language-agnostic. Every rule holds in Java, TypeScript, Dart, Go, Python or Ruby. The stack guides above add the commands.

---

## 1. Two categories, and why the contradiction dissolves

Most performance arguments are two people using one word for two different things.

| Category | When you apply it | Examples |
|---|---|---|
| **Structural hygiene** | Always, in review, no measurement needed | Pagination on every list; an index on every FK and every column you filter, join or sort by; no query inside a loop; fetch known associations in one statement; lazy/virtualized list widgets; a TTL on every cache key; bounded thread and connection pools; an explicit timeout on every outbound call |
| **Optimization** | Only after a measurement names the hotspot | Caching a computed value; memoizing a UI subtree; tuning pool sizes; GC flags; code-splitting one specific route; batch sizes; object reuse |

Hygiene is not optimization. Pagination is the difference between O(n) and O(1) as the table grows — measuring it is redundant, skipping it is how "worked fine with 100 rows" dies at 100k. "Optimize only when measured" governs the second row, never the first.

> `repository.findAll().stream().filter(...)` showed up, written by an AI assistant, in two unrelated projects of ours within the same quarter. Both worked in dev with 200 rows. One of them was a table that grows by thousands of rows a day.

---

## 2. Measure first

The loop, in order. Skipping step 1 means you cannot tell an improvement from a coincidence.

```text
baseline  ->  budget  ->  change  ->  measure  ->  keep or revert
   |            |           |           |              |
 a number    a number   one thing    same tool     revert is a
 in a file   in a file  at a time    same load     normal outcome
```

**A performance change is still a normal change.** It passes the same gates as any other work: the build succeeds, the files exist, the behaviour works, nothing regressed, and it follows the patterns already in the repo. A 40% latency win that breaks pagination ordering is a rollback, not a win.

### The four golden signals

From Google's SRE book, [Monitoring Distributed Systems](https://sre.google/sre-book/monitoring-distributed-systems/). If you instrument nothing else, instrument these four.

| Signal | What it answers | Typical first measurement |
|---|---|---|
| Latency | How long does a request take — and how long for the unlucky ones? | p50 / p95 / p99 per route, successes and errors separated |
| Traffic | How much demand is arriving? | requests/second, active sessions, queue depth in messages/second |
| Errors | What fraction fails? | 5xx rate, plus "successful but wrong" (200 with an empty payload) |
| Saturation | How full is the most constrained resource? | connection pool in use vs max, heap after GC, CPU run queue, disk queue |

Latency and errors are not independent: a fast 500 will flatter your p95 if you average both together. Split them.

For saturation, the optional deeper lens is Brendan Gregg's [USE method](https://www.brendangregg.com/usemethod.html) — for every resource, check Utilization, Saturation and Errors. Use it when the app looks idle and is still slow.

### p95, and why averages lie

An average tells you about a request nobody made. The SRE book's own example: a service averaging 100 ms at 1,000 requests/second can have 1% of requests taking 5 seconds — 10 users per second having a terrible time, invisible in the mean.

**p95 = 95% of requests were at least this fast; the slowest 5% were worse.** Read it as "the experience of your unluckiest one-in-twenty users". Quote p95 for budgets and p99 for capacity planning. k6 writes thresholds in exactly this shape — `http_req_duration: ['p(95)<300']` ([k6 thresholds](https://grafana.com/docs/k6/latest/using-k6/thresholds/)).

Rule: **every performance number in this repo carries a unit and a percentile.** "Fast" is not a measurement. "p95 < 300 ms on the list endpoint at 50 VUs" is.

### Minimum instrumentation, per layer

You need all four before week 2. None of them takes an afternoon.

| Layer | Turn on first | What it exposes |
|---|---|---|
| API | Per-route request metrics (`http.server.requests` in Spring/Micrometer, `prom-client` histogram in Node, `prometheus_client` in Python, `promhttp` in Go) scraped by Prometheus, drawn in Grafana | p95 by route, error rate, traffic |
| Database | Slow-query log on (start at 200 ms), ORM SQL logging in dev, `EXPLAIN (ANALYZE, BUFFERS)` on every new query | N+1, sequential scans, rows examined vs returned |
| Web | Lighthouse locally (`npx lighthouse <url> --only-categories=performance`), field Core Web Vitals from real users | LCP, INP, CLS, JS bytes shipped |
| Mobile | Profile mode on a **physical device** plus the frame overlay | Frames over budget, jank location |

Add an error tracker and structured JSON logs with a correlation id, so a slow trace and its exception are the same story. Do not expose your metrics endpoint publicly and never wildcard the exposed set.

---

## 3. Performance budgets

A budget is not a wish. **A budget is a number in a file in the repo, checked by CI.** If no job fails when the number is exceeded, you have a comment, not a budget. See [performance budgets 101](https://web.dev/articles/performance-budgets-101) for the taxonomy — quantity budgets (bytes, requests) are the cheap starting point, user-centric timings are what you graduate to.

| Signal | Budget | Where measured | Gate |
|---|---|---|---|
| API p95 latency (read) | < 300 ms | k6 / Gatling against staging | CI threshold |
| API p95 latency (write) | < 500 ms | same | CI threshold |
| Error rate under load | < 1% | same | CI threshold |
| DB: rows examined per row returned | < 10 (from `EXPLAIN ANALYZE`) | PR review | reviewer |
| LCP / INP / CLS (p75) | <= 2.5 s / <= 200 ms / <= 0.1 | Lighthouse CI, field RUM | CI assertion |
| JS shipped on first route | < 200 KB gzip (set your own) | Lighthouse `resource-summary` or a bundle analyzer | CI assertion |
| Mobile frame time | < 16 ms (60 Hz) / < 8 ms (120 Hz) | DevTools / integration test timeline | manual + integration test |
| App size delta per PR | < +500 KB unless justified | release build size analysis | reviewer |

Sources: the web numbers are [Core Web Vitals](https://web.dev/articles/vitals) — LCP <= 2.5 s, INP <= 200 ms, CLS <= 0.1, all judged **at p75 of page loads**, and FID is retired. The API latency rows are our practical defaults: a starting point, tuned to your product, not a law.

### RAIL: the budget behind the budget

[RAIL](https://web.dev/articles/rail) gives you the human thresholds any interactive product is judged against:

| Phase | Budget | Meaning |
|---|---|---|
| Response | 100 ms | Handle an input inside 100 ms or the tap feels broken |
| Animation | 10 ms per frame | The frame budget is ~16 ms; the browser needs the rest |
| Idle | 50 ms chunks | Split background work so input is never blocked |
| Load | 5 s | Interactive within 5 s on a mid-tier device and network |

Write your chosen numbers into one file — `perf-budgets.md` at the repo root is enough — and have the k6 thresholds and Lighthouse assertions carry the same values. They live in two places; a reviewer keeps them equal.

---

## 4. Hygiene in code: two pairs you will write this week

Pseudocode, because the mistake is language-independent.

**Pagination.** Never hand a caller an unbounded collection.

```text
BAD
rows   = repo.findAll()                  // 100 rows in dev, 1.2M in year two
active = rows.filter(r => r.status == "ACTIVE")
return active                            // memory grows with the table
```

```text
GOOD
size   = min(requestedSize, 100)         // clamp in the controller, always
page   = repo.findByStatus("ACTIVE", page, size)   // WHERE in the database
return { items: page.items, page, size, total: page.total }
```

The opt-out is allowed exactly once: when the bound is explicit in the code (`LIMIT 50`) and a comment names the maximum cardinality. "The table is small" is not a bound; it is a prediction about a table you do not control.

**Query inside a loop.** The N+1 you will not see until the SQL log is on.

```text
BAD
orders = repo.findOrders(page)           // 1 query
for o in orders:
    o.items = repo.findItems(o.id)       // + 1 query per row -> 21 queries per page
```

```text
GOOD
orders = repo.findOrders(page)                        // 1 query
items  = repo.findItemsForOrders(idsOf(orders))       // 1 query, WHERE order_id IN (...)
attach(orders, groupBy(items, "orderId"))             // join in memory, bounded by the page
```

Two cheap extras while you are in there: mark read paths read-only in your ORM (`@Transactional(readOnly = true)` and its equivalents) — it is a free hint and a correctness guard — and push aggregation into the query.

> A dashboard endpoint loaded twelve months of rows to compute four numbers. The fix was not a cache; it was `COUNT` and `SUM` in the query, then a continuous aggregate when the table hit tens of millions of rows. Cache came third, with a 5-minute TTL.

### Three 12-factor rules that are performance rules

From [12factor.net](https://12factor.net/), read through a latency lens.

| Factor | Performance consequence |
|---|---|
| VI. Processes are stateless | You can add an instance under load. In-process caches are allowed only for data that may vanish at any moment and is size-bounded; session state never lives in the process |
| VIII. Concurrency via the process model | Scale horizontally before you tune a single process. A second instance is usually cheaper than a week of GC flags |
| IX. Disposability — fast startup, graceful shutdown | Slow startup makes autoscaling useless and deploys scary; ignoring SIGTERM turns every deploy into a burst of user-visible errors |

---

## 5. The eight ways an AI silently writes slow code

The model writes locally-correct code. It cannot see your SQL log, your bundle, or your device. These eight are the ones we keep catching in diffs.

| # | What it does by default | Prompt that causes it | Review question that catches it |
|---|---|---|---|
| F1 | N+1 hidden in a generated loop (`for (o : orders) o.getItems().size()`, `await repo.find(id)` inside `map`) | "Return each order with its items" | "How many statements does this path execute for a page of 20?" |
| F2 | `findAll()` / `SELECT *` / `.find({})` with no page | "List all users" | "What is the maximum number of rows this can return?" |
| F3 | Unbounded in-memory collections (`findAll().stream().filter()`, whole dataset in component state, `.map().toList()` into a non-lazy list widget) | "Filter the active ones" | "Where does this filter run — the database or the heap?" |
| F4 | Sync I/O on the hot path: blocking call in a handler with no timeout, `readFileSync` in a request, network call inside a UI build | "Fetch the profile before rendering" | "What is the timeout, and what happens when the dependency hangs?" |
| F5 | Missing indexes — the migration creates the table and the FK, no index | "Add a migration for the orders table" | "Which index serves the WHERE/JOIN/ORDER BY of the query in this same PR?" |
| F6 | Premature micro-optimization when you say "performant": caching everywhere, memoizing every component, custom pools | "Write a performant version of this" | "What did you measure before adding this? Show the before and after number" |
| F7 | Claims with no evidence: "now O(1)", "production-ready, < 100 ms" | "Make it fast and production-ready" | "Which command produced that number? Paste its output" |
| F8 | Fetching the world to render a summary (12 months of rows to show a count) | "Show total revenue this year on the dashboard" | "Why is this aggregation happening in the application instead of the database?" |

> A delivery report generated by an AI agent on one of our projects listed "< 100 ms response SLA (< 50 ms typical)" as a shipped feature. Four lines below, under "next steps", it listed "load testing (verify SLAs)". The number was a hope, not a measurement.

That scar is F7 in its natural habitat, and it is why the acceptance rule in the next section exists.

---

## 6. How to ask an AI for performant code

Good prompts are context first, surgical scope, explicit negative constraints, and success criteria you can check. Applied to performance, that is this block — keep it in a snippet manager and paste it.

```text
Context: <stack, expected row/user volume in 2 years, current p95 if known>.
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

The negative constraints are load-bearing. Without "do NOT add caching", "performant" is read as "add optimizations", and you get F6 in a diff you now have to review.

### Asking the AI to check its own code

The second prompt is the one most people never send. Run it before you read the diff.

```text
Verify what you just wrote, one item at a time:
1. Show the SQL for this path. Paste the log lines, not a summary of them.
2. Count the DB statements executed by the test for this endpoint and print the count.
3. Run the k6 smoke against the local server and paste the k6 summary block.
4. Run `npx lighthouse <url> --only-categories=performance` and paste LCP, TBT, CLS.
5. For every number above, name the command that produced it.
   If you did not run it, write "unmeasured" next to it. Do not estimate.
```

**Acceptance rule: no number, no merge.** A performance claim in a PR description is either accompanied by the command and its output, or it is deleted from the description before review. This applies to your own claims too.

Heavy static-analysis platforms are optional here — in AI-driven repos we do not run them, and none of the gates above needs one. Free, single-file and fast beats a server nobody maintains.

---

## 7. Same idea in Java / Node / Python / Go

| Concern | Java (Spring Boot) | Node/TypeScript | Python | Go |
|---|---|---|---|---|
| Pagination idiom | `Page<T> findAll(Pageable)` + `PageRequest.of(page, size)` | ORM `take`/`skip` or `LIMIT`/`OFFSET` | Django `Paginator`; SQLAlchemy `.limit().offset()` | `LIMIT $1 OFFSET $2` in the query |
| N+1 detector | `hibernate.generate_statistics=true` + statement count in a test | Prisma `log: ['query']`; `DEBUG=knex:query` | `django-debug-toolbar`; `nplusone` | Query logging on the driver/pool [check for your driver] |
| Profiler | JFR (`-XX:StartFlightRecording`); async-profiler | `node --cpu-prof` | `cProfile`; `py-spy` | `net/http/pprof` |
| Load tool | k6; Gatling (Java DSL, assertions fail the build) | k6 | k6; Locust | k6; `hey` |
| Metrics library | Micrometer + Actuator | `prom-client` | `prometheus_client` | `promhttp` |

Keyset pagination (`WHERE id > :last ORDER BY id LIMIT :n`) beats offset pagination on large tables in every one of those columns — offset makes the database walk and discard the rows you skipped.

---

## 8. Day 1 / Week 1 — greenfield

You have no data yet, which is exactly why this is cheap. Everything here is hygiene; none of it requires a measurement to justify.

| When | Do | Done when |
|---|---|---|
| Day 1 | Turn on ORM SQL logging in the dev profile | You can see every statement your first endpoint issues |
| Day 1 | Expose per-route request metrics and scrape them | p95 per route is a graph, not a guess |
| Day 1 | Write `perf-budgets.md` with the section 3 table, your numbers | The file exists and is committed |
| Day 1 | Paste the section 6 prompt block into your AI instruction file | The agent reads the constraints before writing code |
| Day 1 | Add the review question to the PR template: "Query in a loop? Load without pagination? Objects piling up in memory?" | Every PR asks it |
| Week 1 | k6 smoke in CI: 5 VUs, 30 s, thresholds `p(95)<300` and `rate<0.01` | A pushed regression fails the job |
| Week 1 | Lighthouse CI on the main route with LCP/CLS/TBT assertions | The build fails when the bundle balloons |
| Week 1 | PR rule: every new query ships with `EXPLAIN (ANALYZE, BUFFERS)` output and its index | A reviewer can refuse without arguing |
| Week 1 | Install the anti-pattern grep hook so it runs on every edit | F2/F3 die seconds after they are written |

Wiring the hook and the CI jobs is the enforcement layer — configs live in [enforcement/README.md](./enforcement/README.md), not in this guide.

---

## 9. Day 1 / Week 1 — legacy

Do not start with a profiler and do not start with a list of everything wrong. Start with the thing users complain about.

| When | Do | Done when |
|---|---|---|
| Day 1 | Pick **one** endpoint or screen users actually complain about | It is named in writing, with the complaint |
| Day 1 | Measure it as it is today: p95 under a realistic load, or LCP on the real route | You have a number with a unit and a percentile |
| Day 1 | Write that number in `perf-budgets.md` under "baseline, <date>" | Future-you can prove the change helped |
| Day 1 | Turn on the slow-query log (200 ms) and dev SQL logging | The top offenders show up by lunch |
| Day 1 | Grep the repo for unbounded loads: `findAll(`, `.objects.all()`, `.find({})`, `SELECT *`, a repository call inside `for`/`map`/`forEach` | You have a list, ranked by table size |
| Week 1 | Fix the top 3 **by user impact**, not by how ugly the code is | Each fix has a before/after number from the same command |
| Week 1 | For each fix, add the threshold that would have caught it | The regression cannot come back silently |
| Week 1 | Install the grep hook and put the prompt block in the AI instruction file | New code stops adding to the list |
| Week 1 | Leave everything else alone and write it in a backlog file | Scope stays honest |

Three fixes with numbers beat thirty without. The backlog file is what stops the fourth week from becoming a rewrite.

---

## 10. Anti-patterns you will be tempted by

- **Caching before measuring.** A cache is a correctness liability you accept in exchange for a measured win. With no baseline you get the liability and an unknown. And if you do cache: no TTL, no cache.
- **"Make it async" with no queue.** Moving work off the request thread without a bounded executor, a retry policy and a dead-letter destination does not remove the work; it removes your visibility of it. Async is the fix only after the requirement is a number.
- **Unbounded pools.** Unlimited threads, unlimited connections, unlimited in-memory caches. Every pool gets a maximum, and saturation of that maximum is a graph you watch. More connections than the database can serve is slower, not faster.
- **Microservices as a performance fix.** Our default is a modular monolith; split into services when a **measured** requirement demands it, not when the diagram looks nicer. Splitting a slow query across a network adds a network to a slow query.
- **Runtime and GC flags before query fixes.** JVM flags, worker counts and heap sizes are the last row of the optimization table. The database is almost always the answer, and a missing index is worth more than every flag combined.
- **Disabling pagination "just for the export".** The export is precisely the path that hits the whole table. Exports go to a background job that streams or pages; they never call the unbounded finder "because it is a report".

The counter-example, so this does not read as "never go async":

> In one of our projects, a click-tracking endpoint had a hard requirement of under 50 ms. The design that met it was not a faster monolith: it was an in-memory store answering synchronously (about 5 ms), a queue behind it, and a time-series database writing in 5-second batches. Async was the fix, but only after the requirement was a number.

---

## Sources & further reading

- Google SRE Book, "Monitoring Distributed Systems" — the four golden signals, and why means hide the tail: https://sre.google/sre-book/monitoring-distributed-systems/
- web.dev, "Core Web Vitals" — LCP <= 2.5 s, INP <= 200 ms, CLS <= 0.1 at p75: https://web.dev/articles/vitals
- web.dev, "Measure performance with the RAIL model" — 100 ms / 10 ms / 50 ms / 5 s: https://web.dev/articles/rail
- web.dev, "Performance budgets 101" — quantity, milestone and rule-based budgets: https://web.dev/articles/performance-budgets-101
- Grafana k6, "Thresholds" — percentile expressions and non-zero exit as a CI gate: https://grafana.com/docs/k6/latest/using-k6/thresholds/
- Brendan Gregg, "The USE Method" — Utilization, Saturation, Errors per resource: https://www.brendangregg.com/usemethod.html
- The Twelve-Factor App — factors VI, VIII and IX read as performance rules: https://12factor.net/
- Brendan Gregg, *Systems Performance*, 2nd ed. — the reference for the methodology behind all of the above.

## Related

- [backend-performance-guide.md](./backend-performance-guide.md) — the database as the main character: N+1, indexes, `EXPLAIN`, pools, caching ladder, load tests
- [frontend-performance-guide.md](./frontend-performance-guide.md) — Core Web Vitals, bundle budgets, render discipline, Lighthouse CI
- [mobile-performance-guide.md](./mobile-performance-guide.md) — frame budget, list and image discipline, app size, device profiling
- [enforcement/README.md](./enforcement/README.md) — turning these recommendations into instructions, hooks and CI gates
- [../../skills/perf-engineer/SKILL.md](../../skills/perf-engineer/SKILL.md) — the agent skill that applies all of the above
- [../testing/testing-from-zero.md](../testing/testing-from-zero.md) — the same first-day/first-week treatment for automated tests

_Last reviewed: 2026-09-07._
