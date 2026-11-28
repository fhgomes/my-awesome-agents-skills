# Companions of the Orders system

> Invented example. The repositories, paths and line numbers are made up to show the format.

Five repositories make one system. Read this file before a change that crosses a repo boundary.

| Repo | Role | Location | Card |
|---|---|---|---|
| `orders-web` | The screens people use to create and approve orders (Angular) | `../../orders-web/` | not included in this example |
| `orders-backend` | Order workflow, approvals and persistence (Java, Spring Boot) | `../../orders-backend/` | not included in this example |
| `orders-e2e` | End-to-end tests that drive the UI against a deployed stack (Cypress) | `../../orders-e2e/` | not included in this example |
| `catalog-service` | Master data for items and suppliers; owned by another team | `../../catalog-service/` | [catalog-service.md](catalog-service.md) |
| `pricing-service` | Price lists and currency rules; owned by another team | `../../pricing-service/` | not included in this example |

## Call graph (one arrow per line, with the file that proves it)

```
orders-web      -> orders-backend    REST  /api/orders/**             orders-web/src/app/core/api/orders.api.ts:14
orders-web      -> orders-backend    REST  /api/items/**              orders-web/src/app/core/api/items.api.ts:9
orders-backend  -> catalog-service   SOAP  ItemPort.getItem           orders-backend/src/main/java/app/client/catalog/CatalogClient.java:41
orders-backend  -> catalog-service   SOAP  ItemPort.findSuppliers     orders-backend/src/main/java/app/client/catalog/CatalogClient.java:58
orders-backend  -> pricing-service   REST  GET /prices/{itemId}       orders-backend/src/main/java/app/client/pricing/PricingClient.java:27
orders-e2e      -> orders-web        UI    baseUrl                    orders-e2e/cypress.config.ts:6
orders-e2e      -> orders-backend    REST  seed and cleanup calls     orders-e2e/cypress/support/api.ts:18
```

## Shared facts that no single repo owns

- User roles come from `catalog-service` (`ItemPort.getUserRoles`), and `orders-backend` calls it during
  login. A slow catalog means nobody logs in. Evidence: `orders-backend/.../security/RoleLoader.java:33`.
- Dates cross the SOAP boundary as local dates without a zone. The back end assumes UTC. No test covers it.

## Unverified

- `pricing-service` may also be called by a nightly job in `orders-backend`; the scheduler class exists
  but the job is disabled in every profile found. Ask the back-end owners.
