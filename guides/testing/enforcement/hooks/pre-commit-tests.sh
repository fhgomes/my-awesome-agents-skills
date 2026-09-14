#!/usr/bin/env bash
# pre-commit-tests.sh — run the tests affected by the staged files, before the commit lands.
#
# WHAT IT GUARDS
#   Staged source files are mapped to the tests that cover them and only those tests
#   run. A red test rejects the commit. It is a convenience layer: a developer can
#   bypass it with `git commit --no-verify`, and a fresh clone does not have it at all.
#   The guarantee is the CI required check (see ../README.md).
# INSTALL (repo root): copy to scripts/git-hooks/pre-commit, chmod +x, then copy
#   into .git/hooks/pre-commit (or run scripts/install-hooks.sh — see ../README.md).
#
# SKIP TRAILER: "[skip-tests] reason: <why>" (alias "[skip-e2e] reason:") in the
#   commit body waives the run. With `git commit -m` the message file already
#   exists when pre-commit runs; with an editor it does not. If you depend on the
#   trailer, install this script as `commit-msg` as well — there "$1" is the
#   message file. Both paths are handled below.
#
# ENV: TESTS_CMD (run this instead of auto-detection), GRADLE_MODULE (e.g. ":backend";
#   when unset the module is derived from the file path: orders/src/... -> :orders),
#   BASELINE_FILE (known-red list, one id/file per line; default .testing-baseline).
#
# EXIT CODES
#   0  passed, nothing affected, or a documented skip trailer was present
#   1  COMMIT REJECTED — a mapped test failed

set -euo pipefail

BASELINE_FILE="${BASELINE_FILE:-.testing-baseline}"
PYTHON="$(command -v python3 || command -v python || echo python3)"

# Gradle module = first path segment that owns a build file (":orders" for orders/src/...).
# A bare `./gradlew test --tests X` fails in multi-module builds ("No tests found" in siblings).
gradle_module() {
  local top="${1%%/*}"
  if [ -n "${GRADLE_MODULE:-}" ]; then printf '%s' "$GRADLE_MODULE"
  elif [ "$top" != "$1" ] && { [ -f "$top/build.gradle" ] || [ -f "$top/build.gradle.kts" ]; }; then printf ':%s' "$top"
  else printf ''; fi
}

reject() { printf '\nCOMMIT REJECTED — %s\n\n' "$1"; exit 1; }
say()    { printf '[pre-commit] %s\n' "$1"; }

# Known-red baseline: a hook that fails on a repo that is already red gets
# uninstalled within a day. Anything listed here is never selected.
in_baseline() {
  [ -f "$BASELINE_FILE" ] || return 1
  grep -vE '^[[:space:]]*(#|$)' "$BASELINE_FILE" | grep -qF -- "$1"
}

MSG_FILE=""
if [ -n "${1:-}" ] && [ -f "${1:-}" ]; then
  MSG_FILE="$1"
elif GIT_DIR_PATH="$(git rev-parse --git-dir 2>/dev/null)" && [ -f "$GIT_DIR_PATH/COMMIT_EDITMSG" ]; then
  MSG_FILE="$GIT_DIR_PATH/COMMIT_EDITMSG"
fi
if [ -n "$MSG_FILE" ] && grep -qE '\[(skip-tests|skip-e2e)\] reason:' "$MSG_FILE"; then
  say "skip trailer present — affected tests not run (CI still runs the full suite)."
  exit 0
fi

STAGED="$(git diff --cached --name-only --diff-filter=ACM || true)"
[ -n "$STAGED" ] || { say "no staged files."; exit 0; }

