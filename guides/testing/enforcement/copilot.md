# Testing Enforcement — GitHub Copilot

**Best used when:** your team uses Copilot in VS Code, the Copilot coding agent on GitHub, or the Copilot CLI, and you want "ships a test" to be a property of the repo rather than of the prompt.
**Read before:** writing `.github/copilot-instructions.md` or adding `.github/hooks/`.
**See also:** [README.md](./README.md) · [hooks/require-spec-for-feature.sh](./hooks/require-spec-for-feature.sh) · [hooks/ci-required-check.yml](./hooks/ci-required-check.yml) · [../testing-from-zero.md](../testing-from-zero.md)

Copilot is three products with three enforcement stories: the IDE assistant, the cloud coding agent that opens pull requests, and the CLI. The cloud agent is the one that matters most here. It does have a finish gate (`agentStop`), but its exit-code rules differ from every other tool on this list — and because it delivers work as a pull request, the CI required check is still the guarantee.

## 1. Instruction files

| Path | Applies to | Scope |
|---|---|---|
| `.github/copilot-instructions.md` | Chat, code review, cloud agent | Whole repo |
| `.github/instructions/NAME.instructions.md` | Cloud agent + code review only | Paths in `applyTo:` frontmatter |
| `AGENTS.md` (anywhere; nearest wins) | Cloud agent | Directory subtree |
| `CLAUDE.md` / `GEMINI.md` at the root | Cloud agent | Whole repo |

Verified against https://docs.github.com/en/copilot/how-tos/configure-custom-instructions/add-repository-instructions on 2026-09-07.

`.github/copilot-instructions.md` gets the block from [README.md](./README.md) section 5(a) — or one line pointing at `AGENTS.md` if that is your canonical file, since the cloud agent reads it natively.

Path-scoped variant, `.github/instructions/testing.instructions.md`:

