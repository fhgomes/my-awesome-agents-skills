# AGENTS.md — orders-backend (invented example)

Order workflow, approvals and persistence. Java, Spring Boot. Build with `./mvnw verify`.

## Companions

This repo is one part of a larger system. Map: `../harness/companions/INDEX.md`

| When you touch | Read first |
|---|---|
| anything under `client/catalog/` or a WSDL-generated class | `../harness/companions/catalog-service.md` |
| anything under `client/pricing/` | `../harness/companions/pricing-service.md` |
| a response DTO, an endpoint path or a status code | `../harness/companions/orders-web.md` and `../harness/companions/orders-e2e.md` |
| login, roles or session code | `../harness/companions/catalog-service.md` (roles are loaded from there) |

Before changing a contract, list who consumes it: the cards have a "Consumed by" column, and
`../orders-web/` and `../orders-e2e/` are checked out next to this repo so you can search them.
