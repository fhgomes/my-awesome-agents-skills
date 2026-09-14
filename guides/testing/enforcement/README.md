# Testing Enforcement

**Best used when:** the testing rules are agreed and still not followed — by people, by an AI coding tool, or by both — and you want the ones that matter to be impossible to skip rather than merely written down.
**Read before:** adding a hook, writing a `CLAUDE.md`/`AGENTS.md` testing section, or turning on a branch protection rule.
**See also:** [../testing-from-zero.md](../testing-from-zero.md) · [claude-code.md](./claude-code.md) · [codex.md](./codex.md) · [gemini-cli.md](./gemini-cli.md) · [copilot.md](./copilot.md) · [cursor-cline-aider.md](./cursor-cline-aider.md) · [../../../skills/test-engineer/SKILL.md](../../../skills/test-engineer/SKILL.md)

The guides in `guides/testing/` recommend. This directory enforces. They are separate on purpose, and the reason is written into the official docs of the tool most people are using.

---

## 1. Why enforcement is a separate file set

An instruction file is read, not obeyed. Anthropic says so about its own format:

> "Claude treats them as context, not enforced configuration. To block an action regardless of what Claude decides, use a PreToolUse hook."
> — Claude Code memory documentation, https://code.claude.com/docs/en/memory (read 2026-09-07)

The same is true of `AGENTS.md`, `GEMINI.md`, `.github/copilot-instructions.md`, `.cursor/rules/`, `.clinerules/` and `CONVENTIONS.md`. They shape behaviour. They raise the odds. On a long turn, with a full context window and a failing build, they lose to whatever the model decides next. A rule you care about needs a layer that does not depend on a decision.

Hooks are that layer — but only on the machine that has them installed, and only for the tool that reads them. A teammate who clones the repo and never runs the installer has none. `git commit --no-verify` skips the git ones. Switching from Cursor to Codex switches hook files entirely.

CI is the only layer that does not care which tool, which machine or which human produced the change. That is the whole argument: **layers 1 and 2 are conveniences, layer 3 is the guarantee.**

## 2. The three layers

| Layer | Mechanism | CAN guarantee | CANNOT | Bypassed by | Cost to set up |
|---|---|---|---|---|---|
| 1. Instructions | `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md`, `.cursor/rules/`, `.clinerules/`, `CONVENTIONS.md` | That the agent knows the rule, the layer table and the single-test command | Nothing. It blocks no action | A model that forgets, a long context, a human who never read it | 15 minutes, once |
| 2. Hooks | Tool lifecycle hooks (post-edit, stop/finish) + git `pre-commit` / `commit-msg` | Tests actually run after an edit; a turn or a commit is refused while red | Protecting a clone that never installed them, or a tool with no hook support | `--no-verify`, a different tool, an uninstalled clone, `HUSKY=0` | An afternoon, plus upkeep |
| 3. CI required check + branch protection | GitHub Actions (or equivalent) + "require status checks" on the default branch | That nothing merges while the suite is red or a `feat` has no test | Stopping a bad local commit; it acts at merge time | Repo admins — so **disable admin bypass** | An afternoon, then near zero |

Run all three. They fail in different directions: layer 1 catches the honest mistake, layer 2 catches it in seconds instead of minutes, layer 3 catches everything else.

## 3. What each layer should carry

| Layer | Put in it | Keep out of it |
|---|---|---|
| Instructions | The rule ("every feat/fix ships a test at the layer where the bug lives"), the single-test command, the full-suite command, a pointer to the layer table, the known-red baseline location, the `[skip-tests] reason:` trailer | The whole testing guide. An instruction file over ~200 lines stops being read |
| Hooks | Run the *affected* tests after an edit; refuse to finish or commit on red; require a test file in a `feat`/`fix` commit; block a diff that adds `@Disabled` / `.only(` / `skip(true` | The full suite. Minutes per turn is how a hook gets uninstalled |
| CI | Full suite with a clean test task, coverage ratchet on new code, spec-coverage guard, `forbidOnly` for Playwright, artifact upload on failure | Anything that needs a developer's local state |

## 4. What each tool can actually enforce

Facts below were read from each vendor's current documentation on 2026-09-07; per-tool files carry the exact URLs and the config blocks. `[verify]` means the vendor does not document it well enough to copy.

