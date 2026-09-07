# Performance Enforcement — Gemini CLI

**Best used when:** Gemini CLI is writing code in the repo and you want the performance rules in its context file plus a hook that greps every write.
**Read before:** writing `GEMINI.md` or editing `.gemini/settings.json`.
**See also:** [README.md](./README.md) · [hooks/perf-post-edit-hook.sh](./hooks/perf-post-edit-hook.sh) · [../performance-from-zero.md](../performance-from-zero.md)

Gemini CLI has both layers: a hierarchical context file and a real hook system. One trap to remember before you copy anything — **its hook timeout is in milliseconds**, where Claude Code and Codex use seconds.

## 1. What this tool reads

| Path | Behaviour |
|---|---|
| `~/.gemini/GEMINI.md` | Global |
| `GEMINI.md` at the project root and in subdirectories | Concatenated, hierarchical |
| `.gemini/settings.json` -> `context.fileName` | Changes which filenames count as context |
| `@file.md` inside a context file | Imports that file |

If `AGENTS.md` is your canonical file, point Gemini at it instead of duplicating the block:

```json
{ "context": { "fileName": ["AGENTS.md", "GEMINI.md"] } }
```

<!-- Verified against https://geminicli.com/docs/cli/gemini-md/ on 2026-09-07 -->

## 2. The instruction block

Paste into `GEMINI.md` — or into `AGENTS.md` if you used the setting above.

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

A per-area split works well here because the context files are hierarchical: `backend/GEMINI.md` can carry rules 1-5 and `web/GEMINI.md` rules 6-8, with `@../PERFORMANCE.md` importing the shared block into both.

## 3. Hooks

`.gemini/settings.json` for the project, `~/.gemini/settings.json` for every project.

```json
{
  "hooks": {
    "AfterTool": [
      {
        "matcher": "write_file|replace",
        "hooks": [
          {
            "name": "perf-review",
            "type": "command",
            "command": "$GEMINI_PROJECT_DIR/.gemini/hooks/perf-post-edit-hook.sh",
            "timeout": 30000
          }
        ]
      }
    ]
  }
}
```

<!-- Verified against https://geminicli.com/docs/hooks/reference/ on 2026-09-07 -->

Install, then prove it fires:

```bash
mkdir -p .gemini/hooks
cp guides/performance/enforcement/hooks/perf-*.sh .gemini/hooks/ && chmod +x .gemini/hooks/*.sh
echo '{"tool_input":{"file_path":"src/Foo.java"}}' | bash .gemini/hooks/perf-post-edit-hook.sh
```

| Contract | Value |
|---|---|
| Events | `BeforeTool`, `AfterTool`, `BeforeAgent`, `AfterAgent`, `BeforeModel`, `AfterModel`, `SessionStart`, `SessionEnd`, others |
| Matcher | Regex against the tool name — `write_file`, `replace`, `run_shell_command`, … |
| Handler | `{ "name", "type": "command", "command", "timeout" }`, **timeout in milliseconds** |
| Stdin | `session_id`, `transcript_path`, `cwd`, `hook_event_name`, `timestamp`, plus `tool_name` and `tool_input` on tool events |
| Exit 2 | Blocks; stderr is the reason |
| Stdout JSON | May carry `decision` (`allow` / `deny` / `block`), `reason`, `systemMessage` |
| Env | `$GEMINI_PROJECT_DIR` expands to the project root |

<!-- Verified against https://geminicli.com/docs/hooks/reference/ on 2026-09-07 -->

`30000` is thirty seconds, not thirty milliseconds. A `30` there would kill the hook before `grep` finished and you would see an unexplained failure on every edit.

The hook script reads `tool_input.file_path` and falls back to `tool_input.path`; that second key was **not** verified for Gemini CLI, and if neither is present the script falls back to `git diff --name-only`, so it degrades to "scan what changed" rather than doing nothing.

## 4. CI

Same for every tool: [hooks/github-actions-perf.yml](./hooks/github-actions-perf.yml) — Lighthouse assertions, the k6 threshold job, and the checklist over the PR diff with `PERF_HOOK_BLOCK=1`.

## 5. Tool-specific notes

- Use `BeforeTool` instead of `AfterTool` only if you want to refuse the write itself. Refusing after the fact is usually enough and keeps the edit loop fast.
- Ask for the number explicitly: "Run `npx lighthouse http://localhost:5173 --only-categories=performance --quiet` and paste the performance score and LCP." Without that, you get prose.
- Settings files are per-project and per-user; a fresh clone has `GEMINI.md` and no hooks. The git `pre-commit` fallback in [README.md](./README.md) section 5(b) covers that gap.

## Sources & further reading

- Gemini CLI context files (`GEMINI.md`, `context.fileName`, imports) — https://geminicli.com/docs/cli/gemini-md/
- Gemini CLI hooks reference (events, matcher, timeout, exit codes) — https://geminicli.com/docs/hooks/reference/

## Related

- [README.md](./README.md) — the three layers, the minimum set, the budget file
- [hooks/README.md](./hooks/README.md) — patterns, suppression, try-it fixtures
- [../frontend-performance-guide.md](../frontend-performance-guide.md) · [../backend-performance-guide.md](../backend-performance-guide.md)

_Last reviewed: 2026-09-07._
