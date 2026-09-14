#!/usr/bin/env bash
# perf-post-edit-hook.sh — run the performance checklist on the file an agent just edited.
#
# WHAT IT GUARDS
#   Layer 2. It INFORMS by default: findings go to stderr (which is what the agent reads
#   back on a non-zero exit) and one summary line goes to stdout, and it exits 0 so an
#   edit is never blocked. Set PERF_HOOK_BLOCK=1 to make it block instead.
#
# WIRE IT UP (exact blocks per tool in ../claude-code.md and siblings)
#   Claude Code  .claude/settings.json  -> PostToolUse, matcher "Edit|Write"; optional Stop gate
#   Codex        .codex/hooks.json      -> PostToolUse (hooks are experimental, opt-in)
#   Gemini CLI   .gemini/settings.json  -> AfterTool, matcher "write_file|replace"
#   Copilot      .github/hooks/*.json   -> postToolUse
#   Cursor       .cursor/hooks.json     -> afterFileEdit
#   No hooks (Cline, aider) -> call it from .git/hooks/pre-commit instead.
#
# STDIN
#   The hook event as JSON. Reads, in order:
#     .tool_input.file_path   documented for Claude Code Edit/Write
#     .tool_input.path        NOT verified for any tool; kept so an undocumented payload
#                             still resolves a file
#     .toolArgs.file_path / .toolArgs.path   Copilot names its payload toolArgs; the key
#                             inside it was NOT verified
#   If none is present (a Stop event, an unknown payload, empty stdin) it falls back to
#   "everything changed in the working tree" — staged, unstaged and untracked files.
#
# ENV
#   PERF_CHECKLIST      path to perf-review-checklist.sh
#                       (default: next to this script, then <project>/scripts/)
#   PERF_HOOK_BLOCK=1   exit 2 on findings (blocking); default is report-only
#
# EXIT CODES
#   0  always, unless PERF_HOOK_BLOCK=1 and there was at least one finding
#   2  findings, blocking mode (stderr is the reason shown to the agent)

set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-${GEMINI_PROJECT_DIR:-${CURSOR_PROJECT_DIR:-$PWD}}}"

CHECKLIST="${PERF_CHECKLIST:-}"
if [ -z "$CHECKLIST" ]; then
  for c in "$HERE/perf-review-checklist.sh" "$PROJECT_DIR/scripts/perf-review-checklist.sh" "$PWD/scripts/perf-review-checklist.sh"; do
    if [ -f "$c" ]; then CHECKLIST="$c"; break; fi
  done
fi
if [ -z "$CHECKLIST" ] || [ ! -f "$CHECKLIST" ]; then
  echo "[perf] checklist not found (looked next to this script and in scripts/); set PERF_CHECKLIST" >&2
  exit 0
fi

PAYLOAD="$(cat 2>/dev/null || true)"
FILE=""
if command -v jq >/dev/null 2>&1; then
  FILE="$(printf '%s' "$PAYLOAD" | jq -r '.tool_input.file_path // .tool_input.path // .toolArgs.file_path // .toolArgs.path // empty' 2>/dev/null || true)"
else
  # No jq: first "file_path" value, else first "path" value. POSIX sed only (no GNU \| alternation).
  FILE="$(printf '%s' "$PAYLOAD" | sed -n 's/.*"file_path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)"
  [ -n "$FILE" ] || FILE="$(printf '%s' "$PAYLOAD" | sed -n 's/.*"path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)"
fi

cd "$PROJECT_DIR" 2>/dev/null || true

if [ -n "${FILE:-}" ] && [ -f "$FILE" ]; then
  OUT="$(bash "$CHECKLIST" "$FILE" 2>&1)"; CODE=$?
else
  OUT="$(bash "$CHECKLIST" 2>&1)"; CODE=$?
fi

COUNT="$(printf '%s\n' "$OUT" | grep -c ': \[F[0-9]\]' || true)"

if [ "$COUNT" -eq 0 ]; then
  echo "[perf] clean — ${FILE:-working tree}"
  exit 0
fi

printf '%s\n' "$OUT" >&2
echo "[perf] $COUNT performance finding(s) in ${FILE:-the working tree}. Fix them or add 'perf:ok <reason>' on the line."

if [ "${PERF_HOOK_BLOCK:-0}" = "1" ]; then exit 2; fi
exit 0
