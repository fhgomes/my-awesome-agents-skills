#!/usr/bin/env bash
# claude-stop-gate.sh — refuse to let the agent say "done" on red, stale or weakened tests.
#
# WHAT IT GUARDS
#   Three failure modes that instruction files never catch:
#     1. the last affected-test run was RED;
#     2. source changed after the last GREEN, so the green is stale;
#     3. the uncommitted diff ADDS a skip marker (@Disabled, test.skip(true, .only(,
#        xit(, fit(, @Ignore, t.Skip(, @pytest.mark.skip) — "a weakened guard is a
#        deleted guard".
#   It reads the state file written by claude-post-edit-test.sh. It never runs the
#   full suite: that is CI's job and minutes per turn is how a hook gets uninstalled.
#
# WIRE IT UP (verified against each vendor's docs on 2026-09-07, see ../<tool>.md)
#   Claude Code  .claude/settings.json -> "Stop" (and "SubagentStop")   exit 2 + stderr
#   Codex        .codex/hooks.json     -> "Stop"                        exit 2 + stderr
#   Gemini CLI   .gemini/settings.json -> "AfterAgent"                  exit 2 + stderr
#   Copilot      .github/hooks/*.json  -> "agentStop"  exit 2 is only a WARNING there:
#                                          set STOP_GATE_JSON=1 to emit {"decision":"block"}
#   Cursor       .cursor/hooks.json    -> "stop"       set STOP_GATE_JSON=cursor to emit
#                                          {"followup_message": ...}
#
# LOOP GUARD: exits 0 when the payload says the agent is already continuing because
#   of this hook — `stop_hook_active: true` (Claude Code, Codex, Gemini, Copilot) or
#   Cursor's `loop_count` >= 1. Without it a blocking Stop hook fires forever.
#
# ENV: STATE_FILE, BASELINE_FILE, STOP_GATE_JSON (unset | 1 | cursor),
#   STOP_GATE_REQUIRE_TEST=1 (also block when the edited file had no test at all;
#   off by default so the first day is survivable).
#
# EXIT CODES
#   0  fine to stop (or, with STOP_GATE_JSON set, the block is on stdout as JSON)
#   2  BLOCK — stderr is shown to the agent as the reason and it keeps working

set -euo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-${GEMINI_PROJECT_DIR:-${CURSOR_PROJECT_DIR:-$PWD}}}"
STATE_DIR="$PROJECT_DIR/.git"; [ -d "$STATE_DIR" ] || STATE_DIR="${TMPDIR:-/tmp}"
STATE_FILE="${STATE_FILE:-$STATE_DIR/agent-test-state}"
BASELINE_FILE="${BASELINE_FILE:-$PROJECT_DIR/.testing-baseline}"

PAYLOAD="$(cat || true)"
if printf '%s' "$PAYLOAD" | grep -qE '"stop_hook_active"[[:space:]]*:[[:space:]]*true|"loop_count"[[:space:]]*:[[:space:]]*[1-9]'; then
  exit 0
fi

json_str() {  # one JSON string literal from $1
  if command -v jq >/dev/null 2>&1; then printf '%s' "$1" | jq -Rs .
  else printf '"%s"' "$(printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g' | tr '\n' ' ')"; fi
}
block() {
  local msg="Do not finish yet. $1"
  case "${STOP_GATE_JSON:-}" in
    cursor) printf '{"followup_message":%s}\n' "$(json_str "$msg")"; exit 0 ;;
    1|json|decision) printf '{"decision":"block","reason":%s}\n' "$(json_str "$msg")"; exit 0 ;;
  esac
  printf '%s\n' "$msg" >&2; exit 2
}
tree_hash() {  # must match claude-post-edit-test.sh: names + contents of uncommitted files
  { git diff HEAD --name-only -- . 2>/dev/null; git ls-files --others --exclude-standard 2>/dev/null; } \
    | sort -u | while IFS= read -r f; do printf '%s\n' "$f"; [ -f "$f" ] && cat "$f"; done \
    | cksum | awk '{print $1}'
}

cd "$PROJECT_DIR"

# 3. Weakened tests, checked first — it is the cheapest and the most damaging.
#    Staged, unstaged and untracked files are all inspected.
if git rev-parse --git-dir >/dev/null 2>&1; then
  MARKERS='@Disabled|@Ignore|test\.skip\(true|describe\.only\(|it\.only\(|test\.only\(|\bxit\(|\bfit\(|t\.Skip\(|@pytest\.mark\.skip'
  ADDED="$( { git diff -U0 HEAD -- . \
                | awk '/^\+\+\+ b\//{f=substr($0,7)} /^\+[^+]/{print f ": " substr($0,2)}' | grep -E "$MARKERS"
              git ls-files --others --exclude-standard -z | xargs -0 grep -HnE "$MARKERS" 2>/dev/null
            } | head -3 || true)"
  if [ -n "$ADDED" ]; then
    block "the diff adds a skip/disable marker. Remove it and make the test pass, or
delete the test with a stated reason. Lines:
$ADDED"
  fi
fi

[ -f "$STATE_FILE" ] || exit 0   # nothing was edited through the hook; nothing to judge
STATUS="$(sed -n 's/^STATUS=//p' "$STATE_FILE" | head -1)"
TARGET="$(sed -n 's/^TARGET=//p' "$STATE_FILE" | head -1)"
SEEN_HASH="$(sed -n 's/^DIFF_HASH=//p' "$STATE_FILE" | head -1)"
NOW_HASH="$(tree_hash)"

if [ -f "$BASELINE_FILE" ] && [ -n "${TARGET:-}" ] \
   && grep -vE '^[[:space:]]*(#|$)' "$BASELINE_FILE" | grep -qF -- "$TARGET"; then
  echo "[stop-gate] $TARGET is in the documented known-red baseline — not blocking." >&2
  exit 0
fi

case "${STATUS:-UNKNOWN}" in
  RED)
    block "the last test run was RED for $TARGET. Run it, paste the failure, fix it.
If it is a known red, add it to $BASELINE_FILE with a one-line reason." ;;
  NOTEST)
    if [ "${STOP_GATE_REQUIRE_TEST:-0}" = "1" ]; then
      block "you changed $TARGET and no test covers it. Add a test at the layer where
the behaviour lives, or state '[skip-tests] reason: <why>' in the commit body."
    fi ;;
esac

if [ "$STATUS" = "GREEN" ] && [ "${SEEN_HASH:-0}" != "$NOW_HASH" ]; then
  block "the last GREEN was recorded before the current set of changed files. The green
is stale — re-run the affected tests and paste the output before finishing."
fi

exit 0