| Tool | Instruction file | Path-scoped rules | Reads AGENTS.md | Post-edit hook | Stop / finish hook | Pre-commit equivalent | Notes |
|---|---|---|---|---|---|---|---|
| Claude Code | `CLAUDE.md` (root or `.claude/`) | `.claude/rules/*.md`, `paths:` frontmatter | No — import `@AGENTS.md` or symlink | `PostToolUse`, matcher `Edit\|Write\|MultiEdit`; stdin `tool_input.file_path` | `Stop`, `SubagentStop` | git hook | Exit 2 + stderr blocks, or JSON `{"decision":"block","reason"}`; check `stop_hook_active` or you loop |
| OpenAI Codex | `AGENTS.md` | Nearest `AGENTS.md` wins per directory | Yes, natively | `PostToolUse`, matcher `apply_patch` (a patch, no file path) | `Stop`, sends `stop_hook_active` | git hook | Project hooks load only when the project is trusted |
| Gemini CLI | `GEMINI.md` | Directory hierarchy; globs `[verify]` | Via `context.fileName` setting | `AfterTool`, matcher `write_file\|replace`; stdin `tool_input.file_path` | `AfterAgent`, sends `stop_hook_active` | git hook | `timeout` is milliseconds; stdout must be ONLY the JSON |
| GitHub Copilot (VS Code, cloud agent, CLI) | `.github/copilot-instructions.md` | `.github/instructions/*.instructions.md`, `applyTo:` — cloud agent + code review only | Yes | `postToolUse`; stdin `toolArgs` (shape undocumented) | `agentStop` — fires in the cloud agent too; blocks only via JSON `{"decision":"block"}`, exit 2 is a warning | git hook locally; CI for the cloud agent | Hook files must be on the default branch for the cloud agent to see them |
| Cursor | `.cursor/rules/*.mdc` | `globs:` frontmatter | Yes | `afterFileEdit`; stdin `file_path` | `stop` — answers with `followup_message`, capped by `loop_limit` | git hook | Exit 2 denies on tool events; hooks fail open unless `failClosed`; scripts need `chmod +x` |
| Cline | `.clinerules/*.md` | `paths:` frontmatter | Yes (also `.cursorrules`) | `PostToolUse` `[verify]` | `TaskComplete` `[verify]` | git hook | Hook contract points at SDK plugins and is not documented — do not rely on it |
| aider | `CONVENTIONS.md` via `.aider.conf.yml` | No | Via `read: [AGENTS.md]` | `auto-test: true` runs `test-cmd` after every edit | None | git hook | `auto-test` IS aider's enforcement; there is no hook system |
| Continue | `.continue/rules/*.md` | `globs:` / `regex:` frontmatter | Not documented | None documented | None documented | git hook | Rules verified; no hooks in the docs |
| Any OpenAI-compatible model (DeepSeek, Qwen, local Ollama) | Inherits the host tool's row | Inherits | Inherits | Inherits | Inherits | git hook | Enforcement does not care about the model. A weaker model needs MORE of it, not less |

## 5. The provider-agnostic recipe

Three artifacts. Set them up in this order; each one works without the next.

### (a) One instruction block, one canonical file

Put this in `AGENTS.md` at the repo root and replace the two placeholders. Every tool in the table above either reads `AGENTS.md` natively or can be pointed at it in one line.

