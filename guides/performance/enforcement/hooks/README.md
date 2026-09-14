# Performance Hooks and CI Artifacts

**Best used when:** the performance rules are written down and you want a machine to check them on every edit, every commit and every PR.
**Read before:** copying any of these files into a repo.
**See also:** [../README.md](../README.md) · [../claude-code.md](../claude-code.md) · [../codex.md](../codex.md) · [../gemini-cli.md](../gemini-cli.md) · [../copilot.md](../copilot.md) · [../cursor-cline-aider.md](../cursor-cline-aider.md)

Two shell scripts (layer 2) and three CI artifacts (layer 3). Nothing here explains why a rule exists — that is in [../../performance-from-zero.md](../../performance-from-zero.md) and the stack guides.

## Install matrix

| File | Copy to | Wired by |
|---|---|---|
| `perf-review-checklist.sh` | `scripts/` | the hook script, `.git/hooks/pre-commit`, and CI |
| `perf-post-edit-hook.sh` | `.claude/hooks/`, `.codex/hooks/`, `.gemini/hooks/`, `.github/hooks/` or `.cursor/hooks/` | the tool's hook config — exact block in each per-tool file |
| `lighthouserc.json` | repo root, next to `package.json` | `lhci autorun` in CI |
| `k6-smoke.js` | `perf/k6-smoke.js` | `grafana/run-k6-action@v1` in CI |
| `github-actions-perf.yml` | `.github/workflows/perf.yml` | GitHub Actions; mark the three jobs as required checks |

```bash
mkdir -p scripts perf .claude/hooks .github/workflows && H=guides/performance/enforcement/hooks
cp $H/perf-review-checklist.sh scripts/ && cp $H/perf-post-edit-hook.sh .claude/hooks/
chmod +x scripts/perf-review-checklist.sh .claude/hooks/perf-post-edit-hook.sh
cp $H/k6-smoke.js perf/ && cp $H/lighthouserc.json . && cp $H/github-actions-perf.yml .github/workflows/perf.yml
```

The hook script looks for the checklist next to itself, then in `scripts/` under the project root (the layout above); set `PERF_CHECKLIST=<path>` when it lives anywhere else. `jq` is optional — without it a `sed` fallback reads the file path.

JSON carries no comments, so the verification note for `lighthouserc.json` lives here: its shape (`ci.collect`, `ci.assert.assertions`, `["error", {"maxNumericValue": N}]`, bytes for `resource-summary:script:size`) is Verified against https://github.com/GoogleChrome/lighthouse-ci/blob/main/docs/configuration.md on 2026-09-07. `lighthouserc.json` and `k6-smoke.js` carry hand-copied duplicates of the budget numbers; the source of truth is `perf-budgets.md` ([../README.md](../README.md) section 7) and a reviewer keeps the three equal. There is no sync.

## Patterns the checklist matches

| Id | Pattern | Verdict |
|---|---|---|
| F2 | `findAll(` on a line with no `Pageable` / `PageRequest` / `Sort` / `Limit` | unpaged read |
| F3 | `.findAll().stream()` | whole table in memory, filtered in the language |
| F3 | `ListView(` / `GridView(` with `children:` and `.map(` within 3 lines | every item built eagerly |
| F2 | `SELECT *` inside a query string | over-fetching columns |
| F1 | `for` / `forEach` / `map` with `repository.` or `await …find\|get\|fetch\|query` within 3 lines | call inside a loop |
| F4 | `readFileSync` / `execSync` under `src/` in `.ts` / `.js` | blocking I/O on the hot path |
| F2 | `.objects.all()` with no slice in `.py` | unpaged queryset |
| F1 | `.map(` with `useEffect(` and `fetch(` within 3 lines | one request per rendered row |

Extensions scanned: `.java .kt .ts .tsx .js .jsx .dart .py .go`. Everything else is skipped.

## Suppression

These are shapes, not facts, so false positives are expected. Put the marker on the line, with a reason:

```java
List<Country> all = countryRepository.findAll(); // perf:ok bounded reference table, 250 rows max
```

`# perf:ok <reason>` works for Python and shell comment styles. The reason is what a reviewer reads; a bare `perf:ok` is a bug in your review, not in the script.

## Try it

Three BAD lines, one per stack. Save them and run the checklist.

```java
// Foo.java — expect [F3] and [F1]
var active = repository.findAll().stream().filter(u -> u.isActive()).toList();
for (Order o : orders) { var items = itemRepository.findByOrderId(o.getId()); }
```

```dart
// list.dart — expect [F3]
ListView(children: items.map((i) => ItemTile(item: i)).toList());
```

```typescript
// src/a.ts — expect [F1]
rows.map(async (r) => { await repo.find(r.id); });
```

```bash
bash scripts/perf-review-checklist.sh /tmp/Foo.java /tmp/list.dart src/a.ts
# /tmp/Foo.java:2: [F3] findAll().stream() loads the whole table into memory — see guides/...
echo '{"tool_input":{"file_path":"src/Foo.java"}}' | bash .claude/hooks/perf-post-edit-hook.sh
# findings on stderr, one summary line on stdout
```

Both exit `0` in report-only mode and `2` when `PERF_HOOK_BLOCK=1` and there is at least one finding — the mode CI and a blocking hook use. With no arguments the checklist scans everything changed in the working tree — staged, unstaged and untracked — so a `Stop` hook sees the file the agent just created; `--staged` is the pre-commit shape; `--diff <ref>` is the CI shape and exits `1`, loudly, when the ref does not resolve instead of passing an empty diff.

## Related

- [../README.md](../README.md) — the three layers, the instruction block, the recipe
- [../../backend-performance-guide.md](../../backend-performance-guide.md) · [../../frontend-performance-guide.md](../../frontend-performance-guide.md) · [../../mobile-performance-guide.md](../../mobile-performance-guide.md)

_Last reviewed: 2026-09-07._
