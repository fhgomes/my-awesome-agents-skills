#!/usr/bin/env bash
# require-spec-for-feature.sh — a feat/fix commit that touches code must also touch a test.
#
# WHAT IT GUARDS
#   The rule "every fix or feature ships test coverage at the layer where the bug
#   lives". Only `feat:` and `fix:` subjects are checked — docs, chore, refactor,
#   style and build commits pass untouched. The escape hatch is explicit and
#   reviewable: "[skip-tests] reason: <why>" in the commit body.
#
# INSTALL (repo root): copy to scripts/git-hooks/commit-msg, chmod +x, copy into
#   .git/hooks/commit-msg. `commit-msg` is the right event: "$1" is the message
#   file, so the subject and body always exist. It also runs from pre-commit if
#   .git/COMMIT_EDITMSG is already written, but that is not guaranteed.
#
# CI MODE: with --range <base>..<head> it checks every commit in a range instead
#   of the staged set — that is how the spec-guard job in ci-required-check.yml
#   runs it, so a `--no-verify` commit still gets caught before merge.
#
# ENV: CODE_GLOBS (default 'src/|web/|lib/|app/'), TEST_GLOBS (default below).
#
# EXIT CODES
#   0  not a feat/fix, a test was touched, or a documented exemption was present
#   1  COMMIT REJECTED — feat/fix without a test and without a reason

set -euo pipefail

CODE_GLOBS="${CODE_GLOBS:-^(src/|web/|lib/|app/|server/|internal/)}"
TEST_GLOBS="${TEST_GLOBS:-(^|/)(test|tests|e2e|__tests__|spec)/|\.(test|spec)\.[jt]sx?$|_test\.(dart|go|py)$|Test(s)?\.(java|kt)$}"

reject() {
  cat >&2 <<MSG

COMMIT REJECTED — $1
  Add or update a test at the layer where the change lives, OR state the
  exemption in the commit body:
    [skip-tests] reason: <why this commit does not need a test>
  Examples that are accepted in review:
    [skip-tests] reason: CSS-only change, no logic
    [skip-tests] reason: covered by existing checkout-flow spec
  "no time" is not a reason. See ../README.md, section "The skip trailer".

MSG
  exit 1
}

check_commit() { # $1 = subject, $2 = body, $3 = newline-separated file list
  local subject="$1" body="$2" files="$3"
  echo "$subject" | grep -qE '^(feat|fix)(\(.+\))?!?:' || return 0
  echo "$files" | grep -qE "$CODE_GLOBS" || return 0
  if echo "$files" | grep -qE "$TEST_GLOBS"; then
    echo "[require-spec] test file touched — ok."
    return 0
  fi
  if echo "$body" | grep -qE '\[(skip-tests|skip-e2e)\] reason: *[^ ]'; then
    echo "[require-spec] documented exemption accepted for: $subject"
    return 0
  fi
  reject "no test added or updated for: $subject"
}

if [ "${1:-}" = "--range" ]; then
  RANGE="${2:?usage: require-spec-for-feature.sh --range <base>..<head>}"
  while IFS= read -r sha; do
    [ -n "$sha" ] || continue
    check_commit \
      "$(git log -1 --format=%s "$sha")" \
      "$(git log -1 --format=%b "$sha")" \
      "$(git show --name-only --format= "$sha")"
  done < <(git rev-list --no-merges "$RANGE")
  echo "[require-spec] range $RANGE clean."
  exit 0
fi

MSG_FILE="${1:-}"
if [ -z "$MSG_FILE" ] || [ ! -f "$MSG_FILE" ]; then
  GIT_DIR_PATH="$(git rev-parse --git-dir)"
  MSG_FILE="$GIT_DIR_PATH/COMMIT_EDITMSG"
  # pre-commit can run before the message exists; nothing to judge, so pass.
  [ -f "$MSG_FILE" ] || { echo "[require-spec] no commit message yet — install as commit-msg to enforce."; exit 0; }
fi

# An editor-composed message carries git's "#" comment lines and may start with blank
# lines; strip both so the subject is the first real line, as git itself will see it.
CLEAN="$(grep -vE '^#' "$MSG_FILE" | sed '/./,$!d')"
check_commit \
  "$(printf '%s\n' "$CLEAN" | head -1)" \
  "$(printf '%s\n' "$CLEAN" | tail -n +2)" \
  "$(git diff --cached --name-only --diff-filter=ACMR || true)"
exit 0
