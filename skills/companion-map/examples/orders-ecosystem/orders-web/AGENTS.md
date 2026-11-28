# AGENTS.md — orders-web (invented example)

The screens people use to create and approve orders. Angular. Run with `npm start`, test with `npm test`.

## Companions

This repo is one part of a larger system. Map: `../harness/companions/INDEX.md`

| When you touch | Read first |
|---|---|
| a file under `src/app/core/api/` | `../harness/companions/orders-backend.md` (the endpoints behind each call) |
| a route, a `data-cy` attribute or visible text a test may select | `../harness/companions/orders-e2e.md` |
| how an item, a supplier or a price is displayed | `../harness/companions/catalog-service.md` and `../harness/companions/pricing-service.md` |

The API types in `src/app/core/api/models/` are copied by hand from the back end DTOs. When a field
changes there, it must change here in the same pull request series.
