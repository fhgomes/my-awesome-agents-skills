# Testing Enforcement — Gemini CLI

**Best used when:** Gemini CLI edits files in your repo and you want the affected tests to run on every write, and the agent to be refused a clean finish while they are red.
**Read before:** editing `GEMINI.md` or `.gemini/settings.json`.
**See also:** [README.md](./README.md) · [hooks/claude-post-edit-test.sh](./hooks/claude-post-edit-test.sh) · [hooks/claude-stop-gate.sh](./hooks/claude-stop-gate.sh) · [../testing-from-zero.md](../testing-from-zero.md)

Gemini CLI has the most complete hook event list of the CLI agents and one rule that catches everyone once: a hook's stdout must be nothing but JSON. The shared scripts print progress lines, so they run behind a two-line wrapper that moves stdout to stderr.

## 1. Instruction file

`GEMINI.md` is read from `~/.gemini/GEMINI.md`, the project root, its parent directories, and just-in-time from the subdirectory being worked in. `@file.md` imports work inside it.

If `AGENTS.md` is your canonical file, do not copy it — tell Gemini to read it:

```json
{
  "context": {
    "fileName": ["AGENTS.md", "GEMINI.md"]
  }
}
```

`.gemini/settings.json`, checked in. Verified against https://geminicli.com/docs/cli/gemini-md/ on 2026-09-07.

The testing block is the one from [README.md](./README.md) section 5(a): the rule, the layer choice, the single-test and full-suite commands, red-then-green with pasted output, the ban on weakened assertions, and the `[skip-tests] reason:` trailer.

Path-scoped rules: Gemini scopes by directory, not by glob. A monorepo puts `src/GEMINI.md` and `e2e/GEMINI.md` next to the code they govern; a `globs:`-style frontmatter is `[verify]` — it is not in the current docs.

## 2. Hooks

Hooks live under `"hooks"` in the same `.gemini/settings.json` (project) or `~/.gemini/settings.json` (user).

```json
{
  "hooks": {
    "AfterTool": [
      {
        "matcher": "write_file|replace",
        "hooks": [
          {
            "name": "affected-tests",
            "type": "command",
            "command": "$GEMINI_PROJECT_DIR/.gemini/hooks/post-edit-test.sh",
            "timeout": 180000
          }
        ]
      }
    ],
    "AfterAgent": [
      {
        "hooks": [
          {
            "name": "finish-gate",
            "type": "command",
            "command": "$GEMINI_PROJECT_DIR/.gemini/hooks/stop-gate.sh",
            "timeout": 30000
          }
        ]
      }
    ]
  }
}
```

Verified against https://geminicli.com/docs/hooks/ on 2026-09-07.

| Contract | Value |
|---|---|
| Events | `SessionStart`, `SessionEnd`, `BeforeAgent`, `AfterAgent`, `BeforeModel`, `AfterModel`, `BeforeToolSelection`, `BeforeTool`, `AfterTool`, `PreCompress`, `Notification` |
| Matcher | Regex over tool names — file edits are `write_file` and `replace` |
| Stdin, all events | `session_id`, `transcript_path`, `cwd`, `hook_event_name`, `timestamp` |
| Stdin, `BeforeTool` / `AfterTool` | `tool_name`, `tool_input` (the raw tool arguments — for `write_file` and `replace` that is `tool_input.file_path`), `AfterTool` adds `tool_response` |
| Stdin, `AfterAgent` | `prompt`, `prompt_response`, `stop_hook_active` (true when this hook already forced a retry — the loop guard) |
| `timeout` | **Milliseconds**, not seconds. `180` is 0.18s and every test run will look like a timeout |
| Stdout | Must be **only** the final JSON object. Send every log line to stderr or the parse fails |
| Exit 0 | Stdout is parsed as the hook's JSON result |
| Exit 2 | Block; stderr is used as the reason |
| Other non-zero | Warning only — the agent proceeds |
| Decision JSON | `{"decision": "deny", "reason": "..."}` (`"block"` is an alias); on `AfterAgent` it rejects the response and forces a retry with `reason` as feedback |
| Env | `GEMINI_PROJECT_DIR`, `GEMINI_SESSION_ID`, `GEMINI_CWD`, plus `CLAUDE_PROJECT_DIR` as an alias |

