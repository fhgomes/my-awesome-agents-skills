# Performance Enforcement — OpenAI Codex

**Best used when:** Codex is the agent on the repo and you want the performance rules in the file it already reads, plus a hook if you are willing to run an experimental feature.
**Read before:** writing an `AGENTS.md` performance section or turning on Codex hooks.
**See also:** [README.md](./README.md) · [hooks/perf-post-edit-hook.sh](./hooks/perf-post-edit-hook.sh) · [../performance-from-zero.md](../performance-from-zero.md)

Codex reads `AGENTS.md` natively, which makes layer 1 free. Layer 2 exists but is experimental, so treat CI as the layer you actually rely on.

## 1. What this tool reads

| Path | Behaviour |
|---|---|
| `~/.codex/AGENTS.md` | Global, read first |
| `AGENTS.md` from the git root down to the working directory | Concatenated; the file closest to the code wins |
| `AGENTS.override.md` | Replaces `AGENTS.md` at the same level |
| `~/.codex/config.toml` -> `project_doc_max_bytes` | Caps the combined size, 32 KiB by default |

<!-- Verified against https://learn.chatgpt.com/docs/agent-configuration/agents-md on 2026-09-07 -->

The 32 KiB cap is a real constraint: an `AGENTS.md` that also carries architecture, style and testing sections has maybe a page of room for performance. Keep the block below whole and put the reasoning in the guides, where it belongs. If you need per-area rules, use a nested `AGENTS.md` — `backend/AGENTS.md` for the database rules, `web/AGENTS.md` for the bundle rules — rather than one long root file.

## 2. The instruction block

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

## 3. Hooks (experimental, opt in)

Codex hooks are **experimental, off by default, and not available on Windows**. Enable them in `config.toml`:

```toml
[features]
hooks = true
```

Then `<repo>/.codex/hooks.json` (or `~/.codex/hooks.json` for every project):

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "",
        "hooks": [
          { "type": "command", "command": "bash .codex/hooks/perf-post-edit-hook.sh", "timeout": 30 }
        ]
      }
    ]
  }
}
```

<!-- Verified against https://learn.chatgpt.com/docs/hooks on 2026-09-07 -->

**The matcher is left empty on purpose.** The exact tool names Codex reports for file edits were not verified for this file; an empty matcher matches every tool, and the hook script is cheap enough to run on all of them. If you confirm the edit tool names in the current docs, narrow it — a hook that runs on every shell command is noise you will eventually mute.

Install and test:

```bash
mkdir -p .codex/hooks
cp guides/performance/enforcement/hooks/perf-*.sh .codex/hooks/ && chmod +x .codex/hooks/*.sh
echo '{"tool_input":{"file_path":"src/Foo.java"}}' | bash .codex/hooks/perf-post-edit-hook.sh
```

| Contract | Value |
|---|---|
| Events | `PreToolUse`, `PostToolUse`, `UserPromptSubmit`, `Stop`, `SessionStart`, `SessionEnd`, others |
| Stdin | `session_id`, `cwd`, `hook_event_name`, `model`, `permission_mode`, plus `tool_name` and `tool_input` on tool events |
| Handler | `type: "command"`; `matcher` is a regex; `timeout` in **seconds** (default 600) |
| Block | Exit 2, or stdout `{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"..."}}` |
| Trust | Hooks that are not covered by the repo trust model require a trust review before they run |

<!-- Verified against https://learn.chatgpt.com/docs/hooks on 2026-09-07 -->

Because of the trust prompt and the Windows gap, assume a fresh clone runs no Codex hook at all. Add the git `pre-commit` fallback from [README.md](./README.md) section 5(b) so the check survives.

## 4. CI

Same for every tool: [hooks/github-actions-perf.yml](./hooks/github-actions-perf.yml) — Lighthouse assertions, the k6 threshold job, and the checklist over the PR diff with `PERF_HOOK_BLOCK=1`.

## 5. Tool-specific notes

- Nested `AGENTS.md` beats a long root file, both for the byte cap and for attention. Backend rules next to backend code get followed more often.
- Ask for the measurement explicitly: "Run `k6 run --env BASE_URL=http://localhost:8080 perf/k6-smoke.js` and paste the `http_req_duration` line." Without that sentence you get a summary of intent.
- `AGENTS.override.md` is useful for a spike branch where the rules are deliberately relaxed. Delete it before the PR, and say in the PR that you did.

## Sources & further reading

- Codex `AGENTS.md` discovery and `project_doc_max_bytes` — https://learn.chatgpt.com/docs/agent-configuration/agents-md
- Codex hooks (events, stdin, exit codes, trust) — https://learn.chatgpt.com/docs/hooks
- The `AGENTS.md` cross-tool convention — https://agents.md/

## Related

- [README.md](./README.md) — the three layers, the minimum set, the budget file
- [hooks/README.md](./hooks/README.md) — patterns, suppression, try-it fixtures
- [../backend-performance-guide.md](../backend-performance-guide.md) · [../frontend-performance-guide.md](../frontend-performance-guide.md)

_Last reviewed: 2026-09-07._
