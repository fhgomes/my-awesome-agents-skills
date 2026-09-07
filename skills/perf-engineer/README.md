# Perf Engineer — Measure Before You Claim

**SKILL.md** — drop-in skill for any runtime that loads a SKILL.md.

## What it does

Turns "make it faster" into a measurement, a fix and a threshold instead of an opinion:

- Open the SQL log, the profiler or the Lighthouse run **before** the code. Every performance
  statement carries the command and its output, or the literal word `unmeasured`.
- Separate structural hygiene (pagination, indexes, no query in a loop, TTL on every cache key,
  timeouts, lazy lists — always) from optimization (caching, memoization, pool and GC tuning — only
  after a measurement names the hotspot).
- Reject unmeasured claims, its own included: "production-ready", "O(1)", "sub-100 ms" are not results until a command and its output are pasted.
- Grep AI-written diffs for the eight failure modes that keep coming back — `findAll()` without a
  page, `findAll().stream().filter()`, repository calls inside loops, migrations with no index,
  `React.memo` with no profile, claims with no evidence.
- Prioritize by user impact — timeouts and unbounded growth before micro-optimizations — and never
  run a load test against production or a third party without explicit authorization.

**Domains:** database and JPA (N+1, pagination, indexes, `EXPLAIN`); API and concurrency (timeouts,
virtual threads vs job queues, bounded pools, HikariCP); caching (the no-cache -> headers ->
in-process -> Redis ladder, TTL on every key); JVM (heap sizing, JFR, dumps before flags); web
frontend (Core Web Vitals, bundle budgets, render discipline, Lighthouse CI); mobile (build
discipline, lazy lists, images, frame budget, app size).

## What's inside

- `SKILL.md` — identity, five operating principles, the standard response format (Diagnosis /
  Evidence / Fix / Verification / Budget), the F1-F8 grep table, a verified command table for
  measuring each layer, domains A-F, and the ethics limits.
- `references/checklists.md` — backend, frontend and mobile review lists, the budget table, and
  Day 1 / Week 1 plans for a new project and for an existing one with no performance practice.

This folder is **self-contained** — copy it into any runtime that loads a SKILL.md (Claude,
OpenClaw, custom agents) and it works as-is. No other part of this repository is required.

## See also (optional)

Longer-form material lives in [../../guides/performance/](../../guides/performance/) — from-zero,
backend, frontend and mobile guides, plus an `enforcement/` folder for instruction files, hooks and
CI gates. Alternative reading, not a prerequisite.

## Trigger keywords

`slow endpoint`, `latency`, `p95`, `N+1`, `pagination`, `index`, `EXPLAIN`, `connection pool`, `HikariCP`, `cache`, `TTL`, `Redis`, `Caffeine`, `GC`, `heap`, `OOM`, `k6`, `Gatling`, `JMeter`,
`Lighthouse`, `Core Web Vitals`, `LCP`, `INP`, `CLS`, `bundle size`, `re-render`, `TanStack Query`,
`jank`, `frame drop`, `Flutter DevTools`, `app size`, "make it faster", "will this scale", "is this performant".

_Last reviewed: 2026-09-07._
