# Testing Enforcement — Claude Code

**Best used when:** you drive Claude Code on a repo and "add a test" keeps turning into "I updated the docs instead".
**Read before:** editing `CLAUDE.md` or `.claude/settings.json` for testing rules.
**See also:** [README.md](./README.md) · [hooks/claude-post-edit-test.sh](./hooks/claude-post-edit-test.sh) · [hooks/claude-stop-gate.sh](./hooks/claude-stop-gate.sh) · [../testing-from-zero.md](../testing-from-zero.md)

Claude Code is the tool whose own documentation states the split this whole directory is built on: instruction files are context, hooks are enforcement.

> "Claude treats them as context, not enforced configuration. To block an action regardless of what Claude decides, use a PreToolUse hook."

Verified against https://code.claude.com/docs/en/memory on 2026-09-07.

## 1. Instruction file

| Path | Scope |
|---|---|
| `./CLAUDE.md` or `./.claude/CLAUDE.md` | The project, checked in |
| `./CLAUDE.local.md` | Your machine only — gitignore it |
| `~/.claude/CLAUDE.md` | Every project you open |
| `.claude/rules/*.md` with `paths:` frontmatter | Loaded only for matching files |

**Claude Code reads `CLAUDE.md`, not `AGENTS.md`.** If `AGENTS.md` is your canonical router (it is for Codex, Cursor and Copilot), do not duplicate it — import it:

```markdown
# CLAUDE.md
@AGENTS.md

<Claude Code specifics only below this line.>
```

`ln -s AGENTS.md CLAUDE.md` works too, and is worse on Windows checkouts. Keep each file under ~200 lines; past that it stops being read carefully. Verified against https://code.claude.com/docs/en/memory on 2026-09-07.

The testing block itself is the one from [README.md](./README.md) section 5(a) — the rule, the layer choice, the single-test and full-suite commands, red-then-green with pasted output, the ban on weakened assertions, and the `[skip-tests] reason:` trailer. If `CLAUDE.md` imports `AGENTS.md`, you write it once.

**Path-scoped variant** — `.claude/rules/testing.md`, loaded only when Claude touches test code:

```markdown
---
paths:
  - "src/**/*Test.java"
  - "src/**/*.test.ts"
  - "e2e/**/*.spec.ts"
---
One scenario per test, named `Should X when Y`. Assert results, not internal calls.
Assert failures by status + machine-readable code, never by message text.
Never add `@Disabled`, `test.skip(true)`, `.only(` or `xit(` to reach green.
```

Verified against https://code.claude.com/docs/en/memory on 2026-09-07.

## 2. Hooks

`.claude/settings.json`, checked in. `.claude/settings.local.json` is the personal override; `~/.claude/settings.json` is the global one.

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write|MultiEdit",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/claude-post-edit-test.sh",
            "timeout": 180
          }
        ]
      }
    ],
    "Stop": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/claude-stop-gate.sh"
          }
        ]
      }
    ]
  }
}
```

Verified against https://code.claude.com/docs/en/hooks on 2026-09-07.

```bash
mkdir -p .claude/hooks
cp guides/testing/enforcement/hooks/claude-post-edit-test.sh .claude/hooks/
cp guides/testing/enforcement/hooks/claude-stop-gate.sh .claude/hooks/
chmod +x .claude/hooks/*.sh
```

| Contract | Value |
|---|---|
| Stdin | JSON with `session_id`, `cwd`, `hook_event_name`, `tool_name`, `tool_input.file_path`, `tool_input.command`; `Stop` adds `stop_hook_active` and `last_assistant_message` |
| Exit 0 | Proceed; stdout is parsed as JSON if it is JSON |
| Exit 2 | **Block.** stderr is fed back to Claude as the reason. On `Stop` this refuses the finish and Claude keeps working |
| Other | Non-blocking error, surfaced to the user |
| JSON alternative | Exit 0 with `{"decision": "block", "reason": "..."}` on stdout — top-level fields, `reason` required. (`hookSpecificOutput.additionalContext` only adds context; it does not block.) `STOP_GATE_JSON=1` makes the script emit this |
| Loop cap | `stop_hook_active` is `true` when Claude is already continuing because of a Stop hook; Claude Code also caps consecutive forced continuations at 8 |
| `timeout` | Seconds |
| Env | `${CLAUDE_PROJECT_DIR}` is the repo root — use it, hooks do not run from a predictable cwd |

Verified against https://code.claude.com/docs/en/hooks on 2026-09-07.

`claude-stop-gate.sh` checks `stop_hook_active` and exits 0 when it is true. Without that guard, a Stop hook that blocks fires again on the next stop and the session never ends. Add `SubagentStop` with the same command if you run subagents; a subagent that returns red work is exactly where a stale green comes from.

Optionally add `.claude/agents/test-engineer.md` as a subagent whose body points at `skills/test-engineer/SKILL.md`, so "write the tests for this" routes to the checklist instead of improvising.

## 3. Verify it works

| Step | Command | Expected |
|---|---|---|
| 1. Tests run after an edit | Ask Claude to change one source file that has a test | Transcript shows `[post-edit] GREEN — <target>`; `.git/agent-test-state` has a fresh timestamp |
| 2. Red refuses the finish | Break an assertion in that test by hand, ask Claude to edit the source again, then let it finish | `Do not finish yet. the last test run was RED for ...` and the turn continues |
| 3. A `feat` with no test is rejected | `git commit -m "feat: thing"` after staging only source | `COMMIT REJECTED — no test added or updated for: feat: thing` |

Step 3 is the git hook from [hooks/require-spec-for-feature.sh](./hooks/require-spec-for-feature.sh), not Claude Code. That is the point: it fires no matter which tool wrote the code.

## 4. Limits

- Hooks live in the working copy. A fresh clone has `CLAUDE.md` (checked in) and no installed git hooks. Run `scripts/install-hooks.sh` in onboarding and `--check` in CI.
- Claude Code hooks only fire for Claude Code. The same repo edited in Cursor or by a Copilot cloud agent gets nothing from `.claude/settings.json`.
- The Stop gate reasons over a state file, not over the truth. It knows the affected test was green; it does not know the full suite is green. That answer only exists in CI.
- Nothing here stops `git commit --no-verify`. [hooks/ci-required-check.yml](./hooks/ci-required-check.yml) does.

## Sources & further reading

- Claude Code memory (CLAUDE.md, imports, `.claude/rules/`) — https://code.claude.com/docs/en/memory
- Claude Code hooks (events, stdin, exit codes) — https://code.claude.com/docs/en/hooks
- Claude Code settings precedence — https://code.claude.com/docs/en/settings

## Related

- [README.md](./README.md) — the three layers and the provider-agnostic recipe
- [hooks/claude-post-edit-test.sh](./hooks/claude-post-edit-test.sh) · [hooks/claude-stop-gate.sh](./hooks/claude-stop-gate.sh)
- [../testing-from-zero.md](../testing-from-zero.md) — the layer table the instruction block points at

_Last reviewed: 2026-09-07._
