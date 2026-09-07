# Performance Enforcement — GitHub Copilot

**Best used when:** Copilot writes or reviews code in the repo — in the editor, as the cloud coding agent, from the CLI, or as an automated PR reviewer.
**Read before:** writing `.github/copilot-instructions.md`, a path-scoped instruction file, or `.github/hooks/`.
**See also:** [README.md](./README.md) · [hooks/perf-post-edit-hook.sh](./hooks/perf-post-edit-hook.sh) · [hooks/github-actions-perf.yml](./hooks/github-actions-perf.yml) · [../performance-from-zero.md](../performance-from-zero.md)

Copilot has all three layers, with a catch on layer 2: repository hooks in `.github/hooks/` fire for the coding agent and the CLI, not for chat completions in the editor. Editor suggestions get layer 1 and layer 3 only, so the git `pre-commit` fallback and the CI checklist job are not optional here.

## 1. What this tool reads

| Path | Scope |
|---|---|
| `.github/copilot-instructions.md` | The whole repository |
| `.github/instructions/<name>.instructions.md` | Files matching the `applyTo:` frontmatter glob — honored by the cloud coding agent and by Copilot code review; optional `excludeAgent` narrows that |
| `AGENTS.md` anywhere in the repo | Nearest one wins |
| `CLAUDE.md` / `GEMINI.md` at the root | Also read |

<!-- Verified against https://docs.github.com/en/copilot/how-tos/custom-instructions/adding-repository-custom-instructions-for-github-copilot on 2026-09-07 -->

## 2. The instruction block

Paste into `.github/copilot-instructions.md` (or `AGENTS.md`, which Copilot also reads).

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

## 3. Path-scoped rules

`.github/instructions/perf-backend.instructions.md`:

```md
---
applyTo: "**/*.java"
---
Every repository read that can return more than one row takes a `Pageable`; clamp `size` to 100
in the controller. Never `findAll()` from a service, and never `findAll().stream().filter(...)` —
filter in the query.
No repository call inside a `for` or a `stream` over entities: use `@EntityGraph` or `JOIN FETCH`.
Any column used in `WHERE`, `JOIN` or `ORDER BY` gets an index in the same migration; every FK
gets a non-unique index named `<table>_<column>_idx`.
`@Transactional(readOnly = true)` on read paths. Explicit timeouts on every `RestClient`/`WebClient`.
Every cache key has a TTL.
```

`.github/instructions/perf-frontend.instructions.md`:

