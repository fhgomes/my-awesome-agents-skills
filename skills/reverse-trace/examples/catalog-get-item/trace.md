# Reverse trace: CatalogClient.getItem

> Invented example. It belongs to the same made-up Orders system as
> `../../../companion-map/examples/orders-ecosystem/`. Repositories, classes, paths, line numbers and
> commit hashes are invented to show the format.

- **Sink:** `ItemDto CatalogClient.getItem(String itemCode)` in
  `orders-backend/src/main/java/app/client/catalog/CatalogClient.java:41` (SOAP `ItemPort.getItem`)
- **Why it is changing:** the SOAP client is being replaced by the catalog REST API (`GET /v2/items/{id}`).
- **Snapshot:** `orders-backend@3f9c2a1` · `orders-web@b71e0d4` · `orders-e2e@09aa5c3`
- **Searched:** `orders-backend/src/`, `orders-backend/src/main/resources/bpmn/`, `orders-web/src/`,
  `orders-e2e/cypress/` · **Not searched:** mobile app (no checkout available), reporting scripts

The sink has one wrapper that only delegates, `CatalogClient.getItemCached(String)` at line 77. It is
the same sink and its callers are included below.

## Paths

### Path 1: Order detail screen

| Hop | Where | Evidence |
|---|---|---|
| Sink | `CatalogClient.getItem` | `orders-backend/.../client/catalog/CatalogClient.java:41` |
| Caller | `ItemLookupService.describe` | `orders-backend/.../service/ItemLookupService.java:52` |
| Caller | `OrderQueryService.findDetail` | `orders-backend/.../service/OrderQueryService.java:88` |
| Entry point | `GET /api/orders/{id}` | `orders-backend/.../api/OrderController.java:47` |
| Front-end call | `OrdersApi.getOrder` | `orders-web/src/app/core/api/orders.api.ts:14` |
| Component | `OrderDetailComponent` | `orders-web/src/app/orders/detail/order-detail.component.ts:31` |
| Screen | Order detail at `/orders/:id` | `orders-web/src/app/orders/orders.routes.ts:12` |

**Tests:** `orders-e2e/cypress/e2e/orders/order-detail.cy.ts` asserts the item description and the
supplier name shown for a seeded order. `OrderQueryServiceIT` asserts the description field.
**Coverage:** `covered`
**Action:** run both tests before and after the switch.

### Path 2: Item picker in "New order"

| Hop | Where | Evidence |
|---|---|---|
| Sink | `CatalogClient.getItemCached` (delegates to `getItem`) | `orders-backend/.../client/catalog/CatalogClient.java:77` |
| Caller | `ItemSearchService.preview` | `orders-backend/.../service/ItemSearchService.java:64` |
| Entry point | `GET /api/items/{code}` | `orders-backend/.../api/ItemController.java:29` |
| Front-end call | `ItemsApi.preview` | `orders-web/src/app/core/api/items.api.ts:9` |
| Component | `ItemPickerComponent` | `orders-web/src/app/orders/new/item-picker.component.ts:58` |
| Screen | New order, item picker at `/orders/new` | `orders-web/src/app/orders/orders.routes.ts:9` |

**Tests:** `orders-e2e/cypress/e2e/orders/new-order.cy.ts` picks one existing item and checks that the
form moves to the next step. It never asserts the previewed data and never tries an unknown code.
**Coverage:** `happy-path`
**Action:** add two cases to `new-order.cy.ts`: an item with no supplier (the empty element) and an
unknown code (expected message "Item not found"). Until they exist, test both by hand as a buyer user.

### Path 3: Approval step in the order workflow

| Hop | Where | Evidence |
|---|---|---|
| Sink | `CatalogClient.getItem` | `orders-backend/.../client/catalog/CatalogClient.java:41` |
| Caller | `ApprovalDelegate.execute` (resolved by name from the process model) | `orders-backend/.../workflow/ApprovalDelegate.java:36` |
| Entry point | BPMN service task `checkItemStatus` | `orders-backend/src/main/resources/bpmn/order-approval.bpmn:118` |
| Front-end call | `OrdersApi.approve` triggers the process step | `orders-web/src/app/core/api/orders.api.ts:31` |
| Component | `ApprovalPanelComponent` | `orders-web/src/app/orders/detail/approval-panel.component.ts:22` |
| Screen | Order detail, "Approve" button, at `/orders/:id` | `orders-web/src/app/orders/orders.routes.ts:12` |

"Find usages" did not show this caller: the process model names the delegate as a string.

**Tests:** `OrderApprovalProcessTest` runs the process with a mocked `CatalogClient` that always
returns an active item. No E2E spec presses "Approve".
**Coverage:** `happy-path`
**Action:** add a process test where the item is inactive (approval must stop). Manual check: approve
an order as an approver user and confirm the item status shown in the history panel.

### Path 4: Nightly open-order refresh job

| Hop | Where | Evidence |
|---|---|---|
| Sink | `CatalogClient.getItem` | `orders-backend/.../client/catalog/CatalogClient.java:41` |
| Caller | `OpenOrderRefresher.refresh` | `orders-backend/.../jobs/OpenOrderRefresher.java:44` |
| Entry point | `@Scheduled(cron = "0 0 2 * * *")` | `orders-backend/.../jobs/OpenOrderRefresher.java:27` |
| Screen | no UI caller found (searched `orders-web/src/`) | |

**Tests:** none reach the sink through this path.
**Coverage:** `not-covered`
**Action:** write an integration test for `OpenOrderRefresher.refresh` with two open orders before the
switch. Manual check in staging: run the job once by hand and compare the refreshed fields of three
orders with the values before the run.

## Related sink, traced separately

`CatalogClient.getUserRoles` (`CatalogClient.java:96`) goes through the same SOAP client and is called
by `RoleLoader` during login. It has its own trace: if the client is replaced, login is in the blast
radius even though no screen shows catalog data at that moment.

## Unverified hops

- `ReportExportService` builds item names from a cache that `getItemCached` fills. Whether a report can
  trigger a cache miss (and so the sink) depends on cache settings per environment. Ask the back-end owners.

## Summary

| Coverage | Paths |
|---|---|
| covered | 1 |
| happy-path | 2 |
| not-covered | 1 |
