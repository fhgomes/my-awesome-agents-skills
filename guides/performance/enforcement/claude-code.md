# Performance Enforcement — Claude Code

**Best used when:** "make it fast" keeps coming back from Claude Code as `@Cacheable` on everything with a `findAll()` underneath.
**Read before:** editing `CLAUDE.md` or `.claude/settings.json` for performance rules.
**See also:** [README.md](./README.md) · [hooks/perf-post-edit-hook.sh](./hooks/perf-post-edit-hook.sh) · [../performance-from-zero.md](../performance-from-zero.md)

Two layers here: the instruction file (Claude reads it) and the hooks (Claude gets no vote). CI is layer 3, identical for every tool.

## 1. What this tool reads

| Path | Scope |
|---|---|
| `./CLAUDE.md` or `./.claude/CLAUDE.md` | The project, checked in |
| `.claude/rules/*.md` | Path-scoped rules: a `paths:` frontmatter list of globs makes the file load only when Claude works on matching files |
| `~/.claude/CLAUDE.md` | Every project you open |
| `.claude/settings.json` | Hooks, checked in |

Claude Code reads `CLAUDE.md`, not `AGENTS.md`. If `AGENTS.md` is your canonical file (it is for Codex, Cursor, Copilot and Cline), do not duplicate the block — import it:

```markdown
# CLAUDE.md
@AGENTS.md
```

<!-- Verified against https://code.claude.com/docs/en/memory on 2026-09-07: "Claude Code reads CLAUDE.md, not AGENTS.md" — the @AGENTS.md import, the ln -s AGENTS.md CLAUDE.md alternative, and .claude/rules/*.md with a paths: frontmatter are all documented there -->

The same page is blunt about what layer 1 is: CLAUDE.md files are "context, not enforced configuration. To block an action regardless of what Claude decides, use a PreToolUse hook." That sentence is why section 3 exists.

## 2. The instruction block

Paste into `CLAUDE.md` — or into `AGENTS.md` if you use the import above. To keep it out of the way while Claude edits docs, put it in `.claude/rules/performance.md` with `paths: ["src/**/*.{java,kt,ts,tsx,dart}"]` at the top instead.

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

Keep `CLAUDE.md` under ~200 lines in total. Past that it stops being read carefully, and this block is not the only thing in it.

## 3. Hooks

`.claude/settings.json`, checked in. `.claude/settings.local.json` is the personal override.

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/perf-post-edit-hook.sh",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
```

<!-- Verified against https://code.claude.com/docs/en/hooks on 2026-09-07 -->

Install, then prove it fires without waiting for Claude:

```bash
mkdir -p .claude/hooks
cp guides/performance/enforcement/hooks/perf-*.sh .claude/hooks/ && chmod +x .claude/hooks/*.sh
echo '{"tool_input":{"file_path":"src/Foo.java"}}' | bash .claude/hooks/perf-post-edit-hook.sh
```

| Contract | Value |
|---|---|
| Stdin | JSON with `session_id`, `cwd`, `hook_event_name`, `tool_name`, `tool_input` (`tool_input.file_path` for Edit/Write), `tool_use_id` |
| Exit 0 | Proceed |
| Exit 2 | **Block** on a blocking event (`PreToolUse`, `Stop`, …); stderr is the reason Claude reads. On `PostToolUse` the tool has already run, so exit 2 does not block — it only shows stderr to Claude |
| `timeout` | Seconds |
| Env | `${CLAUDE_PROJECT_DIR}` expands to the repo root — hooks do not run from a predictable cwd |
| JSON alternative | `{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"..."}}` |

<!-- Verified against https://code.claude.com/docs/en/hooks on 2026-09-07 -->

Optional blocking gate at the end of a turn — the checklist over the working diff, refusing "done" while findings stand:

```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "PERF_HOOK_BLOCK=1 ${CLAUDE_PROJECT_DIR}/.claude/hooks/perf-post-edit-hook.sh",
            "timeout": 60
          }
        ]
      }
    ]
  }
}
```

<!-- Verified against https://code.claude.com/docs/en/hooks on 2026-09-07 -->

With `PERF_HOOK_BLOCK=1` the script exits 2 and its stderr — the file:line findings — goes back to Claude as the reason to keep working. With no file in the payload the script scans the whole working tree, untracked files included, so a file Claude created this turn is not missed. Two cautions: the gate re-fires on every stop until the findings are gone (Claude Code sets `stop_hook_active: true` on those re-fires and caps consecutive forced continuations at 8, so the loop is bounded — the same field the testing area's stop gate uses to yield after one block), so a false positive needs a `perf:ok <reason>` on the line before Claude can finish; and start with `PostToolUse` only, adding the `Stop` gate after a week of clean report-only runs.

## 4. CI

Same for every tool: [hooks/github-actions-perf.yml](./hooks/github-actions-perf.yml) — Lighthouse assertions, the k6 threshold job, and the checklist replayed over the PR diff with `PERF_HOOK_BLOCK=1`. That last job is what catches the commit made with `--no-verify` and the teammate who never installed a hook.

## 5. Tool-specific notes

- **Ask for the number, in the same turn.** "Run `k6 run --env BASE_URL=http://localhost:8080 perf/k6-smoke.js` and paste the summary block, including `http_req_duration p(95)`." Claude Code can run it; without the instruction it will describe what the run would show.
- Same for SQL: "Set `logging.level.org.hibernate.SQL=DEBUG`, hit the endpoint once, paste how many statements were logged." A statement count is the cheapest N+1 detector there is.
- Hooks fire for Claude Code only. The same repo edited in Cursor or by a Copilot cloud agent gets nothing from `.claude/settings.json` — that is why layer 3 exists.
- A hook that takes 30 seconds gets uninstalled. The checklist greps one file, so it stays in milliseconds; never put a build or a load test in a `PostToolUse` hook.

## Sources & further reading

- Claude Code hooks (events, stdin, exit codes, `${CLAUDE_PROJECT_DIR}`) — https://code.claude.com/docs/en/hooks
- k6 thresholds — https://grafana.com/docs/k6/latest/using-k6/thresholds/

## Related

- [README.md](./README.md) — the three layers, the minimum set, the budget file · [hooks/README.md](./hooks/README.md) — patterns, suppression, fixtures
- [../backend-performance-guide.md](../backend-performance-guide.md) · [../frontend-performance-guide.md](../frontend-performance-guide.md)

_Last reviewed: 2026-09-07._
