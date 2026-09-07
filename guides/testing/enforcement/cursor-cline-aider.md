# Testing Enforcement — Cursor, Cline, aider (and any model behind them)

**Best used when:** the team is on Cursor, Cline or aider — often driving a non-frontier model like DeepSeek, Qwen or a local Ollama build — and "it said it added tests" keeps turning out to be false.
**Read before:** writing `.cursor/rules/`, `.clinerules/`, `CONVENTIONS.md` or `.aider.conf.yml`.
**See also:** [README.md](./README.md) · [hooks/pre-commit-tests.sh](./hooks/pre-commit-tests.sh) · [hooks/claude-stop-gate.sh](./hooks/claude-stop-gate.sh) · [../testing-from-zero.md](../testing-from-zero.md)

These three sit at three different points on the enforcement scale: Cursor has real lifecycle hooks, Cline documents rules well and hooks poorly, aider has no hooks at all and does not need them because it runs your test command after every edit by design.

## 1. Cursor

**Rules** — `.cursor/rules/testing.mdc`, checked in. `AGENTS.md` is read natively (nested, nearest wins), so point at it rather than duplicating it.

```markdown
---
description: Testing rules for source and spec files
globs: ["src/**/*.ts", "src/**/*.java", "e2e/**/*.spec.ts"]
alwaysApply: false
---
Every feat/fix ships a test at the layer where the bug lives. If you fix a bug,
write the test that would have caught it. Choose the layer before writing.
Single test: `<SINGLE_TEST_CMD>` · Full suite: `<FULL_SUITE_CMD>`
Red then green: paste the failure, then the pass, then the count before -> after.
Never weaken an assertion or add `@Disabled` / `test.skip(true)` / `.only(` / `xit(`.
No test? `[skip-tests] reason: <why>` in the commit body. "No time" is not a reason.
```

Verified against https://cursor.com/docs/context/rules on 2026-09-07.

**Hooks** — `.cursor/hooks.json` (project) or `~/.cursor/hooks.json` (user).

```json
{
  "version": 1,
  "hooks": {
    "afterFileEdit": [
      { "command": ".cursor/hooks/post-edit-test.sh" }
    ],
    "stop": [
      { "command": ".cursor/hooks/stop-gate.sh", "loop_limit": 3 }
    ]
  }
}
```

Verified against https://cursor.com/docs/agent/hooks on 2026-09-07.

| Contract | Value |
|---|---|
| Events | `sessionStart`, `sessionEnd`, `beforeShellExecution`, `afterShellExecution`, `beforeMCPExecution`, `afterMCPExecution`, `beforeReadFile`, `afterFileEdit`, `beforeSubmitPrompt`, `preToolUse`, `postToolUse`, `postToolUseFailure`, `preCompact`, `stop`, `afterAgentResponse`, `subagentStart`, `subagentStop` |
| `afterFileEdit` stdin | `{"file_path": "<absolute path>", "edits": [{"old_string": "...", "new_string": "..."}]}` |
| `stop` stdin / stdout | In: `{"status": "completed" \| "aborted" \| "error", "loop_count": 0}`. Out: `{"followup_message": "..."}` — auto-submitted as the next user message, i.e. "keep working". `loop_limit` (default 5) caps the follow-ups |
| Tool events stdout | `{"permission": "allow"` / `"deny"` / `"ask"`, `"user_message": "...", "agent_message": "..."}` |
| Exit 0 | The JSON on stdout is used |
| Exit 2 | Block (same as `permission: "deny"`) on tool events |
| Other | Fail-open — the agent proceeds. Set `"failClosed": true` on a hook entry to invert that |
| Env | `CURSOR_PROJECT_DIR`, `CURSOR_VERSION`, `CURSOR_TRANSCRIPT_PATH` |

Verified against https://cursor.com/docs/agent/hooks on 2026-09-07.

```bash
mkdir -p .cursor/hooks
cp guides/testing/enforcement/hooks/claude-post-edit-test.sh .cursor/hooks/post-edit-test.sh
cp guides/testing/enforcement/hooks/claude-stop-gate.sh      .cursor/hooks/claude-stop-gate.sh
printf '#!/usr/bin/env bash\nSTOP_GATE_JSON=cursor exec "$CURSOR_PROJECT_DIR/.cursor/hooks/claude-stop-gate.sh"\n' > .cursor/hooks/stop-gate.sh
chmod +x .cursor/hooks/*.sh
```

The post-edit script reads Cursor's top-level `file_path` as-is. The stop gate needs the one-line wrapper: Cursor's `stop` hook does not block on exit 2, it continues on `followup_message`, and `STOP_GATE_JSON=cursor` makes the script emit exactly that (and exit 0 when `loop_count` is already above zero, so `loop_limit` is a backstop rather than the only guard). `chmod +x` is not optional; Cursor will not run a non-executable hook. Note the fail-open default: a hook that crashes lets the agent through, so keep the scripts boring or set `failClosed`.

## 2. Cline

**Rules** — `.clinerules/testing.md` at the workspace root (a folder, not a single file). Cline also reads `AGENTS.md`, `.cursorrules` and `.windsurfrules`, and supports conditional rules through frontmatter:

```markdown
---
paths:
  - "src/**"
  - "test/**"
---
Every feat/fix ships a test at the layer where the bug lives.
Run `<SINGLE_TEST_CMD>` and paste the output before claiming the task is done.
Never add `@Disabled`, `test.skip(true)`, `.only(` or `xit(` to reach green.
```

Verified against https://docs.cline.bot/features/cline-rules on 2026-09-07.

**Hooks** — `.clinerules/hooks/`, with events `TaskStart`, `PreToolUse`, `PostToolUse` and `TaskComplete`. The documentation page defers to the SDK plugins docs and does not specify the stdin fields, the stdout schema or the blocking exit code. `[unverified — check your tool's docs]` — do not build your gate on it. Use the git `pre-commit` hook and the CI required check for Cline, and treat `.clinerules/` as layer 1 only.

**Choosing the model** — Settings -> API Provider dropdown -> DeepSeek -> paste the API key -> pick the model in the model dropdown. Verified against https://docs.cline.bot/provider-config/deepseek on 2026-09-07.

## 3. aider

aider has no hook system and does not need one, because running the tests after every edit is a first-class setting. `.aider.conf.yml` at the repo root:

```yaml
read: [CONVENTIONS.md, AGENTS.md]
test-cmd: "./gradlew :app:test --tests '*'"   # your single-suite command
auto-test: true
lint-cmd: "npm run lint"
auto-lint: true
model: deepseek/deepseek-chat                  # or any model id
# openai-api-base: http://localhost:11434/v1   # any OpenAI-compatible endpoint
```

Verified against https://aider.chat/docs/config/aider_conf.html, https://aider.chat/docs/usage/lint-test.html and https://aider.chat/docs/usage/conventions.html on 2026-09-07.

`auto-test: true` makes aider run `test-cmd` after each change and attempt a fix when it fails. **That is aider's enforcement** — the same job the post-edit hook does elsewhere, built in. `/test <cmd>` runs it on demand mid-chat. `read:` marks the listed files read-only context, which is how `CONVENTIONS.md` (or your `AGENTS.md`) stays in every prompt without aider trying to edit it.

Two cautions. `test-cmd` should be the *fast* suite; point it at the full ten-minute gate and it will be turned off by the end of the week. And "attempt a fix when it fails" is exactly the moment a model reaches for a weakened assertion, so the git `commit-msg` hook and the `stop`-equivalent do not become optional — review the diff for skip markers.

## 4. Continue

`.continue/rules/*.md` (project) with frontmatter `name`, `description`, `globs`, `regex`, `alwaysApply`; rules apply to Agent, Chat and Edit, not to autocomplete. Verified against https://docs.continue.dev/customize/deep-dives/rules on 2026-09-07. Neither hooks nor `AGENTS.md` support appear in that documentation — copy the testing block into a rule file. Layer 1 only; use the git hook and CI.

## 5. The model does not change the enforcement

DeepSeek, Qwen, a local Ollama build and a frontier model all hit the same `pre-commit` hook, the same `test-cmd`, the same required status check. Enforcement is about the repo, not the weights.

What does change is how much you need. A weaker or cheaper model skips tests more often, claims a green it never ran more often, and reaches for `skip(true)` under pressure more often. So on those setups: keep `auto-test: true` on, keep the git hooks installed (`scripts/install-hooks.sh --check` in CI so a stale clone is visible), and turn on `STOP_GATE_REQUIRE_TEST=1` for [hooks/claude-stop-gate.sh](./hooks/claude-stop-gate.sh) where the tool supports a finish gate. More enforcement, not less.

## 6. Verify it works

| Step | How | Expected |
|---|---|---|
| 1. Tests run after an edit | Cursor: edit a covered source file. aider: any edit with `auto-test: true` | Cursor prints `[post-edit] GREEN — <target>`; aider prints the test command's output |
| 2. Red refuses the finish | Break an assertion by hand, edit the source again, let the agent finish | Cursor: `Do not finish yet. the last test run was RED ...`. aider: the failure is pasted and it tries to fix. Cline and Continue: nothing — this is why step 3 exists |
| 3. A `feat` with no test is rejected | `git commit -m "feat: thing"` with only source staged | `COMMIT REJECTED — no test added or updated for: feat: thing` |

## 7. Limits

| Tool | Cannot enforce | Fall back to |
|---|---|---|
| Cursor | Anything after a hook crash — hooks fail open unless `failClosed: true`; the `stop` hook can only ask for more turns, up to `loop_limit` | git hook + CI |
| Cline | Any blocking behaviour; the hook contract is undocumented | git hook + CI |
| aider | A finish gate; it can only run and retry `test-cmd` | git hook + CI |
| Continue | Everything beyond rules text | git hook + CI |

All four share the same real guarantee: [hooks/require-spec-for-feature.sh](./hooks/require-spec-for-feature.sh) installed as `commit-msg`, and [hooks/ci-required-check.yml](./hooks/ci-required-check.yml) as a required status check with admin bypass off.

## Sources & further reading

- Cursor rules — https://cursor.com/docs/context/rules · Cursor hooks — https://cursor.com/docs/agent/hooks
- Cline rules — https://docs.cline.bot/features/cline-rules · Cline hooks — https://docs.cline.bot/features/hooks · Cline DeepSeek — https://docs.cline.bot/provider-config/deepseek
- aider conventions — https://aider.chat/docs/usage/conventions.html · lint and test — https://aider.chat/docs/usage/lint-test.html · config file — https://aider.chat/docs/config/aider_conf.html
- Continue rules — https://docs.continue.dev/customize/deep-dives/rules

## Related

- [README.md](./README.md) — the three layers and the provider-agnostic recipe
- [hooks/pre-commit-tests.sh](./hooks/pre-commit-tests.sh) · [hooks/require-spec-for-feature.sh](./hooks/require-spec-for-feature.sh) · [hooks/claude-stop-gate.sh](./hooks/claude-stop-gate.sh)
- [../testing-from-zero.md](../testing-from-zero.md) — the layer table the instruction block points at

_Last reviewed: 2026-09-07._
