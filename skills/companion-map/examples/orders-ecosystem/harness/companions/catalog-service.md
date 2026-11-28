# catalog-service

> Invented example of a filled card.

**Role:** master data for items, suppliers and user roles. If it is down, order screens show no items
and nobody can log in to the Orders system.

**Location:** `../../catalog-service/` · default branch: `main` · owned by the master-data team

**Stack:** Java 17, Spring Boot, SOAP endpoints (contract-first) and a newer REST API side by side

## Entry points

| Kind | Where | Notes |
|---|---|---|
| SOAP | `src/main/java/catalog/ws/ItemEndpoint.java` | WSDL at `src/main/resources/wsdl/item.wsdl` |
| HTTP | `src/main/java/catalog/api/ItemController.java` | base path `/v2/items` |

## Provides (others depend on these)

| Contract | Defined in | Consumed by |
|---|---|---|
| `ItemPort.getItem(id)` | `wsdl/item.wsdl:88` | `orders-backend` |
| `ItemPort.findSuppliers(filter)` | `wsdl/item.wsdl:121` | `orders-backend` |
| `ItemPort.getUserRoles(user)` | `wsdl/item.wsdl:160` | `orders-backend` (login) |
| `GET /v2/items/{id}` | `ItemController.java:34` | nobody yet |

## Consumes (this repo depends on these)

Nothing from the Orders system.

## Run and test

```bash
./mvnw verify                 # about 6 minutes
./mvnw spring-boot:run -Dspring-boot.run.profiles=local
```

Source of these commands: `README.md` and `.ci/pipeline.yml`.

## Do-not-break

- `getItem` returns an empty element, not a missing one, when an item has no supplier. The Orders
  back end maps "empty" to an empty list and "missing" to null.
- Item codes come back left-padded with zeros to 10 characters over SOAP. The REST API returns them
  unpadded. A caller that moves from one to the other must normalize.

## Open questions

- Is `ItemPort` scheduled for removal? The WSDL has no deprecation note. Ask the master-data team.
