---
name: reverse-trace
description: >
  Trace backwards from one final integration call (a SOAP or REST client method, a query, a message
  publish) to everything that reaches it: services, endpoints, jobs, front-end calls, screens and the
  tests that cover each path, then turn the result into a test plan. Use ALWAYS when the conversation
  involves: "what does this change touch", "who calls this", "impact analysis", "blast radius",
  "which screens use this endpoint", "which tests cover this", "trace back from the call", "map the
  usages before migrating", replacing or migrating an integration (SOAP to REST, one client library
  to another, a database or queue swap), or planning what to test manually versus automatically.
  Also trigger on: "reverse trace", "call chain", "coverage map", "happy path only", "not covered",
  "characterization before migration". Also triggers on the equivalent phrases in other languages.
---

# Reverse Trace: from the final call back to the screen

Forward tracing asks "what does this screen do?". A migration needs the opposite question: "this call
is about to change, so who reaches it, from where, and what proves it still works?". This skill walks
the call chain backwards, one hop at a time, across repositories, and ends with a table that says for
each path whether a test covers it, covers only the happy path, or does not cover it.

## Inputs

- **The sink**: the exact method, query or publish that will change. One trace per sink.
- **The repositories** on disk: the caller, its front end and its E2E tests. A companion map helps
  (see the optional `companion-map` skill) but is not required.

## What you produce

```
trace/
  <sink-name>.md       the chain, hop by hop, with file:line evidence
  trace-map.csv        one row per path: sink, chain, endpoint, screen, test, coverage, action
```

## Procedure

### 1. Pin the sink

Write its full signature and the file that declares it. List every overload and every wrapper that
only delegates to it; they are the same sink.

### 2. Walk up inside the back end

For each caller, record `file:line` and move up until you reach an **entry point**: an HTTP endpoint,
a message consumer, a scheduled job, a workflow or process step, a startup hook.

A plain "find usages" misses callers. Also search by name for:

- interfaces and their implementations (the caller holds the interface);
- dependency-injection wiring by name or qualifier, and factory methods;
- reflection, expression languages and string references (workflow delegates, templates, scripts);
- caches and decorators that wrap the sink;
- copies: the same call written twice in old code under a different helper.

Stop a branch only at an entry point. Mark a hop you could not confirm as **unverified**.

### 3. Cross into the front end

For each HTTP entry point, search the front end for the path (and its constant, and its builder).
Follow the API service up to the components that call it, then to the routes that render those
components. Record the screen as a user would name it, plus the route.

Entry points nobody in the front end calls are still entry points: other systems, jobs or a mobile
app may call them. Write "no UI caller found" and say where you searched.

### 4. Find the tests

For each path, look for tests at three levels and record the file:

- unit or integration tests that execute the sink through this chain;
- API tests that hit the entry point;
- E2E specs that open the screen and perform the action.

### 5. Grade the coverage of each path

| Grade | Meaning |
|---|---|
| `covered` | A test drives this path and asserts on data that comes from the sink |
| `happy-path` | A test drives it but only the success case, or asserts only that the page loads |
| `not-covered` | No test reaches the sink through this path |

Read the assertions before grading. A spec that visits the screen without checking the data is
`happy-path` at best.

### 6. Turn the map into a plan

Fill the `action` column of `trace-map.csv`:

- `covered`: run the existing test before and after the change.
- `happy-path`: add the missing cases (empty result, error, permission, large payload) or test by hand.
- `not-covered`: write a test, or list the exact manual steps (screen, user role, data, expected result).

Order the work by risk: paths many users hit, paths with money or permissions, paths with no test.
The lowest-risk paths migrate first.

## Output format

`trace/<sink>.md` uses `assets/trace-template.md`. The CSV has exactly these columns:

```
sink,chain,entry_point,ui_screen,ui_route,test,coverage,action
```

## Rules

- Every hop cites `path:line`. No evidence, no hop.
- Never write `covered` without naming the test file and the assertion that checks sink data.
- Do not collapse paths. Two screens reaching the same endpoint are two rows.
- Say what you searched and what you did not. "No caller found in orders-web (searched src/)" is a result.
- The trace is a snapshot. Put the commit hash of each repository at the top of the file.

## Works well with (optional)

- `companion-map`, to know which repositories to search.
- `parity-check`, to prove the old and the new path return the same data once the map says where to look.