Verified against https://geminicli.com/docs/hooks/ , https://geminicli.com/docs/hooks/reference and https://geminicli.com/docs/tools/file-system/ on 2026-09-07.

The shared script reads `tool_input.file_path` directly, so stdin passes straight through. The wrapper exists only for the stdout rule:

```bash
#!/usr/bin/env bash
# .gemini/hooks/post-edit-test.sh
# Everything on stdout would be parsed as the hook result, so the shared script's
# progress lines go to stderr and the hook answers with an empty JSON object.
set -euo pipefail
"$GEMINI_PROJECT_DIR/.gemini/hooks/claude-post-edit-test.sh" >&2
echo '{}'
```

```bash
mkdir -p .gemini/hooks
cp guides/testing/enforcement/hooks/claude-post-edit-test.sh .gemini/hooks/
cp guides/testing/enforcement/hooks/claude-stop-gate.sh      .gemini/hooks/
chmod +x .gemini/hooks/*.sh
```

The finish gate needs the same stdout discipline:

```bash
#!/usr/bin/env bash
# .gemini/hooks/stop-gate.sh — exit 2 with the reason on stderr; nothing on stdout.
set -euo pipefail
"$GEMINI_PROJECT_DIR/.gemini/hooks/claude-stop-gate.sh" 1>&2
```

`claude-stop-gate.sh` prints its reason to stderr and exits 2, which is exactly Gemini's blocking contract, and it honours `stop_hook_active` in the `AfterAgent` payload so a block does not loop. If you prefer the JSON form, `STOP_GATE_JSON=1` makes it exit 0 with `{"decision":"block","reason":"..."}` on stdout — Gemini accepts `block` as an alias of `deny`.

## 3. Verify it works

| Step | How | Expected |
|---|---|---|
| 1. Tests run after an edit | Ask Gemini to change one source file that has a test | `[post-edit] GREEN — <target>` on stderr; `.git/agent-test-state` refreshed |
| 2. Red refuses the finish | Break an assertion by hand, ask Gemini to touch the source again, let it finish | `Do not finish yet. the last test run was RED for ...` |
| 3. A `feat` with no test is rejected | `git commit -m "feat: thing"` with only source staged | `COMMIT REJECTED — no test added or updated for: feat: thing` |

If step 1 appears to hang and then fail, check the `timeout` unit before anything else. It is the mistake everyone makes once.

## 4. Limits

- Anything written to stdout by a hook is treated as its JSON result. A stray `echo` from a script you copied in will look like a broken hook, not a noisy one.
- The Gemini CLI documentation site currently carries a banner about the CLI being replaced by "Antigravity CLI" for some tiers. Re-read it before investing in Gemini-specific hook wiring; the git hook and CI below it are tool-independent.
- A non-2 non-zero exit is a warning, not a block. If you want a refusal, it must be exactly exit 2.
- Gemini hooks fire only for Gemini CLI. The git hook and [hooks/ci-required-check.yml](./hooks/ci-required-check.yml) cover everything else.

## Sources & further reading

- Gemini CLI hooks — https://geminicli.com/docs/hooks/ · stdin/stdout reference — https://geminicli.com/docs/hooks/reference · tool arguments — https://geminicli.com/docs/tools/file-system/
- Gemini CLI context files (`GEMINI.md`, `context.fileName`, imports) — https://geminicli.com/docs/cli/gemini-md/
- The `AGENTS.md` convention — https://agents.md/

## Related

- [README.md](./README.md) — the three layers and the provider-agnostic recipe
- [hooks/claude-post-edit-test.sh](./hooks/claude-post-edit-test.sh) · [hooks/claude-stop-gate.sh](./hooks/claude-stop-gate.sh) · [hooks/require-spec-for-feature.sh](./hooks/require-spec-for-feature.sh)
- [../testing-from-zero.md](../testing-from-zero.md) — the layer table the instruction block points at

_Last reviewed: 2026-09-07._
