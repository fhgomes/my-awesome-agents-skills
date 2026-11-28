# Parity Check — Same Input, Same Data, Old Path Versus New Path

**SKILL.md** — drop-in skill for any runtime that loads a SKILL.md.

## What it does

When an integration is replaced, the screens keep working while the data quietly changes: a renamed
field, an empty list that became null, a date in another time zone, a default the old client used to
fill in. This skill makes the agent prove equivalence before any caller is switched.

- Sets up two test-only routes: one returns the old client's final output exactly as production gets
  it, the other returns what the new path will hand to callers.
- Calls both with the same inputs and compares the JSON field by field: names, nesting, lists, null
  versus empty, dates, numbers, defaults, codes and error shapes.
- Treats every difference as a bug until someone accepts it; normalizes only what no consumer sees.
- Runs reads first, and writes only against isolated non-production copies.

## What's inside

- `SKILL.md` — the setup, the comparison checklist, the procedure and the rules.
- `assets/parity-read.k6.js` — a generic [k6](https://k6.io/) script for read operations: base URL,
  routes and ids from environment variables, a `compare` function that lists every difference, and
  thresholds that fail the run on any of them.

This folder is **self-contained** — copy it into any runtime that loads a SKILL.md and it works as-is.
The script needs only k6.

## See also (optional)

[../reverse-trace/](../reverse-trace/) tells you which operations and paths to check first.
[../companion-map/](../companion-map/) shows who consumes each contract. Both are optional.
