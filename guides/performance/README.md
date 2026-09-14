# Performance Guides

**Best used when:** your project has no performance practice — no budget, no load test, no SQL log, no frame number — and you want the first day and the first week that pay off, whether you or an AI coding tool types the code.
**Read before:** accepting a "production-ready, sub-100 ms" claim from anyone, human or model, that arrives without the command that produced it.
**See also:** [../testing/](../testing/) (the same treatment for automated tests) · [../../skills/perf-engineer/SKILL.md](../../skills/perf-engineer/SKILL.md) (the agent skill)

One review question seeds this whole area: **"Can this change hurt performance? A query inside a loop, a load without pagination, objects piling up in memory."** One rule keeps it from turning into a week of guesswork: **maintainable > fast — optimize only when measured.** Every file here separates the two so they stop contradicting each other:

| Category | When | Examples |
|---|---|---|
| **Structural hygiene** | Always, in review, no measurement needed | Pagination on every list (max size 100); an index on every FK and every filtered/sorted column, in the same migration; no query inside a loop; lazy lists; TTL on every cache key; bounded pools; a timeout on every outbound call |
| **Optimization** | Only after a measurement names the hotspot | Caching; memoization; pool and GC tuning; `RepaintBoundary`; batch sizes |

Every file is self-contained — open one and act on it; the links are see-also, never prerequisites.

## Start here

| You are | Read | Then do, today |
|---|---|---|
| **Greenfield** — new repo, no data yet | [performance-from-zero.md](./performance-from-zero.md) section 8, then the section 14/11/12 "Greenfield" table of your stack guide | Turn on SQL logging in dev, expose per-route request metrics, write `perf-budgets.md` with the budget table, paste the prompt block into your AI instruction file. Week 1: a k6 smoke and a Lighthouse CI assertion in the pipeline |
| **Legacy** — existing app, nothing measured | [performance-from-zero.md](./performance-from-zero.md) section 9, then the "Legacy" table of your stack guide | Pick the one endpoint or screen users complain about, measure it, write the number down with the date. Grep for `findAll(`, `.objects.all()`, `SELECT *`, `ListView(children:`. Week 1: fix the top three by user impact, each with a before/after number, and add the threshold that would have caught it |
| **"I use an AI tool and want it to measure, not narrate"** | [performance-from-zero.md](./performance-from-zero.md) sections 5-6, then [enforcement/README.md](./enforcement/README.md) | Put the canonical instruction block in `AGENTS.md`/`CLAUDE.md`, install the grep hook for your tool, copy the CI workflow. Acceptance rule: no number, no merge — a claimed latency comes with the command and its output or it is deleted from the PR |

Stack guides: [backend](./backend-performance-guide.md) (Spring Boot + PostgreSQL), [frontend](./frontend-performance-guide.md) (React + Vite), [mobile](./mobile-performance-guide.md) (Flutter). Each has a "same idea in Node / Python / Go" (or Next / Vue / Angular, or React Native) table.

## Files

| File | What it is |
|---|---|
| [performance-from-zero.md](./performance-from-zero.md) | Language-agnostic entry point: measure first (golden signals, p95), budgets (RAIL, Core Web Vitals), hygiene vs optimization, the eight ways an AI silently writes slow code, how to prompt for and verify performant code, Day 1 / Week 1 for greenfield and legacy |
| [backend-performance-guide.md](./backend-performance-guide.md) | Java/Spring Boot with the database as the main character: see the SQL, N+1 and JPA, pagination, indexes and `EXPLAIN (ANALYZE, BUFFERS)`, HikariCP, the caching ladder, async vs virtual threads, JVM basics, Actuator/Prometheus, k6 and Gatling as CI gates, review checklist |
| [frontend-performance-guide.md](./frontend-performance-guide.md) | React/TypeScript on Vite: Core Web Vitals (lab vs field), bundle budgets, code splitting, render discipline before `memo`, TanStack Query as the client-side TTL, network rules, Lighthouse CI, Playwright as a perf probe, review checklist |
| [mobile-performance-guide.md](./mobile-performance-guide.md) | Flutter: profile mode on a real device, `build()` discipline, `ListView.builder`, image decode caps, the expensive widgets you do not see, isolates, app size, startup, automated frame tests, review checklist, React Native notes |
| [enforcement/README.md](./enforcement/README.md) | The three layers (instructions, hooks, CI), what to enforce, what each AI tool can actually do, the canonical instruction block, the provider-agnostic recipe, the budget file |
| [enforcement/claude-code.md](./enforcement/claude-code.md) | `CLAUDE.md` / `@AGENTS.md` import, `.claude/rules/`, `PostToolUse` and `Stop` hooks in `.claude/settings.json` |
| [enforcement/codex.md](./enforcement/codex.md) | `AGENTS.md` discovery and the 32 KiB cap, experimental `.codex/hooks.json` |
| [enforcement/gemini-cli.md](./enforcement/gemini-cli.md) | `GEMINI.md` or `context.fileName`, `AfterTool` hook with a millisecond timeout |
| [enforcement/copilot.md](./enforcement/copilot.md) | `.github/copilot-instructions.md`, `applyTo:` path rules, a code-review instruction file, `.github/hooks/` `postToolUse` |
| [enforcement/cursor-cline-aider.md](./enforcement/cursor-cline-aider.md) | `.cursor/rules/*.mdc` and `.cursor/hooks.json`, `.clinerules/`, `CONVENTIONS.md` and aider `--lint-cmd` |
| [enforcement/hooks/README.md](./enforcement/hooks/README.md) | Install matrix, the pattern table, the `perf:ok <reason>` suppression convention, try-it fixtures |
| [enforcement/hooks/perf-review-checklist.sh](./enforcement/hooks/perf-review-checklist.sh) | Greps a diff, the staged set or given files for the anti-pattern shapes (F1-F4); exit 2 in blocking mode |
| [enforcement/hooks/perf-post-edit-hook.sh](./enforcement/hooks/perf-post-edit-hook.sh) | Runs the checklist on the file an agent just edited; wired by every tool's hook config |
| [enforcement/hooks/lighthouserc.json](./enforcement/hooks/lighthouserc.json) | Lighthouse CI assertions: performance >= 0.9, LCP <= 2.5 s, CLS <= 0.1, TBT warn at 300 ms, first-route JS <= 200 KB |
| [enforcement/hooks/k6-smoke.js](./enforcement/hooks/k6-smoke.js) | 5 VUs for 30 s, `p(95)<300` and `rate<0.01`; a failed threshold exits non-zero |
| [enforcement/hooks/github-actions-perf.yml](./enforcement/hooks/github-actions-perf.yml) | Three CI jobs — Lighthouse, k6, the checklist over the PR diff — to mark as required checks |

## Recommendations vs enforcement

The guides (`*.md` here) recommend and explain — they argue for each rule with a scar or a cited source, and they never embed a hook config. `enforcement/` makes the rules mandatory — instruction blocks, hooks and CI gates, with every AI-tool config block either verified against the vendor's docs on a stated date or marked `[unverified — check your tool's docs]`. Read a guide to decide; copy from `enforcement/` to make the decision stick.

## The skill

[../../skills/perf-engineer/](../../skills/perf-engineer/) is a drop-in agent skill (`SKILL.md` + `references/checklists.md`) that reviews diffs for the same failure modes, answers in a fixed Diagnosis / Evidence / Fix / Verification / Budget shape, and refuses to state a number it did not measure. It is self-contained: install it without this folder, or read this folder without installing it.

_Last reviewed: 2026-09-07._