declare -a JAVA=() TS=() DART=() GO=() PY=()
while IFS= read -r f; do
  [ -n "$f" ] || continue
  in_baseline "$f" && continue
  base="$(basename "$f")"
  case "$f" in
    *.java|*.kt) JAVA+=("$(gradle_module "$f")|*${base%.*}*") ;;   # "module|pattern"
    *.ts|*.tsx|*.js|*.jsx|*.mjs) TS+=("$f") ;;
    *_test.dart) DART+=("$f") ;;
    lib/*.dart) cand="test/${f#lib/}"; DART+=("${cand%.dart}_test.dart") ;;
    *.go) GO+=("./$(dirname "$f")") ;;
    *.py) PY+=("$(dirname "$f")") ;;
  esac
done <<< "$STAGED"

uniq_of() { printf '%s\n' "$@" | sort -u; }
RAN=0; FAILURES=""

if [ -n "${TESTS_CMD:-}" ]; then
  say "TESTS_CMD override: $TESTS_CMD"
  bash -c "$TESTS_CMD" || FAILURES="$FAILURES TESTS_CMD"; RAN=1
else
  if [ "${#JAVA[@]}" -gt 0 ] && [ -x ./gradlew ]; then
    # one gradle invocation per module: `:orders:test --tests '*A*' --tests '*B*'`
    for mod in $(uniq_of "${JAVA[@]%%|*}" | sed 's/^$/ROOT/'); do
      [ "$mod" = "ROOT" ] && mod=""
      args=(); while IFS= read -r p; do args+=(--tests "$p"); done \
        < <(printf '%s\n' "${JAVA[@]}" | awk -F'|' -v m="$mod" '$1==m {print $2}' | sort -u)
      say "gradle: ./gradlew ${mod}:test ${args[*]}"
      ./gradlew "${mod}:test" "${args[@]}" || FAILURES="$FAILURES gradle${mod}"; RAN=1
    done
  elif [ "${#JAVA[@]}" -gt 0 ] && [ -f pom.xml ]; then
    pat="$(uniq_of "${JAVA[@]#*|}" | tr '\n' ',' | sed 's/,$//')"
    say "maven: -Dtest=$pat"
    ./mvnw -q -Dtest="$pat" -Dsurefire.failIfNoSpecifiedTests=false test || FAILURES="$FAILURES maven"; RAN=1
  fi
  if [ "${#TS[@]}" -gt 0 ] && [ -f package.json ]; then
    if grep -q '"vitest"' package.json; then
      say "vitest related: $(uniq_of "${TS[@]}" | tr '\n' ' ')"
      npx --no-install vitest related --run $(uniq_of "${TS[@]}") || FAILURES="$FAILURES vitest"
    else
      say "npm test (no vitest detected — running the declared test script)"
      npm test --silent || FAILURES="$FAILURES npm"
    fi
    RAN=1
  fi
  if [ "${#DART[@]}" -gt 0 ] && [ -f pubspec.yaml ]; then
    existing=(); while IFS= read -r t; do [ -f "$t" ] && existing+=("$t"); done < <(uniq_of "${DART[@]}")
    if [ "${#existing[@]}" -gt 0 ]; then
      say "flutter test: ${existing[*]}"
      flutter test "${existing[@]}" || FAILURES="$FAILURES flutter"; RAN=1
    fi
  fi
  if [ "${#GO[@]}" -gt 0 ] && [ -f go.mod ]; then
    say "go test: $(uniq_of "${GO[@]}" | tr '\n' ' ')"
    go test $(uniq_of "${GO[@]}") || FAILURES="$FAILURES go"; RAN=1
  fi
  if [ "${#PY[@]}" -gt 0 ] && { [ -f pyproject.toml ] || [ -f setup.cfg ]; }; then
    say "pytest: $(uniq_of "${PY[@]}" | tr '\n' ' ')"
    "$PYTHON" -m pytest -q $(uniq_of "${PY[@]}") || FAILURES="$FAILURES pytest"; RAN=1
  fi
fi

if [ "$RAN" -eq 0 ]; then
  say "no test target mapped to the staged files (${#JAVA[@]} java, ${#TS[@]} ts, ${#DART[@]} dart, ${#GO[@]} go, ${#PY[@]} py) — nothing run."
  exit 0
fi
[ -z "$FAILURES" ] || reject "affected tests failed:$FAILURES
  Fix the test, or state the exemption in the commit body:
    [skip-tests] reason: <why this commit does not need a test>"
say "affected tests passed (${#JAVA[@]} java / ${#TS[@]} ts / ${#DART[@]} dart / ${#GO[@]} go / ${#PY[@]} py selectors)."
exit 0