```md
---
applyTo: "**/*.ts,**/*.tsx"
---
Paginated lists use the server's `page`/`size` contract; long lists are virtualized, never
`items.map(...)` into a single render pass.
One request per screen, not one per row: no `fetch` inside `.map(`, no `useEffect` per list item.
Server state goes through the query cache with an explicit `staleTime`; no `useEffect` + `useState`
fetching.
Do not add `React.memo`, `useMemo` or `useCallback` unless a React Profiler recording shows that
component re-rendering. State the recording when you add one.
No `readFileSync` / `execSync` on a request path.
```

<!-- Verified against https://docs.github.com/en/copilot/how-tos/custom-instructions/adding-repository-custom-instructions-for-github-copilot on 2026-09-07 -->

## 4. The code-review instruction

Copilot code review reads the same path-scoped files, so this is where you buy back some of the missing layer 2. `.github/instructions/perf-review.instructions.md`:

```md
---
applyTo: "**/*.{java,kt,ts,tsx,dart,py,go}"
---
When reviewing a diff, answer one question first: can this change hurt performance?
A query inside a loop, a load without pagination, objects piling up in memory.
Then check, and comment only when one fails:
- Unpaged read: `findAll(`, `SELECT *`, `.objects.all()`, `.find({})` with no bound.
- Query or HTTP call inside `for` / `forEach` / `.map` / `useEffect`.
- A new query whose `WHERE`/`JOIN`/`ORDER BY` columns have no index in this PR's migration.
- An outbound call with no timeout, or a cache key with no TTL.
- An eager list build where the framework has a lazy one.
- Caching, memoization or async added with no measurement quoted in the PR.
- Any latency, throughput or complexity claim with no command and output attached.
```

Any code change should come with a corresponding test change; the performance twin is that any new query should come with an `EXPLAIN (ANALYZE, BUFFERS)` in the PR. Put that line in the PR template — see [README.md](./README.md) section 5(d).

## 5. Hooks

`.github/hooks/*.json`, checked in. The coding agent reads only that location; the CLI also reads `~/.copilot/hooks/` and an inline `hooks` field in `.github/copilot/settings.json`.

```json
{
  "version": 1,
  "disableAllHooks": false,
  "hooks": {
    "postToolUse": [
      {
        "type": "command",
        "bash": ".github/hooks/perf-post-edit-hook.sh",
        "timeoutSec": 30
      }
    ]
  }
}
```

<!-- Verified against https://docs.github.com/en/copilot/reference/hooks-reference on 2026-09-07 -->

| Contract | Value |
|---|---|
| Events | `sessionStart`, `sessionEnd`, `userPromptSubmitted`, `preToolUse`, `postToolUse`, `postToolUseFailure`, `permissionRequest`, `preCompact`, `subagentStart`, `subagentStop`, `errorOccurred`, `notification`; `agentStop` for the user-level CLI only |
| Command handler | `type: "command"` with `bash` (or `powershell`, or cross-platform `command`), optional `cwd`, `env`, `timeoutSec` (seconds, default 30) |
| Stdin | `sessionId`, `timestamp`, `cwd`, `toolName`, `toolArgs`, and on `postToolUse` a `toolResult` |
| Exit 2 | Deny on `preToolUse`; a warning elsewhere. A timeout always fails open |
| Cloud agent | The hooks file must be on the **default branch** — a PR that adds the hook does not run under it |

<!-- Verified against https://docs.github.com/en/copilot/reference/hooks-reference on 2026-09-07 -->

The payload names its arguments `toolArgs`, not `tool_input`; the hook script reads `toolArgs.file_path` and `toolArgs.path` as fallbacks, but the key Copilot uses for the edited file's path was **not** verified. If neither resolves, the script scans the whole working tree, so it still reports — just less precisely.

```bash
mkdir -p .github/hooks scripts
cp guides/performance/enforcement/hooks/perf-review-checklist.sh scripts/
cp guides/performance/enforcement/hooks/perf-post-edit-hook.sh .github/hooks/ && chmod +x scripts/*.sh .github/hooks/*.sh
echo '{"toolName":"edit","toolArgs":{"path":"src/Foo.java"}}' | bash .github/hooks/perf-post-edit-hook.sh
```

`disableAllHooks: true` in any discovered hooks file turns the whole layer off. Grep for it in review.

For the editor, add the git hook, since chat completions never fire a repository hook:

```bash
# .git/hooks/pre-commit (chmod +x; keep the source under scripts/git-hooks/ so it is reviewable)
#!/usr/bin/env bash
exec scripts/perf-review-checklist.sh --staged
```

## 6. CI

[hooks/github-actions-perf.yml](./hooks/github-actions-perf.yml) runs Lighthouse assertions, the k6 threshold job, and the checklist over the PR diff with `PERF_HOOK_BLOCK=1`. Mark all three as required checks. For a PR the cloud agent opens from a branch nobody ran locally, this is the gate that counts.

## 7. Tool-specific notes

- Instruction and hook files must be on the branch the agent works from (hooks: the default branch). A rule added in a PR does not govern that same PR's cloud-agent run.
- `applyTo` globs are the cheapest way to keep each rule short. A backend rule that a frontend file never sees is a rule that stays read.
- Copilot in the editor is a completion engine on a partial file; it will suggest `findAll()` faster than you can read the instruction. The CI checklist job is what makes that a caught mistake instead of a shipped one.

## Sources & further reading

- Repository custom instructions and `applyTo` — https://docs.github.com/en/copilot/how-tos/custom-instructions/adding-repository-custom-instructions-for-github-copilot
- Copilot hooks reference (`.github/hooks/*.json`, events, `timeoutSec`, stdin) — https://docs.github.com/en/copilot/reference/hooks-reference
- The `AGENTS.md` cross-tool convention — https://agents.md/
- Lighthouse CI configuration — https://github.com/GoogleChrome/lighthouse-ci/blob/main/docs/configuration.md

## Related

- [README.md](./README.md) — the three layers, the minimum set, the budget file
- [hooks/README.md](./hooks/README.md) — patterns, suppression, try-it fixtures
- [../backend-performance-guide.md](../backend-performance-guide.md) · [../frontend-performance-guide.md](../frontend-performance-guide.md)

_Last reviewed: 2026-09-07._
