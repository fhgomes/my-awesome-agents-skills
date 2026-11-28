# Companion Map — One Harness For The Whole System

**SKILL.md** — drop-in skill for any runtime that loads a SKILL.md.

## What it does

Most harnesses stop at the edge of one repository. Real systems do not: the back end, the front end,
the end-to-end tests and the services they call usually live in separate repos. This skill makes the
agent map them and wire the result into every repo, so a question like "what does this change touch?"
gets an answer that crosses repository boundaries.

- Finds the companions from evidence (base URLs, clients, shared libraries, CI, queues), then asks the
  human what the config files do not show.
- Writes one card per repository: role, entry points, what it provides and consumes, how to run it,
  and the behaviour nobody tests but everybody depends on.
- Writes an index with the call graph, one arrow per line, each with the file that proves it.
- Adds a short "Companions" router to each repo's `AGENTS.md`, so the agent knows when to leave the
  repo it is in and which card to read.
- Ends with a proof question the agent could not answer before.

## What's inside

- `SKILL.md` — the procedure, the rules and the `AGENTS.md` block to paste.
- `assets/companion-card.md` — the card template.
- `examples/orders-ecosystem/` — a small invented system (web, back end, E2E, two internal services)
  with the finished index, a card and the cross-pointing `AGENTS.md` files.

This folder is **self-contained** — copy it into any runtime that loads a SKILL.md and it works as-is.

## See also (optional)

[../reverse-trace/](../reverse-trace/) uses this map to follow one integration call back to the
endpoints, the screens and the tests that reach it. [../harness-engineer/](../harness-engineer/)
builds the single-repo harness each companion can have first. Both are optional.
