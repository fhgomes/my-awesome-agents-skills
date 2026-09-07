# Backend Performance Guide (Java / Spring Boot)

**Best used when:** you are adding performance practice to a Spring Boot service that owns a database — greenfield or a five-year-old monolith — and especially when an AI tool writes the code.
**Read before:** merging a new endpoint, a new query, a new migration, or a diff that claims to be "optimized".
**See also:** [performance-from-zero.md](./performance-from-zero.md) (measurement loop, budgets, AI failure modes) · [enforcement/README.md](./enforcement/README.md) (how to make these rules mandatory) · [../../skills/perf-engineer/SKILL.md](../../skills/perf-engineer/SKILL.md)

Stack here: Java 21+, Spring Boot 3.2+, Gradle, JPA/Hibernate, PostgreSQL, Testcontainers, JUnit 5, Micrometer. Section 13 maps every idea to Node, Python and Go.

## 1. The database is the main character

90% of backend latency is the database. The other 10% is waiting on someone else's database.

The review question behind this whole guide: **"Can this change hurt performance? A query inside a loop, a load without pagination, objects piling up in memory."** Ask it on every backend PR. It sits next to "maintainable > fast — optimize only when measured", and the two only agree once you split the work in two:

| Category | When | Backend examples |
|---|---|---|
| **Structural hygiene** | Always, in review, no measurement needed | Pagination on every list endpoint; an index on every FK and every column you filter/join/sort by; no repository or HTTP call inside a loop; `JOIN FETCH`/`@EntityGraph` for associations you know you need; TTL on every cache key; bounded pools; an explicit timeout on every outbound call |
| **Optimization** | Only after a measurement names the hotspot | Caching a computed value; tuning `maximumPoolSize`; GC flags; batch sizes; a materialized view or continuous aggregate |

Hygiene is not optimization — it is the difference between O(n) and O(1) as the table grows. "It worked with 200 rows" is not evidence. Sections 2-5 are hygiene; 6, 7 and 9 need a number first.

## 2. See the SQL before you read the code

You cannot fix an N+1 you cannot see. Turn the SQL on in the dev and test profiles, permanently.

```properties
# application-dev.properties / application-test.properties — never in prod
logging.level.org.hibernate.SQL=DEBUG
spring.jpa.properties.hibernate.generate_statistics=true
spring.jpa.properties.hibernate.query.fail_on_pagination_over_collection_fetch=true
spring.jpa.open-in-view=false
```

