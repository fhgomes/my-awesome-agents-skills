# Testing Enforcement — OpenAI Codex

**Best used when:** Codex is writing code in your repo and you want the affected tests to run without asking, and a finish to be refused while they are red.
**Read before:** editing `AGENTS.md`, `.codex/config.toml` or `.codex/hooks.json`.
**See also:** [README.md](./README.md) · [hooks/claude-post-edit-test.sh](./hooks/claude-post-edit-test.sh) · [hooks/claude-stop-gate.sh](./hooks/claude-stop-gate.sh) · [../testing-from-zero.md](../testing-from-zero.md)

Codex reads `AGENTS.md` natively, which makes it the cheapest tool to set up and the one that most tempts you to stop at layer 1. Instructions are still context, not enforcement.

## 1. Instruction file

`AGENTS.md`, anywhere in the tree — the nearest one to the file being edited wins, so a monorepo can keep `src/AGENTS.md` and `e2e/AGENTS.md` with their own test commands. No pointer file, no setting to flip.

Put the block from [README.md](./README.md) section 5(a) under a `## Testing (non-negotiable)` heading: the rule, the layer choice, the single-test and full-suite commands, red-then-green with pasted output, the ban on weakened assertions, and the `[skip-tests] reason:` trailer.

Two settings in `~/.codex/config.toml` or `.codex/config.toml` decide whether the file is even read in full:

```toml
project_doc_max_bytes = 32768                      # AGENTS.md is truncated past this
project_doc_fallback_filenames = ["CLAUDE.md"]     # read if no AGENTS.md is found
```

Verified against https://learn.chatgpt.com/docs/config-file/config-reference on 2026-09-07.

A testing block that lands past the byte cap is a testing block that does not exist. Keep `AGENTS.md` a router, not a manual.

## 2. Sandbox and approvals

Enforcement needs the agent to be able to run tests. These two settings decide that:

```toml
approval_policy = "on-request"     # "untrusted" | "on-request" | "never"
sandbox_mode    = "workspace-write" # "read-only" | "workspace-write" | "danger-full-access"
```

Verified against https://learn.chatgpt.com/docs/config-file/config-reference on 2026-09-07.

`read-only` means Codex cannot run your test command, so every "tests pass" claim is unverified prose. `workspace-write` is the working default for a repo whose tests are local. Integration tests that need a container are the reason people reach for `danger-full-access`; prefer granting the container socket explicitly over turning the sandbox off.

## 3. Hooks

Codex discovers hooks in `~/.codex/hooks.json`, `~/.codex/config.toml` (inline `[hooks]` tables), `<repo>/.codex/hooks.json` and `<repo>/.codex/config.toml`. **Project hooks load only when the project is trusted** — an untrusted clone silently has no enforcement, which is one more reason the git hook and CI exist.

`.codex/hooks.json`:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "apply_patch",
        "hooks": [
          { "type": "command", "command": ".codex/hooks/post-edit-test.sh", "timeout": 180 }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          { "type": "command", "command": ".codex/hooks/stop-gate.sh", "timeout": 30 }
        ]
      }
    ]
  }
}
```

The same thing inline in `.codex/config.toml`:

```toml
[[hooks.PostToolUse]]
matcher = "apply_patch"
[[hooks.PostToolUse.hooks]]
type = "command"
command = ".codex/hooks/post-edit-test.sh"
timeout = 180
```

Verified against https://learn.chatgpt.com/docs/hooks and https://learn.chatgpt.com/docs/config-file/config-advanced on 2026-09-07.

| Contract | Value |
|---|---|
| Events | `PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `PermissionRequest`, `Stop`, `Interrupt`, `UserPromptSubmit`, `SessionStart`, `SessionEnd`, `SubagentStart`, `SubagentStop`, `PreCompact`, `PostCompact` |
| Stdin | `session_id`, `cwd`, `hook_event_name`, `model`, `permission_mode`; turn-scoped events add `turn_id`; tool events add `tool_name`, `tool_input`; `Stop` adds `stop_hook_active` and `last_assistant_message` |
| File path | **There is no `tool_input.file_path`.** File edits arrive as `apply_patch` (`tool_name` is always `apply_patch`; a matcher may say `apply_patch`, `Edit` or `Write`), and `tool_input.command` carries the patch text, not a clean path |
| Exit 0 | Success, output processed normally |
| Exit 2 | Blocking decision; the reason is read from stderr |
| Other | Hook error, reported to the user |
| Decision JSON | `Stop`: `{"decision": "block", "reason": "..."}` forces another turn. `PreToolUse`: `{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "..."}}` |

Verified against https://learn.chatgpt.com/docs/hooks on 2026-09-07.

Because the path is not handed to you, wrap the shared scripts instead of rewriting them — [hooks/claude-post-edit-test.sh](./hooks/claude-post-edit-test.sh) already falls back to `git diff --name-only` when no path is on stdin:

```bash
# cp guides/testing/enforcement/hooks/claude-post-edit-test.sh .codex/hooks/
# cp guides/testing/enforcement/hooks/claude-stop-gate.sh      .codex/hooks/
# chmod +x .codex/hooks/*.sh

#!/usr/bin/env bash
# .codex/hooks/post-edit-test.sh — Codex passes a patch, not a path. Drop stdin and
# let the shared script find the changed file from the working tree.
set -euo pipefail
cat >/dev/null
echo '{}' | "$(git rev-parse --show-toplevel)/.codex/hooks/claude-post-edit-test.sh"
```

`.codex/hooks/stop-gate.sh` can be `claude-stop-gate.sh` itself, unchanged: Codex's `Stop` payload carries `stop_hook_active`, so the loop guard works, and its exit-2-plus-stderr contract is identical to Codex's.

## 4. Verify it works

| Step | How | Expected |
|---|---|---|
| 1. Tests run after an edit | Ask Codex to change one source file that has a test | `[post-edit] GREEN — <target>` in the hook output; `.git/agent-test-state` refreshed |
| 2. Red refuses the finish | Break an assertion by hand, ask Codex to touch the source again, let it finish | `Do not finish yet. the last test run was RED for ...` |
| 3. A `feat` with no test is rejected | `git commit -m "feat: thing"` with only source staged | `COMMIT REJECTED — no test added or updated for: feat: thing` |

If step 1 does nothing, the project is almost certainly untrusted — check that first, before the JSON.

## 5. Limits

- Untrusted project = no project hooks. Silent, not an error.
- No documented per-path rule scoping beyond directory-nearest `AGENTS.md`.
- Codex hooks only fire for Codex. The git hook and the CI required check are what cover the other tools and the human with `--no-verify`.
- Everything above was read on 2026-09-07 from a documentation set that redirected twice in a year. Re-check the URLs before copying a block into a repo you cannot easily fix.

## Sources & further reading

- Codex config reference — https://learn.chatgpt.com/docs/config-file/config-reference
- Codex advanced config (inline hook tables) — https://learn.chatgpt.com/docs/config-file/config-advanced
- Codex hooks — https://learn.chatgpt.com/docs/hooks (redirected from https://developers.openai.com/codex/hooks)
- The `AGENTS.md` convention — https://agents.md/

## Related

- [README.md](./README.md) — the three layers and the provider-agnostic recipe
- [hooks/claude-post-edit-test.sh](./hooks/claude-post-edit-test.sh) · [hooks/claude-stop-gate.sh](./hooks/claude-stop-gate.sh) · [hooks/require-spec-for-feature.sh](./hooks/require-spec-for-feature.sh)
- [../testing-from-zero.md](../testing-from-zero.md) — the layer table the instruction block points at

_Last reviewed: 2026-09-07._