```markdown
---
applyTo: "src/**/*.ts, src/**/*.java, e2e/**/*.spec.ts"
description: Testing rules for source and spec files
---
Every feat/fix ships a test at the layer where the bug lives. If you fix a bug,
write the test that would have caught it.
One scenario per test, named `Should X when Y`. Assert results, not internal calls.
Assert failures by status + machine-readable code, never by message text.
Never add `@Disabled`, `test.skip(true)`, `.only(` or `xit(` to reach green.
Run `<SINGLE_TEST_CMD>` and paste the output in the PR description.
```

Verified against https://docs.github.com/en/copilot/how-tos/configure-custom-instructions/add-repository-instructions on 2026-09-07.

`applyTo` takes comma-separated globs. `excludeAgent: code-review` (or `cloud-agent`) narrows which consumer sees the file. Path-specific instructions do **not** apply to Copilot chat in the IDE — put anything the IDE must see in `.github/copilot-instructions.md`.

## 2. Hooks

`.github/hooks/*.json`, checked in. The CLI additionally reads user-level hooks from `~/.copilot/hooks/`.

```json
{
  "version": 1,
  "disableAllHooks": false,
  "hooks": {
    "postToolUse": [
      {
        "type": "command",
        "bash": ".github/hooks/post-edit-test.sh",
        "timeoutSec": 180
      }
    ],
    "preToolUse": [
      {
        "type": "command",
        "bash": ".github/hooks/guard-test-edits.sh",
        "timeoutSec": 15
      }
    ],
    "agentStop": [
      {
        "type": "command",
        "bash": ".github/hooks/claude-stop-gate.sh",
        "env": { "STOP_GATE_JSON": "1" },
        "timeoutSec": 30
      }
    ]
  }
}
```

Verified against https://docs.github.com/en/copilot/reference/hooks-reference on 2026-09-07.

| Contract | Value |
|---|---|
| Events | `sessionStart`, `sessionEnd`, `userPromptSubmitted`, `userPromptTransformed`, `preToolUse`, `postToolUse`, `postToolUseFailure`, `agentStop`, `subagentStart`, `subagentStop`, `errorOccurred`, `preCompact`, `notification`; `permissionRequest` exists for the CLI only (cloud agent tool calls are pre-approved) |
| Command fields | `type: "command"`, `bash`, `powershell`, `cwd`, `env`, `timeoutSec` (CLI also accepts `exec` + `args`) |
| Stdin, tool events | `sessionId`, `timestamp`, `cwd`, `toolName`, `toolArgs` (typed `unknown` — its shape depends on the tool); `postToolUse` adds `toolResult` |
| Stdin, `agentStop` | `sessionId`, `timestamp`, `cwd`, `transcriptPath`, `stopReason`, `stop_hook_active` (true when a prior `block` from this hook already forced a turn) |
| PascalCase variant | Naming the event `PreToolUse` / `Stop` instead of `preToolUse` / `agentStop` switches the payload to snake_case (`tool_input`, `stop_hook_active`) for VS Code compatibility |
| `preToolUse` stdout | `{"permissionDecision": "allow"` / `"deny"` / `"ask"`, `"permissionDecisionReason": "...", "modifiedArgs": {}}` |
| `agentStop` stdout | `{"decision": "block", "reason": "..."}` forces another agent turn with `reason` as the prompt — in the cloud agent too, where it counts against the job timeout |
| Exit 0 | stdout parsed as JSON |
| Exit 2 | **A warning, not a block** — except on `preToolUse` and `permissionRequest`, where it denies the call |
| Other non-zero | Fail-open, except `preToolUse`, which is fail-closed (the call is denied). Timeouts are fail-open everywhere |
| Cloud agent requirement | The hook file must be on the **default branch** to be picked up |

Verified against https://docs.github.com/en/copilot/reference/hooks-reference and https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/use-hooks on 2026-09-07.

Two consequences. The finish gate must answer with JSON, which is why the `agentStop` entry above sets `STOP_GATE_JSON=1`: [hooks/claude-stop-gate.sh](./hooks/claude-stop-gate.sh) then exits 0 with `{"decision":"block","reason":"..."}` instead of exit 2, and it honours `stop_hook_active` so a block does not loop. And `preToolUse` is the one event that blocks a *tool call*; use it for the refusal that is genuinely pre-emptive — an edit that adds a skip marker:

```bash
#!/usr/bin/env bash
# .github/hooks/guard-test-edits.sh — deny a write that disables a test.
set -euo pipefail
ARGS="$(cat)"
if printf '%s' "$ARGS" | grep -qE '@Disabled|@Ignore|test\.skip\(true|\.only\(|\bxit\('; then
  printf '{"permissionDecision":"deny","permissionDecisionReason":"This edit disables a test. Make it pass or delete it with a stated reason."}'
else
  printf '{"permissionDecision":"allow"}'
fi
```

For `postToolUse`, wrap the shared script. Copilot sends `toolArgs`, whose shape the docs leave as `unknown`; the script picks up a `file_path` key if one is present anywhere in the payload `[unverified — check your tool's docs]` and otherwise falls back to the first changed file in the working tree:

```bash
#!/usr/bin/env bash
# .github/hooks/post-edit-test.sh
set -euo pipefail
./.github/hooks/claude-post-edit-test.sh >&2
```

```bash
mkdir -p .github/hooks
cp guides/testing/enforcement/hooks/claude-post-edit-test.sh .github/hooks/
cp guides/testing/enforcement/hooks/claude-stop-gate.sh      .github/hooks/
chmod +x .github/hooks/*.sh
```

## 3. The finish gate is a convenience — CI is the guarantee

`agentStop` with `decision: "block"` keeps the agent working, but every forced turn spends the job's timeout budget, the gate only knows about the affected test it last ran, and a hook change cannot be exercised by the PR that introduces it (default-branch rule). The coding agent delivers its work as a pull request, and a pull request is exactly what a required status check inspects.

Install [hooks/ci-required-check.yml](./hooks/ci-required-check.yml). Its `spec-guard` job replays [hooks/require-spec-for-feature.sh](./hooks/require-spec-for-feature.sh) over every commit in the PR range, so a Copilot-authored `feat:` with no test fails the check like anyone else's. Mark the `required` job as required in branch protection and leave admin bypass off.

## 4. Verify it works

| Step | How | Expected |
|---|---|---|
| 1. Tests run after an edit | In the CLI or IDE agent, change one source file that has a test | `[post-edit] GREEN — <target>`; `.git/agent-test-state` refreshed |
| 2. A disabling edit is refused | Ask it to "skip the failing test" | `This edit disables a test...` and the write does not happen |
| 3. Red refuses the finish | Break an assertion by hand, let the agent edit the source and finish | The session log shows one more turn opening with `Do not finish yet. the last test run was RED ...` |
| 4. A `feat` with no test is rejected | Open a PR with a `feat:` commit touching only source | The `spec-guard` job fails and `required` blocks the merge |

## 5. Limits

- Exit 2 is a warning on every event except `preToolUse` and `permissionRequest`. A stop gate that exits 2 here is silently ignored; it must speak JSON (`STOP_GATE_JSON=1`).
- A forced turn from `agentStop` counts against the cloud job's timeout. Keep the gate cheap; the full suite belongs in CI.
- Path-specific `.instructions.md` files are ignored by IDE chat.
- Hook files must be on the default branch for the cloud agent, so a hook change only takes effect after it merges — and it cannot be tested by the PR that introduces it.
- `disableAllHooks: true` in any discovered hooks file turns the whole layer off. Grep for it during review.
- The `toolArgs` shape for edits is undocumented; the scripts do not depend on it.

## Sources & further reading

- Repository custom instructions — https://docs.github.com/en/copilot/how-tos/configure-custom-instructions/add-repository-instructions
- Copilot hooks reference — https://docs.github.com/en/copilot/reference/hooks-reference
- Copilot cloud agent hooks (default-branch rule) — https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/use-hooks · CLI hooks — https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/use-hooks
- Branch protection and rulesets — https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches

## Related

- [README.md](./README.md) — the three layers and the provider-agnostic recipe
- [hooks/ci-required-check.yml](./hooks/ci-required-check.yml) · [hooks/require-spec-for-feature.sh](./hooks/require-spec-for-feature.sh) · [hooks/claude-post-edit-test.sh](./hooks/claude-post-edit-test.sh)
- [../testing-from-zero.md](../testing-from-zero.md) — the layer table the instruction block points at

_Last reviewed: 2026-09-07._
