# Example: tracing `CatalogClient.getItem` back to the screens

An invented trace for the made-up Orders system used in
[`../../../companion-map/examples/orders-ecosystem/`](../../../companion-map/examples/orders-ecosystem/).
Nothing here is real.

- [`trace.md`](trace.md) — the chain for each path, hop by hop, with evidence and a coverage grade.
- [`trace-map.csv`](trace-map.csv) — one row per path; the `action` column is the test plan.

What to notice:

- Four paths reach one SOAP call: two screens, one workflow step and one scheduled job.
- The workflow caller was invisible to "find usages" because the process model names it as a string.
- Two of the four paths are `happy-path`: a test touches them, but none checks the data the sink returns.
- The job has no screen at all, so a UI-only test plan would have missed it.
- Login is in the blast radius through a different method of the same client, so it gets its own trace.