```markdown
## Testing (non-negotiable)

- Every `feat`/`fix` ships a test at the layer where the bug lives.
  If you fix a bug, write the test that would have caught it.
- Choose the layer BEFORE writing: pure logic -> unit; anything touching a database,
  auth, transactions or HTTP status -> integration with a real dependency;
  a cross-page user flow -> E2E. Layer table: `guides/testing/testing-from-zero.md`.
- Single test: `<SINGLE_TEST_CMD>` · Full suite: `<FULL_SUITE_CMD>`
- Known-red baseline: `docs/testing.md`. Read it before judging a red as yours.
- Red then green: run the new test before the fix and paste the failure, run it after
  and paste the pass, and state the test count before -> after.
- Never weaken an assertion, narrow a test filter to hide a failure, or add
  `@Disabled` / `test.skip(true)` / `.only(` / `xit(` to reach green.
- No test for this change? Put it in the commit body: `[skip-tests] reason: <why>`.
  "No time" is not a reason.
```

Then the pointer files, one line each, for the tools that do not read `AGENTS.md`:

| Tool | File | Content |
|---|---|---|
| Claude Code | `CLAUDE.md` | `@AGENTS.md` (an import) — or `ln -s AGENTS.md CLAUDE.md` |
| Gemini CLI | `.gemini/settings.json` | `{"context": {"fileName": ["AGENTS.md", "GEMINI.md"]}}` |
| aider | `.aider.conf.yml` | `read: [AGENTS.md]` |
| Codex, Cursor, Copilot, Cline | — | Nothing. They read `AGENTS.md` already |

### (b) Git hooks, installed by a script that is safe to re-run

Two scripts from [hooks/](./hooks/) do the work: `pre-commit-tests.sh` runs the tests affected by the staged files, `require-spec-for-feature.sh` rejects a `feat`/`fix` that touches code and no test. Copy them into `scripts/git-hooks/` as `pre-commit` and `commit-msg`, then install with:

```bash
#!/usr/bin/env bash
# scripts/install-hooks.sh — idempotent. Run once per clone; run --check in CI.
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
SRC="$ROOT/scripts/git-hooks"; DST="$ROOT/.git/hooks"; ERRORS=0
for hook in pre-commit commit-msg; do
  [ -f "$SRC/$hook" ] || continue
  if [ "${1:-}" = "--check" ]; then
    if diff -q "$SRC/$hook" "$DST/$hook" >/dev/null 2>&1; then echo "ok    $hook"
    else echo "STALE $hook"; ERRORS=$((ERRORS + 1)); fi
    continue
  fi
  cp "$SRC/$hook" "$DST/$hook"; chmod +x "$DST/$hook"; echo "installed $hook"
done
[ "$ERRORS" -eq 0 ] || { echo "run scripts/install-hooks.sh"; exit 1; }
```

Hooks live in `scripts/git-hooks/` because `.git/hooks/` is not versioned — a hook nobody can review is a hook nobody trusts. `--check` in CI tells you who is running an old copy. No `sudo`, no `chown`: a hook that needs root is a hook that will be disabled.

One timing detail: `pre-commit` runs before an editor-composed message exists, so `pre-commit-tests.sh` can only honour the `[skip-tests]` trailer for `git commit -m`. `require-spec-for-feature.sh` runs as `commit-msg`, where the message always exists. If you want the trailer to waive the test run in every flow, install `pre-commit-tests.sh` as `commit-msg` too and chain the two.

### (c) The CI required check

[hooks/ci-required-check.yml](./hooks/ci-required-check.yml) runs the backend suite, the frontend suite, Playwright, and a `spec-guard` job that replays `require-spec-for-feature.sh` over every commit in the PR — which is what catches the `--no-verify` commit and the clone that never installed anything. A final `required` job `needs:` all of them; that is the single check to mark required.

Branch protection: **Settings -> Rules -> Rulesets -> New branch ruleset** (or **Settings -> Branches -> Add rule**), target the default branch, enable **Require status checks to pass**, add `required`, and leave **"Do not allow bypassing the above settings"** ON. Admin bypass turns your only guarantee back into a convention.

## 6. The skip trailer

Not every change needs a test, and a rule with no honest exit gets routed around dishonestly. The exit is one line in the commit body:

```
[skip-tests] reason: CSS-only change, no logic
```

`[skip-e2e]` is accepted as an alias when the waiver is only about the browser suite. Both hooks and the CI `spec-guard` job honour it.

| Reason | Verdict |
|---|---|
| `docs-only` / README, comments, changelog | Accepted |
| `CSS-only change, no logic` | Accepted — until the diff also touches a component's behaviour |
| `covered by existing checkout-flow spec` | Accepted, and name the spec so a reviewer can open it |
| `config/dependency bump, covered by the full suite` | Accepted |
| `no time` / `will add later` / an empty reason | Rejected. "Later" has a measurable success rate and it is low |

Count them. `git log --grep='\[skip-tests\]' --since='1 week ago' --oneline | wc -l` in a weekly job is a smell metric: a number that climbs is a team telling you the tests are too slow, too flaky or too hard to write, and that is the thing to fix.

## 7. Do not

- **Do not run the full suite in a Stop/finish hook.** Minutes per turn is exactly how a hook gets uninstalled. Run the affected subset locally; the full suite belongs in CI.
- **Do not let a hook weaken tests.** A gate that auto-skips a failing test to let the commit through has removed the guard it was installed to protect. A weakened guard is a deleted guard.
- **Do not skip the known-red baseline check.** If the repo already has reds, a hook that fails on all of them is uninstalled the same day. Every script here reads an optional `.testing-baseline` file and never fails on what is listed there. Keep that file short and dated, and never let it grow into "ignore one known red" as guidance — a checklist that teaches people to skip a red is how a real one hides.
- **Do not trust a gate that finished suspiciously fast.** It has not passed, it has abstained. Gradle will report `BUILD SUCCESSFUL` in seconds with every test task `UP-TO-DATE`; the CI job here passes `cleanTest` for that reason. Read the task list, never just the exit code.

## 8. What is in this directory

| File | One line |
|---|---|
| [claude-code.md](./claude-code.md) | `CLAUDE.md` + `.claude/rules/`, `PostToolUse` and `Stop` hooks, the `@AGENTS.md` import |
| [codex.md](./codex.md) | Native `AGENTS.md`, `.codex/config.toml` trust and sandbox settings, `.codex/hooks.json` |
| [gemini-cli.md](./gemini-cli.md) | `GEMINI.md`, reading `AGENTS.md` via `context.fileName`, `AfterTool` / `AfterAgent` hooks |
| [copilot.md](./copilot.md) | `.github/copilot-instructions.md`, `applyTo:` path rules, `.github/hooks/`, why the cloud agent needs CI |
| [cursor-cline-aider.md](./cursor-cline-aider.md) | Cursor rules + hooks, Cline rules, aider `auto-test`, and running any model behind them |
| [hooks/pre-commit-tests.sh](./hooks/pre-commit-tests.sh) | Maps staged files to the tests that cover them and runs only those |
| [hooks/require-spec-for-feature.sh](./hooks/require-spec-for-feature.sh) | Rejects a `feat`/`fix` that touches code with no test and no stated reason |
| [hooks/claude-post-edit-test.sh](./hooks/claude-post-edit-test.sh) | After an agent edit, runs the affected test and records the verdict; reads `file_path` from any tool's payload |
| [hooks/claude-stop-gate.sh](./hooks/claude-stop-gate.sh) | Refuses "done" on red, on a stale green, or on a diff that adds a skip marker; exit 2 by default, JSON with `STOP_GATE_JSON` for Copilot and Cursor |
| [hooks/ci-required-check.yml](./hooks/ci-required-check.yml) | The GitHub Actions workflow and the single job to mark required |

## Sources & further reading

- Claude Code memory and hooks — https://code.claude.com/docs/en/memory · https://code.claude.com/docs/en/hooks
- OpenAI Codex config and hooks — https://learn.chatgpt.com/docs/config-file/config-reference · https://learn.chatgpt.com/docs/hooks
- Gemini CLI hooks and context files — https://geminicli.com/docs/hooks/ · https://geminicli.com/docs/cli/gemini-md/
- GitHub Copilot instructions and hooks — https://docs.github.com/en/copilot/how-tos/configure-custom-instructions/add-repository-instructions · https://docs.github.com/en/copilot/reference/hooks-reference
- Cursor rules and hooks — https://cursor.com/docs/context/rules · https://cursor.com/docs/agent/hooks
- GitHub branch protection and rulesets — https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches
- The `AGENTS.md` cross-tool convention — https://agents.md/

## Related

- [../testing-from-zero.md](../testing-from-zero.md) — what to enforce, and why those rules and not others
- [../backend-testing-guide.md](../backend-testing-guide.md) · [../frontend-testing-guide.md](../frontend-testing-guide.md) · [../mobile-testing-guide.md](../mobile-testing-guide.md) · [../e2e-testing-guide.md](../e2e-testing-guide.md)
- [../../../skills/test-engineer/SKILL.md](../../../skills/test-engineer/SKILL.md) — the agent skill that applies the rules this directory enforces

_Last reviewed: 2026-09-07._
