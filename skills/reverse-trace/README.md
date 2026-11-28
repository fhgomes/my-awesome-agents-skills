# Reverse Trace — From The Final Call Back To The Screen

**SKILL.md** — drop-in skill for any runtime that loads a SKILL.md.

## What it does

Before you replace an integration, you need to know everything that reaches it. This skill starts at
the final call (a SOAP or REST client method, a query, a publish) and walks backwards: services,
endpoints and jobs, then the front-end calls, the components and the screens, then the tests. The
result is a table with one row per path and a coverage grade, and that table is the test plan.

- Walks the chain hop by hop with `file:line` evidence, including the callers "find usages" misses
  (interfaces, wiring by name, workflow delegates, wrappers, duplicated helpers).
- Crosses from the back end into the front end and the E2E repository.
- Grades each path `covered`, `happy-path` or `not-covered` after reading the assertions.
- Fills an action per path: run the existing test, add the missing cases, or the exact manual steps.

## What's inside

- `SKILL.md` — the procedure, the grading table and the rules.
- `assets/trace-template.md` — the per-sink trace file.
- `examples/catalog-get-item/` — a finished trace and its `trace-map.csv` for an invented system.

This folder is **self-contained** — copy it into any runtime that loads a SKILL.md and it works as-is.

## See also (optional)

[../companion-map/](../companion-map/) tells the agent which repositories exist and how they call
each other. [../parity-check/](../parity-check/) proves the old and the new path return the same
data. Both are optional.
