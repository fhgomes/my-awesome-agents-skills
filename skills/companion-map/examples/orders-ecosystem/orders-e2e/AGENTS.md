# AGENTS.md — orders-e2e (invented example)

End-to-end tests that drive the UI against a deployed stack. Cypress. Run with `npx cypress run`.

## Companions

This repo is one part of a larger system. Map: `../harness/companions/INDEX.md`

| When you touch | Read first |
|---|---|
| a selector or a page object | `../harness/companions/orders-web.md` (routes and `data-cy` names) |
| seed or cleanup calls in `cypress/support/api.ts` | `../harness/companions/orders-backend.md` |

Each spec starts with a comment naming the screen and the endpoints it exercises. Keep that comment
true: the reverse trace reads it to decide what is covered.
