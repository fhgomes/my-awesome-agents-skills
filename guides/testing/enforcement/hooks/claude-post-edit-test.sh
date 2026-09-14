#!/usr/bin/env bash
# claude-post-edit-test.sh — after an agent edits a file, run the test that covers it.
#
# WHAT IT GUARDS
#   Nothing, by itself. It INFORMS: it always exits 0 so an edit is never blocked,
#   and it writes the verdict to a state file. claude-stop-gate.sh reads that file
#   and refuses to let the agent finish on red. Splitting the two keeps the edit
#   loop fast and puts the single blocking decision in one place.
#
# WIRE IT UP
#   Claude Code  .claude/settings.json  -> PostToolUse, matcher "Edit|Write|MultiEdit"
#   Gemini CLI   .gemini/settings.json  -> AfterTool,   matcher "write_file|replace"
#   Cursor       .cursor/hooks.json     -> afterFileEdit
#   Copilot      .github/hooks/*.json   -> postToolUse
#   Codex        .codex/hooks.json      -> PostToolUse, matcher "apply_patch"
#   See ../claude-code.md and siblings for the exact block per tool.
#
# STDIN: the hook event as JSON. The edited path is read from the FIRST "file_path"
#   key found anywhere in the payload, which covers the documented shapes:
#     Claude Code / Gemini CLI  .tool_input.file_path   (verified 2026-09-07)
#     Cursor                    .file_path              (verified 2026-09-07)
#     Copilot                   .toolArgs is "unknown" in the docs; a file_path key
#                               inside it is picked up if present  [unverified]
#     Codex                     sends a patch, never a path
#   When no path is found it falls back to the first changed file in the working tree.
#
# ENV: TEST_TIMEOUT (seconds, default 120), STATE_FILE, BASELINE_FILE,
#   GRADLE_MODULE (":backend"; auto-detected from the file path when unset).
#
# EXIT CODES: always 0 (PostToolUse informs; the Stop gate decides).

set -euo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-${GEMINI_PROJECT_DIR:-${CURSOR_PROJECT_DIR:-$PWD}}}"
STATE_DIR="$PROJECT_DIR/.git"; [ -d "$STATE_DIR" ] || STATE_DIR="${TMPDIR:-/tmp}"
STATE_FILE="${STATE_FILE:-$STATE_DIR/agent-test-state}"
TEST_TIMEOUT="${TEST_TIMEOUT:-120}"
BASELINE_FILE="${BASELINE_FILE:-$PROJECT_DIR/.testing-baseline}"
PYTHON="$(command -v python3 || command -v python || echo python3)"

PAYLOAD="$(cat || true)"
if command -v jq >/dev/null 2>&1; then
  FILE="$(printf '%s' "$PAYLOAD" | jq -r '[.. | objects | select(has("file_path")) | .file_path] | first // empty' 2>/dev/null || true)"
else
  FILE="$(printf '%s' "$PAYLOAD" | sed -n 's/.*"file_path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)"
fi
cd "$PROJECT_DIR"
[ -n "$FILE" ] || FILE="$(git diff --name-only HEAD 2>/dev/null | head -1 || true)"
case "$FILE" in "$PROJECT_DIR"/*) FILE="${FILE#"$PROJECT_DIR"/}" ;; esac   # absolute -> repo-relative

# Hash of the NAMES and CONTENTS of every uncommitted file (staged, unstaged, untracked).
# The Stop gate compares it with the hash recorded here: a green recorded on different
# content is stale. Staging a file does not change it; editing one does.
tree_hash() {
  { git diff HEAD --name-only -- . 2>/dev/null; git ls-files --others --exclude-standard 2>/dev/null; } \
    | sort -u | while IFS= read -r f; do printf '%s\n' "$f"; [ -f "$f" ] && cat "$f"; done \
    | cksum | awk '{print $1}'
}
write_state() { printf 'STATUS=%s\nTARGET=%s\nDIFF_HASH=%s\nAT=%s\n' "$1" "${2:-none}" "$(tree_hash)" "$(date -u +%FT%TZ)" > "$STATE_FILE"; }
prior_status() {
  local v=""; [ -f "$STATE_FILE" ] && v="$(sed -n 's/^STATUS=//p' "$STATE_FILE" | head -1)"
  echo "${v:-UNKNOWN}"
}

# Docs, config and lockfiles are a no-op: keep the previous verdict, refresh the hash.
case "$FILE" in
  ""|*.md|*.txt|*.yml|*.yaml|*.json|*.toml|*.lock|*.png|*.svg)
    write_state "$(prior_status)" "no-op:${FILE:-none}"; echo "[post-edit] no test mapped for '${FILE:-<none>}' — no-op."; exit 0 ;;
esac
if [ -f "$BASELINE_FILE" ] && grep -vE '^[[:space:]]*(#|$)' "$BASELINE_FILE" | grep -qF -- "$FILE"; then
  write_state "$(prior_status)" "baseline:$FILE"; echo "[post-edit] $FILE is in the known-red baseline — not judged."; exit 0
fi

# Gradle module = first path segment that owns a build file (":orders" for orders/src/...).
# A bare `./gradlew test --tests X` fails in multi-module builds ("No tests found" in siblings).
gradle_module() {
  local top="${1%%/*}"
  if [ -n "${GRADLE_MODULE:-}" ]; then printf '%s' "$GRADLE_MODULE"
  elif [ "$top" != "$1" ] && { [ -f "$top/build.gradle" ] || [ -f "$top/build.gradle.kts" ]; }; then printf ':%s' "$top"
  else printf ''; fi
}

base="$(basename "$FILE")"; CMD=""; TARGET="$FILE"
case "$FILE" in
  *.java|*.kt)
    if [ -x ./gradlew ]; then CMD="./gradlew $(gradle_module "$FILE"):test --tests '*${base%.*}*'"
    elif [ -f pom.xml ]; then CMD="./mvnw -q -Dtest='*${base%.*}*' -Dsurefire.failIfNoSpecifiedTests=false test"; fi ;;
  *.ts|*.tsx|*.js|*.jsx)
    if [ -f package.json ] && grep -q '"vitest"' package.json; then CMD="npx --no-install vitest related --run $FILE"
    elif [ -f package.json ]; then CMD="npm test --silent"; fi ;;
  *.dart)
    t="test/${FILE#lib/}"; t="${t%.dart}_test.dart"
    case "$FILE" in *_test.dart) t="$FILE" ;; esac
    if [ -f "$t" ]; then CMD="flutter test $t"; TARGET="$t"; fi ;;
  *.go)   [ -f go.mod ] && CMD="go test ./$(dirname "$FILE")" ;;
  *.py)   CMD="$PYTHON -m pytest -q $(dirname "$FILE")" ;;
esac

if [ -z "$CMD" ]; then
  write_state NOTEST "$TARGET"; echo "[post-edit] no test command maps to $FILE — recorded as NOTEST."; exit 0
fi

echo "[post-edit] $CMD"
if timeout "$TEST_TIMEOUT" bash -c "$CMD" >/dev/null 2>&1; then
  write_state GREEN "$TARGET"; echo "[post-edit] GREEN — $TARGET"
else
  code=$?
  write_state RED "$TARGET"
  [ "$code" -eq 124 ] && echo "[post-edit] TIMEOUT after ${TEST_TIMEOUT}s — recorded as RED ($TARGET)" \
                      || echo "[post-edit] RED (exit $code) — $TARGET. Run it yourself: $CMD"
fi
exit 0
