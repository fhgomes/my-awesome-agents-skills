# Example: the Orders ecosystem

An invented system, small enough to read in five minutes, that shows what `companion-map` leaves behind.
Nothing here is real: the repositories, paths and line numbers exist only to show the format.

```
orders-ecosystem/
  harness/companions/
    INDEX.md              the map and the call graph
    catalog-service.md    one filled card (the other four follow the same template)
  orders-backend/AGENTS.md   "Companions" router for the back end
  orders-web/AGENTS.md       "Companions" router for the front end
  orders-e2e/AGENTS.md       "Companions" router for the E2E tests
```

What to notice:

- Every arrow in `INDEX.md` ends with the file that proves it.
- The card for `catalog-service` has a **Do-not-break** section with behaviour no test covers
  (empty versus missing element, zero-padded codes). Those two lines are what saves a migration.
- Each `AGENTS.md` only routes: when to leave the repo, and which card to read. The knowledge stays
  in the cards, in one place.
- The index records a shared fact that surprised the team: login depends on `catalog-service`.

The next step with this map is a reverse trace: see `../../../reverse-trace/examples/catalog-get-item/`.
