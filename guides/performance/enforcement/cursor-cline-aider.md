# Performance Enforcement — Cursor, Cline, aider

**Best used when:** the repo is edited from Cursor, from Cline in VS Code, or from aider on the terminal — including aider driving a non-Anthropic model.
**Read before:** writing `.cursor/rules/`, `.clinerules/` or `CONVENTIONS.md`.
**See also:** [README.md](./README.md) · [hooks/perf-post-edit-hook.sh](./hooks/perf-post-edit-hook.sh) · [../performance-from-zero.md](../performance-from-zero.md)

Three tools, one instruction block, three different files to put it in. Only Cursor has a hook system; for Cline and aider, layer 2 is a git hook and layer 3 is CI. The model behind the tool changes nothing here — a weaker model needs more enforcement, not less.

## 1. What each tool reads

| Tool | File | Notes |
|---|---|---|
| Cursor | `.cursor/rules/*.mdc` | Plain `.md` in that folder is ignored. Frontmatter: `description`, `globs`, `alwaysApply`. `AGENTS.md` is supported too (nested allowed); `.cursorrules` is legacy |
| Cline | `.clinerules/` **folder** at the repo root | Every `.md`/`.txt` inside is loaded. Also auto-detects `.cursorrules`, `.windsurfrules` and `AGENTS.md`. No hooks |
| aider | `CONVENTIONS.md` | Loaded with `aider --read CONVENTIONS.md` or via `.aider.conf.yml` |

<!-- Verified against https://cursor.com/docs/context/rules , https://docs.cline.bot/features/cline-rules and https://aider.chat/docs/usage/conventions.html on 2026-09-07 -->

## 2. The instruction block

The same text goes into all three files. Write it once, copy it three times — a symlink is fine on Linux and macOS and a trap on Windows checkouts.

```markdown
## Performance (non-negotiable)

Two categories. Hygiene is required always and needs no measurement.
Optimization happens only after a measurement names the hotspot.

Structural hygiene — apply without being asked:
1. Every list endpoint and every list query is paginated: `page` + `size`, size clamped
   to a maximum of 100. No `findAll()`, no `SELECT *`, no `.find({})` without a bound.
2. No DB or HTTP call inside a loop (`for`, `forEach`, `.map`, one `useEffect` per row).
   Batch it, join it, or fetch once before the loop.
3. Any column used in `WHERE`, `JOIN` or `ORDER BY` gets an index in the same migration
   as the query that needs it. Every foreign key gets a non-unique index.
4. Every outbound call (HTTP client, DB, queue) sets an explicit connect and read timeout.
5. Every cache key has a TTL. No TTL, no cache.
6. Long lists are lazy: `ListView.builder` in Flutter, a virtualized list on the web,
   a page or keyset query on the server. Never build every row up front.

Optimization — only when I ask, or after a measurement:
7. Do NOT add caching, `@Cacheable`, `React.memo`, `useMemo`, async execution or a thread
   pool unless I ask for it or a profile you ran shows that hotspot.
8. Never claim a latency, a throughput or a complexity you did not measure. Say
   "unmeasured", or paste the command you ran and its output.

Before you call a change done, show me the SQL generated for the main path (or the bundle
size, or the frame time) and the exact command you ran to get it.
```

## 3. Cursor

`.cursor/rules/performance.mdc` — the block above goes under the frontmatter:

```md
---
description: Performance rules for backend and frontend code
globs: src/**/*.java,src/**/*.ts,src/**/*.tsx
alwaysApply: false
---
<the instruction block from section 2>
```

<!-- Verified against https://cursor.com/docs/context/rules on 2026-09-07 -->

With `alwaysApply: false` the rule loads when a matching file is in play, which is what you want: the rule is present while the model writes the repository class, and absent while it edits the README. Set `alwaysApply: true` only for a short block you want in every request. If `AGENTS.md` is already your canonical file, Cursor reads it and you can skip the `.mdc` entirely.

Hooks — `.cursor/hooks.json` in the project (or `~/.cursor/hooks.json` for every project):

```json
{
  "version": 1,
  "hooks": {
    "afterFileEdit": [
      { "command": "./.cursor/hooks/perf-post-edit-hook.sh" }
    ]
  }
}
```

<!-- Verified against https://cursor.com/docs/agent/hooks on 2026-09-07 -->

Documented event names include `afterFileEdit`, `beforeReadFile`, `preToolUse`, `postToolUse`, `stop` and `sessionStart`/`sessionEnd`. Project hooks run from the project root, so the command path is relative to it.

```bash
mkdir -p .cursor/hooks
cp guides/performance/enforcement/hooks/perf-*.sh .cursor/hooks/ && chmod +x .cursor/hooks/*.sh
echo '{"tool_input":{"file_path":"src/Foo.java"}}' | bash .cursor/hooks/perf-post-edit-hook.sh
```

The payload key names Cursor sends were not verified for this file; the hook script reads `tool_input.file_path`, falls back to `tool_input.path`, and falls back again to `git diff --name-only`, so it scans the right thing either way.

## 4. Cline

`.clinerules/` is a folder, not a file. Put the block in `.clinerules/performance.md` and nothing else in it — every file in the folder is loaded, so one topic per file keeps them all short.

<!-- Verified against https://docs.cline.bot/features/cline-rules on 2026-09-07 -->

Cline has no hook system. Install the git hook from [README.md](./README.md) section 5(b) and rely on the CI checklist job.

## 5. aider

Put the block in `CONVENTIONS.md` at the repo root and load it read-only:

```bash
aider --read CONVENTIONS.md
```

or in `.aider.conf.yml`:

```yaml
read: [CONVENTIONS.md]
```

<!-- Verified against https://aider.chat/docs/usage/conventions.html on 2026-09-07 -->

`--read` marks the file read-only so aider does not spend edits rewriting your own rules.

aider has no hook system either, but it does lint after edits, and the checklist can be that linter:

```bash
aider --lint-cmd "bash scripts/perf-review-checklist.sh --staged"
```

<!-- Verified against https://aider.chat/docs/usage/lint-test.html on 2026-09-07: --lint-cmd, --no-auto-lint, --test-cmd and --auto-test exist; aider lints files it modifies unless auto-lint is disabled -->

The equivalent `.aider.conf.yml` keys for `lint-cmd` are `[unverified — check your tool's docs]`; the CLI flag above is the shape that was verified. Note that aider tries to fix what a non-zero lint or test command reports, so run the checklist in report-only mode here (no `PERF_HOOK_BLOCK`) unless you want the model attempting a fix on every finding.

## 6. CI

Same for every tool: [hooks/github-actions-perf.yml](./hooks/github-actions-perf.yml) — Lighthouse assertions, the k6 threshold job, and the checklist over the PR diff with `PERF_HOOK_BLOCK=1`. For Cline and aider this is layer 3 doing the work of layers 2 and 3.

## Sources & further reading

- Cursor rules — https://cursor.com/docs/context/rules · Cursor hooks — https://cursor.com/docs/agent/hooks
- Cline rules — https://docs.cline.bot/features/cline-rules
- aider conventions — https://aider.chat/docs/usage/conventions.html · aider lint and test — https://aider.chat/docs/usage/lint-test.html
- The `AGENTS.md` cross-tool convention — https://agents.md/

## Related

- [README.md](./README.md) — the three layers, the minimum set, the budget file
- [hooks/README.md](./hooks/README.md) — patterns, suppression, try-it fixtures
- [../backend-performance-guide.md](../backend-performance-guide.md) · [../frontend-performance-guide.md](../frontend-performance-guide.md)

_Last reviewed: 2026-09-07._