| Property | What it buys you |
|---|---|
| `logging.level.org.hibernate.SQL=DEBUG` | Every statement, in order. `spring.jpa.show-sql=true` is the lazy variant that bypasses your logging config — prefer the logger. |
| `hibernate.generate_statistics=true` | A per-session summary (statements prepared, entities loaded, collections fetched) and the `Statistics` object you can assert on. |
| `...query.fail_on_pagination_over_collection_fetch=true` | Turns the `HHH000104` warning ("firstResult/maxResults specified with collection fetch; applying in memory") into an exception. That warning means the database returned **every** row and Hibernate paginated in your heap ([vladmihalcea.com](https://vladmihalcea.com/hibernate-query-fail-on-pagination-over-collection-fetch/)). |
| `spring.jpa.open-in-view=false` | Open Session In View keeps the persistence context open until the response is serialized, so a getter touched by Jackson fires a query **after** your service returned — and holds a connection for the whole request. Turn it off, then fix the `LazyInitializationException`s it exposes: each one is a query you did not know you made. |

Test against a real PostgreSQL (`org.testcontainers:postgresql` + `org.testcontainers:junit-jupiter`), not H2 — a plan from H2 is fiction, and `EXPLAIN` is the point.

**Assert the statement count on your hot path.** The cheapest N+1 regression test that exists: it fails on the PR that adds the loop, not in production.

```java
@Test
void listingOrdersUsesOneStatement() {
    Statistics stats = entityManagerFactory.unwrap(SessionFactory.class).getStatistics();
    stats.clear();
    List<OrderSummary> page = orderService.list(PageRequest.of(0, 20));
    assertThat(page).hasSize(20);
    assertThat(stats.getPrepareStatementCount()).isEqualTo(1L);
}
```

`getPrepareStatementCount()` counts statements prepared since `clear()` (technique from [Vlad Mihalcea, "How to detect the N+1 query problem during testing"](https://vladmihalcea.com/how-to-detect-the-n-plus-one-query-problem-during-testing/)). A datasource-level interceptor such as `datasource-proxy` does the same with a dependency — `[verify library name and version for your stack]`.

## 3. N+1 and JPA

**BAD** — one query for the orders, then one per order. Twenty-one statements for a page of twenty.

```java
@Transactional(readOnly = true)
public List<OrderDTO> list(Pageable pageable) {
    return orderRepository.findAll(pageable).getContent().stream()
        .map(o -> new OrderDTO(o.getId(), o.getItems().size()))   // lazy hit, per row
        .toList();
}
```

**GOOD** — tell JPA what you need, once.

```java
@EntityGraph(attributePaths = "items")
Page<Order> findByStatus(String status, Pageable pageable);

@Query("SELECT DISTINCT o FROM Order o JOIN FETCH o.items WHERE o.status = :status")
List<Order> findByStatusWithItems(@Param("status") String status);
```

| Rule | Why |
|---|---|
| `FetchType.LAZY` on **every** `@ManyToOne` and `@OneToOne` | JPA defaults those to `EAGER`. Every eager association is a join you never asked for, on every query touching the entity. |
| Read endpoints return a **DTO projection**, not the entity | `SELECT new com.example.order.OrderSummary(o.id, o.status, o.total) ...` into a `record` (or a Spring Data interface projection) fetches the four columns the screen needs instead of the entity graph. |
| `@Transactional(readOnly = true)` on read methods — in the service, never the controller | No dirty checking, no flush, and replicas become routable later. Free. |
| `@BatchSize(size = 20)` on collections you genuinely iterate | Middle ground: N+1 becomes N/20+1 without multiplying rows in a fetch join. |
| Never `JOIN FETCH` a collection **and** paginate | The `HHH000104` trap from section 2 — page the root ids first, then fetch the collection for that page. |

**AI failure mode F1.** The prompt that produces the BAD version is the innocent one: *"Add an endpoint that returns a customer's orders with the number of items in each."* The model writes locally correct Java and never sees the SQL log. Catch it with the statement-count test above plus a grep for repository calls inside `for` / `stream().map` ([enforcement/README.md](./enforcement/README.md)).

## 4. Pagination is not optional

```java
// BAD — the #1 anti-pattern in AI-written Spring code
List<User> active = userRepository.findAll().stream()
        .filter(u -> u.getStatus().equals("ACTIVE"))
        .toList();

// GOOD — the database filters and the database pages
@Query("SELECT u FROM User u WHERE u.status = :status")
Page<User> findByStatus(@Param("status") String status, Pageable pageable);
```

> `repository.findAll().stream().filter(...)` showed up, written by an AI assistant, in two unrelated projects of ours within the same quarter. Both worked in dev with 200 rows. One of them was a table that grows by thousands of rows a day.

```java
@GetMapping
public Page<OrderSummary> list(@RequestParam(defaultValue = "0") int page,
                               @RequestParam(defaultValue = "20") int size) {
    return orderService.list(PageRequest.of(page, Math.min(size, MAX_PAGE_SIZE))); // MAX_PAGE_SIZE = 100
}
```

- **Clamp the page size in the controller** — an unclamped `size` is a denial-of-service parameter: `?size=1000000`.
- **Opt out only with an explicit bound in code** — `PageRequest.of(0, 50)` plus a comment naming the maximum cardinality ("status codes, 12 rows, seeded by migration"); "the table is small" is not a bound.
- **`Page<T>` costs a second `count(*)` per request** — return `Slice<T>` when the UI only needs "is there a next page" — and on big tables use keyset pagination (`WHERE id > :lastId ORDER BY id LIMIT :n`), because `OFFSET 500000` makes PostgreSQL walk half a million rows to discard them.
- **Exports are jobs, not requests.** "It is a report, it needs everything" is how `findAll()` comes back. Return `202` with a job id, stream the file from a paged query, notify when done (section 8).

## 5. Indexes, migrations and EXPLAIN

| Index rule | Note |
|---|---|
| Every foreign key gets a non-unique index | The FK constraint does not create one in PostgreSQL, and without it a delete on the parent scans the child. |
| Every column a real query filters, joins or sorts by gets an index, named `<table>_<column>_idx` (composite: `<table>_<col1>_<col2>_idx`) | The columns your queries use, not every column. Lowercase, under 30 characters. |
| PK and UK come from constraints, not hand-written indexes | The constraint creates the index. |
| The index ships in the **same migration** as the query that needs it | An index added "later" is added never. |
| Indexes are not free | Each one slows every write on that table. Drop those with `idx_scan = 0` in `pg_stat_user_indexes`. |

| Migration rule | Why |
|---|---|
| One logical change per file (a table plus its indexes counts as one) | Reviewable, revertable. |
| A rollback always exists (Liquibase `<rollback>`, a documented `-- down` for Flyway) | A migration you cannot undo is a deploy you cannot undo. |
| **Never modify a migration that ran in any environment** — fix forward with a new file | Checksums break and environments diverge silently. |
| Naming `yyyyMMddHHmmss-description` (`date +"%Y%m%d%H%M%S"`) | Unique per developer, no merge conflicts, automatic ordering. |
| Schema changes are additive: new columns nullable or defaulted, never renamed in place | Old and new app versions run at the same time during a deploy. |
| Flyway or Liquibase, never `ddl-auto=update` in prod | `update` will cheerfully not do what you assumed. |

### Reading `EXPLAIN (ANALYZE, BUFFERS)`

Run it on production-like volume; a plan over 200 rows tells you nothing.

```sql
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM orders WHERE customer_id = 42 ORDER BY created_at DESC LIMIT 20;
```

| What you see | What it means | Fix |
|---|---|---|
| `Seq Scan` on a large table with a selective `WHERE` | No usable index | Add it, re-run |
| `rows=200000 ... actual rows=20` (examined ≫ returned) | Read a lot to return a little | Index the filter columns, or filter in SQL |
| `Sort Method: external merge Disk: 24MB` | The sort spilled to disk | Index matching the `ORDER BY`, or shrink the row set |
| `Rows Removed by Filter: 480000` | Filtering after the scan | That column belongs in the index (if estimates are far from actual rows, run `ANALYZE <table>;` first) |

Review budget: **rows examined per row returned < 10**. Details in the [PostgreSQL EXPLAIN docs](https://www.postgresql.org/docs/current/using-explain.html).

Column order in a composite index is not cosmetic — it is usable left to right only. `(customer_id, created_at)` serves `WHERE customer_id = ? ORDER BY created_at` **and** plain `WHERE customer_id = ?`; the reverse order serves neither well. Equality columns first, range/sort column last ([use-the-index-luke.com](https://use-the-index-luke.com/)).

```sql
CREATE INDEX order_customer_created_idx ON orders (customer_id, created_at DESC);
CREATE INDEX order_pending_idx ON orders (created_at) WHERE status = 'PENDING';  -- partial
```

**Time-series tables (events, clicks, metrics)** are a different animal: partition by time, keep raw rows only as long as you need them, pre-aggregate what dashboards read.

```sql
SELECT create_hypertable('events', 'time');                                  -- time-partitioned
SELECT add_retention_policy('events', INTERVAL '2 years');
SELECT add_compression_policy('events', compress_segmentby => 'account_id'); -- compress old chunks
-- plus a continuous aggregate holding the hourly/daily buckets the dashboard queries
```

TimescaleDB syntax ([docs.timescale.com](https://docs.timescale.com/)); plain PostgreSQL `PARTITION BY RANGE (time)` with a scheduled materialized view gets you most of it without an extension.
> A dashboard endpoint loaded twelve months of rows to compute four numbers. The fix was not a cache; it was `COUNT` and `SUM` in the query, then a continuous aggregate when the table hit tens of millions of rows. Cache came third, with a 5-minute TTL.

With pre-aggregation in place, 30-day analytics land under 500 ms and 90-day under 1 s; without it, no TTL is short enough to hide the first miss.

## 6. Connection pool

```properties
spring.datasource.hikari.maximum-pool-size=10     # default is 10
spring.datasource.hikari.connection-timeout=3000  # ms waiting for a connection before failing fast
spring.datasource.hikari.max-lifetime=1800000     # keep below the DB/proxy idle timeout
```

- **`maximumPoolSize` is not "more is faster".** A pool bigger than the database can serve converts queuing into context switching. Size it from the [HikariCP "About Pool Sizing" wiki](https://github.com/brettwooldridge/HikariCP/wiki/About-Pool-Sizing), and remember it is per instance: ten instances at 20 is 200 sessions on one PostgreSQL.
- **Watch `hikaricp.connections.pending`** — consistently above zero means threads are waiting for a connection, usually because of a slow query or a transaction held open across a remote HTTP call, not because the pool is too small.
- **Keep `connection-timeout` short** — a fast 503 beats a thread pool waiting 30 s. **Virtual threads do not enlarge the pool.** They make waiting cheap; those thousands of request threads still queue on the same 10 connections. Size the pool for the database.
- **Many instances → PgBouncer** in transaction mode, so total sessions stay bounded; transaction pooling disables session state (advisory locks, some prepared-statement modes), so check before switching.

## 7. Caching layers

Climb this ladder in order. Every step skipped is a cache you will have to invalidate later.

| Step | What | When | Cost of getting it wrong |
|---|---|---|---|
| 0 | **No cache** — fix the query, add the index, aggregate in the database | Always try first | None |
| 1 | **HTTP caching** — `Cache-Control`, `ETag`/`If-None-Match` on GETs | Responses a browser or CDN may hold | Stale content downstream |
| 2 | **In-process (Caffeine)** — `@Cacheable` with `maximumSize` + `expireAfterWrite` | Single instance, or brief per-instance divergence is fine | Unbounded heap growth |
| 3 | **Distributed (Redis)** — `spring-boot-starter-data-redis` | More than one instance, or the cache must survive a restart | One more system to run, monitor and (if you forget TTLs) back up |

```properties
spring.cache.type=caffeine
spring.cache.caffeine.spec=maximumSize=10000,expireAfterWrite=5m
```

In-process caches are only for data that may vanish at any moment and is bounded in size — that is what keeps the service stateless and horizontally scalable. Session state never lives in process.

- **No TTL, no cache.** A key without an expiry is not a cache, it is a second database. Key naming `<domain>:<id>:<what>` — `account:{accountId}:summary`; predictable keys are greppable keys.
- The write path evicts (`@CacheEvict`), or you accept the TTL as your staleness bound. "Cache forever and hope" is not invalidation.
- Cache the DTO you serve, not the entity graph. TTLs from a real pipeline, as a starting shape: 5 min real-time dashboards, 1 h historical aggregates, 7 d attribution lookups, 30 d idempotency keys. Write them down next to the key names.

> Every Redis key in that pipeline has a TTL. The one time a key had no TTL, the cache became a second database that nobody had planned to back up.

## 8. Async and virtual threads

They solve different problems. Pick from the table, not by preference.

| Situation | Choice | Why |
|---|---|---|
| The work must finish inside the request and it is many blocking I/O calls (3 DB + 2 HTTP fan-out) | **Virtual threads** | Blocking gets cheap; the carrier thread is released while you wait |
| The caller does not need the result (email, webhook dispatch, export, report) | **`@Async` with a bounded executor** | The request returns in milliseconds; failures retry instead of vanishing |
| Multi-step workflow needing durability, retry and visibility across restarts | **JobRunr / Spring Batch** | `@Async` state dies with the JVM |
| Hard sub-50 ms write path with heavy downstream work | **Queue it** (scar below) | The synchronous part does the minimum |

```properties
# Spring Boot 3.2+ on Java 21+: web server and @Async/@Scheduled executors use virtual threads
spring.threads.virtual.enabled=true
```

<!-- Verified against https://docs.spring.io/spring-boot/reference/features/task-execution-and-scheduling.html on 2026-09-07 -->

Where you want it explicit: `Executors.newVirtualThreadPerTaskExecutor()`.

- **Bound the `@Async` executor** — a `ThreadPoolTaskExecutor` with an unbounded queue is an `OutOfMemoryError` on a delay: set `corePoolSize`, `maxPoolSize`, `queueCapacity` and a rejection policy.
- **Retry with exponential backoff, max 3 attempts, then a dead letter.** Infinite retries against a broken downstream are a self-inflicted outage.
- **Every outbound call gets explicit connect and read timeouts** on the `RestClient`/`WebClient` request factory — defaults wait far longer than your users will.
- **Never `@Async` something the caller waits on.** That is a thread pool impersonating a method call.

> In one of our projects, a click-tracking endpoint had a hard requirement of under 50 ms. The design that met it was not a faster monolith: it was an in-memory store answering synchronously (about 5 ms), a queue behind it, and a time-series database writing in 5-second batches. Async was the fix, but only after the requirement was a number.

## 9. JVM and GC basics

JVM flags are optimization, never the first move. If you have not read the SQL log yet, you are not ready for GC logs.

| Topic | Practice |
|---|---|
| Heap in containers | `-XX:MaxRAMPercentage=75.0` — the JVM reads the container limit; a fixed `-Xmx` is a guess that ages badly |
| Collector | G1 is the default and is right until proven otherwise. Reach for ZGC only with a **measured** pause-time violation (large heap, strict p99) |
| Profiling | `-XX:StartFlightRecording=duration=120s,filename=app.jfr,settings=profile`, then JDK Mission Control ([JFR docs](https://docs.oracle.com/en/java/javase/21/jfapi/)); GC visibility with `-Xlog:gc*:file=gc.log:time,uptime:filecount=5,filesize=10M` |
| Live inspection | `jcmd <pid> GC.heap_info`, `Thread.print`, `VM.native_memory summary`; on a suspected leak take the dump first (`jcmd <pid> GC.heap_dump /tmp/heap.hprof`) and read it — never "just add heap" |

Rising heap plus rising pauses is almost always an unbounded collection — a cache without `maximumSize`, a `findAll()` in a scheduled job — not a bad collector.

## 10. Observability

Dependencies: `org.springframework.boot:spring-boot-starter-actuator` and `io.micrometer:micrometer-registry-prometheus`.

```properties
management.endpoints.web.exposure.include=health,info,metrics,prometheus
```

<!-- Verified against https://docs.spring.io/spring-boot/reference/actuator/metrics.html on 2026-09-07 -->

**Never `include=*` in production**, and protect `/actuator` with Spring Security — `env`, `heapdump` and `threaddump` are a gift to an attacker. Build your first dashboard out of what you get for free:

| Metric | Tags | Starter panel |
|---|---|---|
| `http.server.requests` | `method`, `status`, `uri`, `outcome` | p95 latency by `uri`; request rate; error rate by `status` |
| `hikaricp.connections.active` / `.idle` / `.max` / `.min` / `.pending` | pool | Active vs max; **pending > 0 is the alert** |
| `jvm.memory.used`, `jvm.gc.pause` | area, cause | Heap after GC; pause p99 |

Alert on the golden signals — latency, traffic, errors, saturation ([sre.google](https://sre.google/sre-book/monitoring-distributed-systems/)) — not on whichever metric you find interesting. Add structured JSON logs with a correlation id in the MDC on every line, and OpenTelemetry for tracing (Spring Cloud Sleuth is discontinued; do not start there).

## 11. Load testing as a CI gate

A latency number no tool produced is not an SLA, it is a hope:
> A delivery report generated by an AI agent on one of our projects listed "< 100 ms response SLA (< 50 ms typical)" as a shipped feature. Four lines below, under "next steps", it listed "load testing (verify SLAs)".

```javascript
// perf/k6-smoke.js  —  k6 run --env BASE_URL=http://localhost:8080 perf/k6-smoke.js
import http from 'k6/http';
export const options = {
  vus: 5,
  duration: '30s',
  thresholds: {
    http_req_duration: ['p(95)<300'],   // the read budget; a write scenario gets 500
    http_req_failed: ['rate<0.01'],
  },
};
export default function () { http.get(`${__ENV.BASE_URL}/api/v1/orders?page=0&size=20`); }
```

<!-- Verified against https://grafana.com/docs/k6/latest/using-k6/thresholds/ on 2026-09-07 -->

A failing threshold makes `k6 run` exit non-zero — that is the entire gate.

```yaml
- uses: grafana/setup-k6-action@v1
- uses: grafana/run-k6-action@v1
  with:
    path: |
      ./perf/k6-smoke.js
    flags: --env BASE_URL=${{ vars.STAGING_URL }}
```

<!-- Verified against https://github.com/grafana/setup-k6-action and https://github.com/grafana/run-k6-action on 2026-09-07 -->

Gradle-native teams can keep it in Java with Gatling — if one assertion fails, the simulation fails and so does the build. A Gatling scenario usually mixes reads and writes, so it asserts against the write budget (500 ms); a read-only scenario gets 300:

```java
setUp(scn.injectOpen(rampUsers(10).during(60)))
  .assertions(
    global().responseTime().percentile(95.0).lt(500),
    global().successfulRequests().percent().gt(99.0)
  );
```

<!-- Verified against https://docs.gatling.io/concepts/assertions/ on 2026-09-07 -->

JMeter is fine and battle-tested, but its XML test plans are not code-reviewable in a pull request: keep it for the nightly if you already run it, and gate PRs with k6 or Gatling.

Cadence: **smoke on every PR** (5 VUs, 30 s, under a minute), **full load nightly** against staging (ramp to expected peak, same thresholds), soak for hours before a big release while watching heap and pool.

**Never point a load test at production.**

> In one of our projects, a Playwright run pointed at production sent about 10 real notifications to real users. Point a load test at production and the story is the same with three more zeros.

Runnable copies live in [enforcement/hooks/k6-smoke.js](./enforcement/hooks/k6-smoke.js) and [enforcement/hooks/github-actions-perf.yml](./enforcement/hooks/github-actions-perf.yml).

## 12. Review checklist (backend)

Copy into `.github/pull_request_template.md`:

```markdown
- [ ] Every new list endpoint is paginated, page size clamped (max 100)
- [ ] No repository, HTTP or cache call inside a `for` / `stream().map` / `forEach`
- [ ] SQL log checked for this path; the statement count is what I expected
- [ ] No `findAll()` outside a bounded, commented case
- [ ] `EXPLAIN (ANALYZE, BUFFERS)` output for every new or changed query is in this PR
- [ ] Every FK and every filtered/sorted column has an index, in the same migration
- [ ] Migration is one logical change, has a rollback, and no executed file was edited
- [ ] Reads are `@Transactional(readOnly = true)`; writes are `@Transactional`
- [ ] Every outbound call has connect and read timeouts
- [ ] Every new cache key has a TTL and an eviction path
- [ ] Async work is bounded: queue capacity, max 3 retries, dead letter
- [ ] No latency claim without the command and its output pasted here
```

## 13. Same idea in Node / Python / Go

| Concern | Node (NestJS/Express) | Python (Django/FastAPI) | Go |
|---|---|---|---|
| Pagination | `take`/`skip` (Prisma, TypeORM) | `Paginator` / SQLAlchemy `.limit().offset()` | `LIMIT` or keyset in SQL |
| See the SQL | Prisma `log: ['query']`, `DEBUG=knex:query` | `django-debug-toolbar`, SQLAlchemy `echo=True` | log wrapper around `database/sql`, `sqlc` |
| N+1 detection | Query log + a count assertion in a test | `nplusone`; `select_related`/`prefetch_related` | Explicit joins — no lazy loading to save you |
| Connection pool | `pg` `max`, Prisma `connection_limit` | SQLAlchemy `pool_size`/`max_overflow` | `db.SetMaxOpenConns` / `SetMaxIdleConns` |
| Off the request path | BullMQ / SQS worker | Celery / RQ / ARQ | goroutine plus a real queue, not a bare `go func()` |
| Profiler / metrics | `node --cpu-prof`; `prom-client` | `cProfile`, `py-spy`; `prometheus_client` | `net/http/pprof`; `promhttp` |

## 14. Day 1 / Week 1

### Greenfield

| When | Do |
|---|---|
| Day 1 | Add `spring-boot-starter-actuator` + `io.micrometer:micrometer-registry-prometheus` and set `management.endpoints.web.exposure.include=health,info,metrics,prometheus`; put the four dev properties from section 2 in `application-dev.properties` |
| Day 1 | Define `MAX_PAGE_SIZE = 100` and paginate the first endpoint you write |
| Day 1 | Add Testcontainers PostgreSQL to the test source set and write the statement-count test for that endpoint |
| Week 1 | Install k6 ([install docs](https://grafana.com/docs/k6/latest/set-up/install-k6/)); commit `perf/k6-smoke.js` with `p(95)<300` (read) and `rate<0.01`; run `k6 run --env BASE_URL=http://localhost:8080 perf/k6-smoke.js` |
| Week 1 | Run that smoke in CI against staging; add the section 12 checklist to the PR template; write your budgets into `perf-budgets.md`; set `spring.threads.virtual.enabled=true` (Java 21+) and give every outbound client timeouts before you have five of them |

### Legacy, with no practice today

| When | Do |
|---|---|
| Day 1 | Pick the endpoint users complain about. `curl -w '%{time_total}\n' -o /dev/null -s <url>` ten times; write the number down. That is your baseline and your argument |
| Day 1 | Turn on the section 2 properties in dev, replay that endpoint, count the statements. Most of the time the problem is visible in ten seconds |
| Day 1 | `grep -rn "findAll()" src/main/java \| grep -v Pageable` — every hit is a candidate; sort by table size, not by file |
| Week 1 | Fix the top three by user impact (pagination, missing index, N+1). One PR each, with before/after `EXPLAIN (ANALYZE, BUFFERS)` and the re-measured `curl` number |
| Week 1 | Set `spring.jpa.open-in-view=false` in its own PR and fix what it exposes — each `LazyInitializationException` is a hidden query |
| Week 1 | Add Actuator + Prometheus with one panel (p95 of `http.server.requests` by `uri`), then a k6 smoke whose threshold **would have failed** before your fixes |

Never start a legacy effort with a rewrite, a cache or a JVM flag. Start with the query the users are waiting on.

## 15. See also

- [performance-from-zero.md](./performance-from-zero.md) — measurement loop, budgets, the eight ways an AI writes slow code
- [enforcement/README.md](./enforcement/README.md) — instruction blocks, hooks and CI gates that make these rules mandatory (runnable artifacts in `enforcement/hooks/`)
- [../../skills/perf-engineer/SKILL.md](../../skills/perf-engineer/SKILL.md) — the reviewer persona that runs these checks for you

## Sources & further reading

- Spring Boot — https://docs.spring.io/spring-boot/reference/actuator/metrics.html (Actuator metrics), https://docs.spring.io/spring-boot/reference/features/task-execution-and-scheduling.html (virtual threads)
- Vlad Mihalcea — https://vladmihalcea.com/hibernate-query-fail-on-pagination-over-collection-fetch/ and https://vladmihalcea.com/how-to-detect-the-n-plus-one-query-problem-during-testing/
- PostgreSQL, "Using EXPLAIN" — https://www.postgresql.org/docs/current/using-explain.html · Markus Winand, *SQL Performance Explained* — https://use-the-index-luke.com/
- HikariCP, "About Pool Sizing" — https://github.com/brettwooldridge/HikariCP/wiki/About-Pool-Sizing · TimescaleDB — https://docs.timescale.com/
- JDK Flight Recorder — https://docs.oracle.com/en/java/javase/21/jfapi/ · k6 thresholds — https://grafana.com/docs/k6/latest/using-k6/thresholds/ · Gatling assertions — https://docs.gatling.io/concepts/assertions/ · Google SRE Book, "Monitoring Distributed Systems" — https://sre.google/sre-book/monitoring-distributed-systems/

---

Last reviewed: 2026-09-07
