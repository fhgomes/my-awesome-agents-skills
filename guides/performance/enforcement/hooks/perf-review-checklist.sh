#!/usr/bin/env bash
# perf-review-checklist.sh — grep the diff (or given files) for the performance
# anti-patterns an AI coding tool writes by default.
#
# WHAT IT GUARDS
#   Layer 2 (developer machine) and layer 3 (CI) of guides/performance/enforcement.
#   It is a heuristic linter, not a profiler: it finds shapes, never facts. It cannot
#   see a missing index, a wasted render or a missing timeout. Those need EXPLAIN and
#   a profiler — see guides/performance/enforcement/README.md section 6.
#
# INSTALL
#   cp perf-review-checklist.sh scripts/ && chmod +x scripts/perf-review-checklist.sh
#   Wire it into a tool hook via perf-post-edit-hook.sh, into .git/hooks/pre-commit
#   as `scripts/perf-review-checklist.sh --staged`, and into CI via github-actions-perf.yml.
#
# USAGE
#   perf-review-checklist.sh                      # everything changed in the working tree:
#                                                 # staged + unstaged + untracked (not ignored)
#   perf-review-checklist.sh --staged             # staged files only (pre-commit)
#   perf-review-checklist.sh --diff origin/main   # files changed against a ref (CI)
#   perf-review-checklist.sh src/Foo.java lib/a.dart
#
# PATTERNS (id = failure mode from guides/performance/performance-from-zero.md)
#   F2  findAll( on a line with no Pageable/PageRequest/Sort
#   F3  .findAll().stream()                              — whole table into memory
#   F3  ListView(/GridView( with children: and .map( within 3 lines
#   F2  SELECT * inside a query string
#   F1  repository/await .find|get|fetch|query inside for/forEach/map within 3 lines
#   F4  readFileSync/execSync under src/ in .ts/.js
#   F2  .objects.all() with no slice in Python
#   F1  .map( with useEffect( + fetch( within 3 lines
#
# SUPPRESSION
#   Put `// perf:ok <reason>` (or `# perf:ok <reason>`) on the offending line.
#   False positives are expected; a suppression with a reason is a review artifact.
#
# ENV
#   PERF_HOOK_BLOCK=1   exit 2 when there is at least one finding (blocking mode)
#
# EXIT CODES
#   0  no findings, or findings in report-only mode (the default)
#   1  usage error, or --diff <ref> does not resolve (fails loudly, never silently passes)
#   2  findings and PERF_HOOK_BLOCK=1
#
# PORTABILITY
#   bash 3.2+, POSIX awk/sed/grep; runs on macOS and Linux. No GNU-only flags.

set -euo pipefail

MODE="worktree"; REF=""; FILES=()
while [ $# -gt 0 ]; do
  case "$1" in
    --staged) MODE="staged"; shift ;;
    --diff) MODE="diff"; REF="${2:-}"; [ -n "$REF" ] || { echo "--diff needs a ref" >&2; exit 1; }; shift 2 ;;
    -h|--help) sed -n '2,40p' "$0"; exit 0 ;;
    -*) echo "unknown option: $1" >&2; exit 1 ;;
    *) FILES+=("$1"); MODE="args"; shift ;;
  esac
done

case "$MODE" in
  staged)   FILE_LIST="$(git diff --cached --name-only --diff-filter=ACMR 2>/dev/null || true)" ;;
  diff)
    git rev-parse --verify --quiet "$REF^{commit}" >/dev/null 2>&1 \
      || { echo "perf-review-checklist: --diff ref '$REF' does not resolve (is the base branch fetched?)" >&2; exit 1; }
    FILE_LIST="$(git diff --name-only --diff-filter=ACMR "$REF" 2>/dev/null || true)" ;;
  worktree)
    # staged + unstaged against HEAD, plus untracked files the agent just created
    FILE_LIST="$( { git diff --name-only --diff-filter=ACMR HEAD 2>/dev/null; git ls-files --others --exclude-standard 2>/dev/null; } | sort -u )" ;;
  args)     FILE_LIST="$(printf '%s\n' "${FILES[@]}")" ;;
esac

GUIDE_BE="guides/performance/backend-performance-guide.md"
GUIDE_FE="guides/performance/frontend-performance-guide.md"
GUIDE_MO="guides/performance/mobile-performance-guide.md"

scan() { # $1 = path
  awk -v F="$1" -v BE="$GUIDE_BE" -v FE="$GUIDE_FE" -v MO="$GUIDE_MO" '
    function report(n, id, msg, doc) { printf "%s:%d: [%s] %s — see %s\n", F, n, id, msg, doc }
    { line[NR] = $0 }
    END {
      for (i = 1; i <= NR; i++) {
        l = line[i]
        if (l ~ /perf:ok/) continue
        win = l
        for (j = i + 1; j <= i + 3 && j <= NR; j++) win = win " \n " line[j]
        u = toupper(l)

        if (l ~ /\.findAll\(\)[ \t]*\.stream\(\)/)
          report(i, "F3", "findAll().stream() loads the whole table into memory", BE)
        else if (l ~ /findAll\(/ && l !~ /Pageable|PageRequest|[Pp]ageable|Sort|Limit/)
          report(i, "F2", "findAll() without a page (page + size, max size 100)", BE)

        if (u ~ /SELECT[ \t]+\*/) report(i, "F2", "SELECT * in a query — project the columns the caller needs", BE)

        if (l ~ /(ListView|GridView)\(/ && win ~ /children:/ && win ~ /\.map\(/)
          report(i, "F3", "ListView(children: ...map()) builds every item — use ListView.builder", MO)

        if (l ~ /for[ \t]*\(|for [A-Za-z_]/ || l ~ /\.forEach\(|\.map\(/) {
          if (win ~ /[Rr]epository\.|[Rr]epo\.|await[ \t]+[A-Za-z_.]*\.(find|get|fetch|query)|\.(findBy|getBy|fetch|query)\(/)
            report(i, "F1", "possible query/HTTP call inside a loop — batch or join instead", BE)
        }

        if (F ~ /\.(ts|tsx|js|jsx)$/ && F ~ /(^|\/)src\// && l ~ /readFileSync|execSync/)
          report(i, "F4", "blocking I/O on the hot path — use the async API", FE)

        if (F ~ /\.py$/ && l ~ /\.objects\.all\(\)/ && l !~ /\[/)
          report(i, "F2", ".objects.all() without a slice — paginate the queryset", BE)

        if (F ~ /\.(ts|tsx|js|jsx)$/ && l ~ /\.map\(/ && win ~ /useEffect\(/ && win ~ /fetch\(/)
          report(i, "F1", "fetch per rendered row — fetch once above the list", FE)
      }
    }
  ' "$1"
}

FOUND=0
while IFS= read -r f; do
  [ -n "$f" ] || continue
  [ -f "$f" ] || continue
  case "$f" in
    *.java|*.kt|*.ts|*.tsx|*.js|*.jsx|*.dart|*.py|*.go) ;;
    *) continue ;;
  esac
  out="$(scan "$f")"
  if [ -n "$out" ]; then
    printf '%s\n' "$out"
    FOUND=$((FOUND + $(printf '%s\n' "$out" | wc -l | tr -d ' ')))
  fi
done <<EOF
$FILE_LIST
EOF

if [ "$FOUND" -eq 0 ]; then
  echo "perf-review-checklist: no findings."
  exit 0
fi

echo "perf-review-checklist: $FOUND finding(s). Suppress a false positive with 'perf:ok <reason>' on the line."
if [ "${PERF_HOOK_BLOCK:-0}" = "1" ]; then exit 2; fi
exit 0
