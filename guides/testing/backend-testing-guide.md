# Backend Testing Guide

**Best used when:** you write, review or fix a backend test on a Spring Boot service that owns a database.
**Read before:** editing any `*Test.java`, or telling an AI tool "add tests for this endpoint".
**See also:** [testing-from-zero.md](./testing-from-zero.md) (layers, smells, AI prompting), [e2e-testing-guide.md](./e2e-testing-guide.md) (the same ownership probes one layer up), [enforcement/README.md](./enforcement/README.md) (how to make any of this mandatory).

Primary stack here is Java 21 + Spring Boot + Gradle + JUnit 5 + Mockito + Testcontainers + MockMvc + AssertJ. The last section maps every idea to Node, Python and Go.

---

## 1. Position: integration-first, Mockito for pure logic

Test at the highest layer that is still fast, deterministic and local. For a Spring/HTTP service that owns a database, that layer is the integration test: real Postgres in Testcontainers (one static container shared by the whole run), real Spring context, HTTP through MockMvc with a real token. Mockito unit tests are for pure logic: state machines, pricing, parsers, mappers, anything where a database adds nothing.

This is an evolution, and we state it as one. The old rule we wrote in 2025 said "prefer unit tests over integration tests, they are cheaper to write and to run". That was right about authoring cost and wrong about what a test is for. Most backend bugs live in the wiring — auth, ownership checks, transaction boundaries, JPA filters, exception-to-status mapping — and a unit test with a mocked repository cannot see any of them. Two things changed the cost model: a shared Testcontainers instance makes the second integration test cost seconds, not minutes, and AI tools write test scaffolding for free. The expensive thing is no longer typing the test. It is trusting a green that asserted nothing.

| Code under test | Default layer | Why |
|---|---|---|
| Pure function / domain rule / state machine | Unit, no framework | Fast, exhaustive edge cases, no infra |
| Service that touches DB, security or transactions | Integration (real DB + MockMvc) | The bugs are in the wiring |
| Controller mapping only, no logic | Integration through the service, not `@WebMvcTest` alone | A slice cannot see `@PreAuthorize` + service + JPA filter together |
| Outbound HTTP client | Unit with a stubbed transport (WireMock / MockWebServer) | Deterministic, and the contract is asserted |
| Scheduled job / outbox drain | Integration, with Awaitility for the wait | Timing and commit boundaries are the risk |

Two corollaries, because they get argued every time:

- **H2 is not "Postgres when convenient."** Use H2 only when the app has zero Postgres-specific behaviour — no `jsonb`, no arrays, no partial indexes, no `ON CONFLICT`, no extensions — and write that decision down in the repo's `docs/testing.md` as a declared exception. The default is Testcontainers against the same major version you run in production.
- **`@SpringBootTest` + MockMvc is the workhorse.** Slice tests (`@WebMvcTest`, `@DataJpaTest`) are an optimization you add later when a specific suite is measurably too slow. They are not the starting point.

## 2. Toolchain

| Choice | Rule |
|---|---|
| JUnit | JUnit 5 (Jupiter) only. No JUnit 4, no `junit-vintage` on a new repo. |
| Assertions | AssertJ (`assertThat`, `assertThatThrownBy`) plus MockMvc's `status()` / `jsonPath()`. No Hamcrest. |
| Mocks | Mockito via `@ExtendWith(MockitoExtension.class)` + `@Mock` / `@InjectMocks`. |
| Database | Testcontainers Postgres, one static container per JVM. |
| HTTP | MockMvc (or `WebTestClient` on WebFlux). Test methods that touch it declare `throws Exception`. |
| Visibility | Test classes and methods are package-private. `public` on a JUnit 5 test buys nothing. |
| Versions | Every version lives in `gradle.properties`. Never hardcode a version in `build.gradle`. |

```properties
# gradle.properties — versions live here, one place to bump
testcontainersVersion=1.20.6
assertjVersion=3.26.3
```

```groovy
// build.gradle (Groovy DSL). Spring Boot's dependency management already pins
// junit-jupiter, mockito and assertj; the properties above are what you use for
// anything it does not manage, and for deliberate overrides.
dependencies {
    testImplementation 'org.springframework.boot:spring-boot-starter-test'
    testImplementation "org.assertj:assertj-core:${assertjVersion}"
    testImplementation "org.testcontainers:junit-jupiter:${testcontainersVersion}"
    testImplementation "org.testcontainers:postgresql:${testcontainersVersion}"
    testImplementation 'org.springframework.security:spring-security-test'
}

tasks.named('test') { useJUnitPlatform() }
```

**`@Testcontainers` + `@Container` static, or a manual singleton?** Prefer the manual singleton shown below. The JUnit extension manages lifecycle per class; a `static` field plus the extension still starts one container for the JVM, but the moment someone drops the `static` — or a module copies the base without it — you get a container per class and the suite goes from three minutes to forty. The manual singleton (`static final` + `start()` in a static block, never stopped; Ryuk reaps it at JVM exit) cannot be broken that way.

**`testcontainers.reuse.enable=true`** keeps the container alive between local runs. It is a local-developer convenience, set in `~/.testcontainers.properties` and never in the repo: a reused container carries yesterday's rows, which in CI turns "my test assumes an empty table" into a flake you cannot reproduce.

## 3. `AbstractIntegrationTest`

One base class, one container, one place to fix things. Never start your own container inside a test class.

```java
@SpringBootTest(classes = TestApplication.class)
@AutoConfigureMockMvc
@ActiveProfiles("integration")
@ContextConfiguration(initializers = AbstractIntegrationTest.IsolatedSchemaInitializer.class)
abstract class AbstractIntegrationTest {

    // One container for the whole JVM. Started here, never stopped: Ryuk reaps it.
    static final PostgreSQLContainer<?> POSTGRES =
            new PostgreSQLContainer<>("postgres:16");   // or the image with the extension you need

    static { POSTGRES.start(); }

    private static final AtomicInteger CONTEXT_SEQ = new AtomicInteger();

    @DynamicPropertySource
    static void datasource(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.username", POSTGRES::getUsername);
        registry.add("spring.datasource.password", POSTGRES::getPassword);
        // The URL is deliberately NOT set here: the initializer owns it because it carries
        // the per-context schema, and dynamic properties are applied after initializers.
    }

    /** One Postgres schema per Spring context. See the war story below. */
    static class IsolatedSchemaInitializer
            implements ApplicationContextInitializer<ConfigurableApplicationContext> {
        @Override
        public void initialize(ConfigurableApplicationContext ctx) {
            String schema = "ctx_" + ProcessHandle.current().pid() + "_" + CONTEXT_SEQ.incrementAndGet();
            try (Connection c = DriverManager.getConnection(
                         POSTGRES.getJdbcUrl(), POSTGRES.getUsername(), POSTGRES.getPassword());
                 Statement s = c.createStatement()) {
                s.execute("CREATE SCHEMA IF NOT EXISTS " + schema);
            } catch (SQLException e) { throw new IllegalStateException(schema, e); }
            TestPropertyValues                       // the container URL already carries a query string
                    .of("spring.datasource.url=" + POSTGRES.getJdbcUrl() + "&currentSchema=" + schema)
                    .applyTo(ctx.getEnvironment());
        }
    }

    @Autowired protected MockMvc mockMvc;
    @Autowired protected ObjectMapper objectMapper;
    @Autowired private TenantRepository tenants;
    @Autowired private TokenService tokenService;   // the PRODUCTION token service

    /** Nonced, so two tests never collide on a slug. */
    protected Tenant createTenant(String prefix) {
        return tenants.save(Tenant.of(prefix + "-" + UUID.randomUUID().toString().substring(0, 8)));
    }

    /** A real JWT from the real issuer. The user is transient: the filter never hits the DB. */
    protected String mintToken(UUID tenantId, Role role) {
        User user = new User(UUID.randomUUID(), tenantId, role);
        return tokenService.issueAccessToken(user);
    }
}
```

Mint the token with the production issuer, not a hand-rolled string and not `@WithMockUser`. A token that went through your real `TokenService` proves the filter, the claims mapping and the authority names all agree. A mocked principal proves you can mock a principal.

If your build is multi-module and the feature modules cannot see the root module's test classes, duplicate this base verbatim in each module and say so in a comment — an honest copy beats a Gradle test-jar nobody maintains.

> **War story: 106 red across 23 classes, every one of them green alone.**
> A module's 89 integration classes resolved to **33 distinct Spring context configurations** (mostly different `@TestPropertySource` feature-flag sets, plus a few mock-bean sets). Spring's `ContextCache` holds **32** (`spring.test.context.cache.maxSize`). Context 33 evicted the least-recently-used entry, and **eviction closes that context**. Closing a context under `ddl-auto=create-drop` runs Hibernate's drop phase — against the single shared schema every other cached context was still using. Result: `ERROR: relation "tenant" does not exist`, 106 failures, 23 classes, and each class passing on its own. `--max-workers=1` reproduced it perfectly, because the cache is per-JVM, not per-Gradle-worker.
>
> **The fix is the initializer above:** the container stays shared, but every Spring context gets its own schema (`currentSchema=ctx_<pid>_<n>`), created in an `ApplicationContextInitializer`, which Spring runs exactly once per context creation. `create-drop` can then only drop the tables of the context that owns them, so eviction, class ordering and cache size stop mattering.
>
> **Rejected fixes.** `@DirtiesContext`, serialising the suite, or pinning every class to one context: all hide the coupling and make the suite slower. Raising `maxSize`: goes green today, breaks again at context 65, and leaves every context able to destroy every other one.
>
> **The two-minute proof** — squeeze the cache so every context load evicts something:
> ```bash
> ./gradlew :orders:test --tests '*IsolationTest' -PctxCacheMaxSize=2
> ```
> The project property is a two-line wiring in the module's `build.gradle`: `tasks.named('test') { systemProperty 'spring.test.context.cache.maxSize', findProperty('ctxCacheMaxSize') ?: '32' }` — Spring reads that system property as the cache size. Green at any cache size is the invariant. If that goes red, something re-introduced cross-context schema sharing.

**Do not put `@Transactional` on an HTTP-level test.** It wraps the test in a transaction that is rolled back at the end, which means your assertions run inside a transaction the real request would have committed. Constraint violations that fire at flush, `@TransactionalEventListener(phase = AFTER_COMMIT)` listeners, outbox rows, and lazy-loading that works only because the test's session is still open — all of them behave differently from production. Rolling back is convenient; per-context schemas plus unique data per test are correct.

**`@MockBean` (`@MockitoBean` on recent Spring) creates a new context configuration.** Every distinct set of mocked beans is another cache entry, another Postgres schema, another 4-8 seconds of boot. Group the classes that need the same mocks so they share one configuration, and prefer a real bean with a stubbed HTTP transport (WireMock/MockWebServer) over mocking a Spring bean.

## 4. Recipe: integration test for a new endpoint

Seed through the API, act through the API, assert status plus `jsonPath` on the DTO.

```java
class OrderStateMachineIntegrationTest extends AbstractIntegrationTest {

    private String adminToken;
    private UUID orderId;

    @BeforeEach
    void setUp() throws Exception {
        Tenant tenant = createTenant("order-sm");
        adminToken = mintToken(tenant.getId(), Role.ADMIN);
        JsonNode order = postAsAdmin("/api/v1/orders", "{\"sku\":\"A-1\",\"qty\":2}", 201);
        orderId = UUID.fromString(order.get("id").asText());
    }

    @Test
    void admin_walksHappyPath_andReopens() throws Exception {
        transitionAsAdmin("PAID").andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("PAID"));
        transitionAsAdmin("SHIPPED").andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("SHIPPED"));
    }

    // --- helpers: one place for the Authorization header and the JSON body ---

    private ResultActions transitionAsAdmin(String next) throws Exception {
        return mockMvc.perform(patch("/api/v1/orders/{id}/status", orderId)
                .header("Authorization", "Bearer " + adminToken)
                .contentType(APPLICATION_JSON)
                .content("{\"status\":\"" + next + "\"}"));
    }

    private JsonNode postAsAdmin(String path, String body, int expected) throws Exception {
        return objectMapper.readTree(mockMvc.perform(post(path)
                        .header("Authorization", "Bearer " + adminToken)
                        .contentType(APPLICATION_JSON).content(body))
                .andExpect(status().is(expected))
                .andReturn().getResponse().getContentAsString());
    }
}
```

Three rules that make this shape work:

1. **Seed through the API, not repository writes.** A repository `save()` in `@BeforeEach` skips authorization, ownership assignment and tenant stamping — exactly the wiring you are trying to cover. If seeding through the API is painful, that pain is a finding.
2. **Small private helpers, not a framework.** Two or three per class. When a helper needs its own helper, split the test class.
3. **Assert status plus `jsonPath` on the DTO**, never the whole body string — that asserts on serialization order.

## 5. Asserting failures

Error responses are RFC 7807 `ProblemDetail`. Its `detail` field carries an i18n message key or human text — both change without the behaviour changing. Assert on the status and the stable machine-readable fields.

```java
transitionAsAdmin("PENDING").andExpect(status().isConflict())
        .andExpect(jsonPath("$.code").value("illegal_transition"))
        .andExpect(jsonPath("$.from").value("SHIPPED"))
        .andExpect(jsonPath("$.to").value("PENDING"));
```

| Failure | Status | Assert on |
|---|---|---|
| Ownership / tenant breach | **403, never 404** | status only, or `$.code` |
| Illegal state transition | 409 | `$.code`, `$.from`, `$.to` |
| Feature disabled by flag | 403 | `$.code` = `feature_disabled` |
| Validation / bad payload | 400 (syntax) or 422 (semantics) | status + the field list, not the message |

Ownership breach is 403, never 404 — a 404 leaks whether the resource exists. Someone will argue that 404 "hides" the resource better. It does the opposite: a probe that gets 404 for a random id and 403 for a real one has just enumerated your database.

In Mockito unit tests, assert the exception **type**, never its message:

```java
assertThatThrownBy(() -> service.cancel(orderId))
        .isInstanceOf(OwnershipViolationException.class);
```

## 6. Tenant and ownership tests

Services are `@Transactional` and `findById` **bypasses** your Hibernate filters — the filter applies to queries the session builds, not to a primary-key load through the persistence context. So the service must ownership-check explicitly, and the test must prove it did. Always test both directions:

```java
@Test
void otherTenant_cannotReadOrder() throws Exception {
    Tenant other = createTenant("other");
    String otherToken = mintToken(other.getId(), Role.ADMIN);

    mockMvc.perform(get("/api/v1/orders/{id}", orderId)
                    .header("Authorization", "Bearer " + otherToken))
            .andExpect(status().isForbidden());     // 403, not 404
}
```

- Owner succeeds, foreign tenant gets 403. One test each; a happy-path-only test proves nothing about isolation.
- Mint the second tenant's token with the same `mintToken` helper. Never fake the tenant claim by hand.
- For list endpoints, decide the contract and assert it: a cross-tenant read either comes back **empty** (`jsonPath("$.content").isEmpty()`) or **403**. Pick one per endpoint, document it, pin it in a test. "It returns something reasonable" is not a contract.
- The same probes belong at E2E against the deployed assembly — see [e2e-testing-guide.md](./e2e-testing-guide.md). Green here and red there means a gateway or proxy is stripping something.

## 7. Mockito unit tests

Reach for Mockito when the behaviour is genuinely database-independent: a state-machine transition table, a pricing rule, a parser, a mapper, a retry/backoff policy.

```java
@ExtendWith(MockitoExtension.class)
class DiscountServiceTest {

    @Mock private PricingRepository pricing;
    @InjectMocks private DiscountService service;

    @Test
    @DisplayName("Should apply the tier discount when the cart exceeds the tier threshold")
    void appliesTierDiscount() {
        when(pricing.tierFor("GOLD")).thenReturn(new Tier("GOLD", 0.15));
        Money result = service.priceFor("GOLD", Money.of(200));
        assertThat(result).isEqualTo(Money.of(170));
    }
}
```

Rules, in order of how often they are broken:

1. **No `verify()` as the primary assertion.** Asserting that `repository.save()` was called tests the implementation, not the result. Assert the returned value or the observable state. `verify()` is right only when the call **is** the behaviour: an audit log entry, an outbox row, an idempotency marker. Then verify it, and say why in the test name.
2. **One scenario per test.** Given/when/then. Many asserts in one test is a design smell — split into variations.
3. **Name it as behaviour.** `Should X when Y` in `@DisplayName`, or a method name that already reads (`appliesTierDiscount`). Do not write both badly.
4. **No production constants in tests.** Assert on literals. `assertThat(fee).isEqualTo(DiscountService.DEFAULT_FEE)` passes forever, including after someone changes `DEFAULT_FEE` to the wrong number.
5. **Cover every result that matters**, not just the return value: the audit entry, the emitted event, the log ops greps for.
6. **Parameterized tests are fine in general** — `@ParameterizedTest` + `@CsvSource` is excellent for a transition table — but do not introduce them into a repo that consistently uses one method per case. Consistency inside a suite beats your preferred style.

For an outbound HTTP client, do not mock the client class you are testing. Stand up WireMock or MockWebServer, point the client at it, and assert the request it sent and the response it parsed. That is a unit test with a real transport and a deterministic peer.

## 8. Naming and layout

| Kind | Class name | Method name |
|---|---|---|
| Real DB + HTTP | `<Feature>IntegrationTest` | reads as behaviour, often carrying the status: `illegalTransition_is409_withFromTo` |
| Mockito, pure logic | `<Service>Test` | `appliesTierDiscount`, or `@DisplayName("Should ... when ...")` |
| Architecture rules | `ArchitectureTest` | `controllersDoNotTouchRepositories` |

`@Nested` is fine for grouping scenarios and is not required. `@DisplayName` is optional when the method name already reads as a sentence — add it when the scenario needs a clause the method name cannot carry.

Optional, cheap, worth it on a modular monolith: **ArchUnit**. One test class pinning "controllers do not reference repositories", "no cycle between modules", "nothing outside `security` imports the token service". It catches layering drift that no functional test can see, in under a second.

## 9. Avoiding brittle tests

- **Never assert on `detail` text.** It is an i18n key or human copy. Assert status and stable fields.
- **Tolerate pre-existing data.** The container is shared across the whole run and DEV seed data may be present. Prefer find-or-create over "the table is empty".
- **Unique data per test.** Nonced slugs, nonced emails, `createTenant(prefix)`. Two tests that both create `acme` will collide the day someone enables parallel execution.
- **No ordering dependence.** If class A leaves a flag enabled and class B assumes it is disabled, you have a suite that passes in one order and fails in another. Neither test is wrong; the coupling is.
- **Every test states its own preconditions.** In one of our projects a sweep passed 50 out of 50 when run alone and failed 14 in the full suite, because it relied on whichever spec happened to run first to clear a piece of user state. Parallel execution means declaration order is not even execution order.
- **A pre-existing red is a documented baseline or a bug, never a habit.** Never write "ignore one known red" into a checklist — a checklist that teaches people to skip a red is how a real one hides.

## 10. Commands and the known-red baseline

| What | Command | Note |
|---|---|---|
| Whole suite | `./gradlew cleanTest test` | `cleanTest` is not optional — see below |
| One class (multi-module) | `./gradlew :orders:test --tests 'com.example.orders.OrderStateMachineIntegrationTest'` | **Must** be module-scoped |
| Wildcard | `./gradlew :orders:test --tests '*StateMachine*'` | Same module scoping |
| Report | open `orders/build/reports/tests/test/index.html` | The stack traces live here, not in the console |

**The single-test command must name the module.** A bare `./gradlew test --tests 'com.example.orders.FooTest'` fails the build in a multi-module project: every sibling module runs the same filter, finds nothing, and reports `No tests found for given includes`. Put the module-scoped form in the repo's `docs/testing.md` and in `AGENTS.md`, because it is the command an AI tool will copy.

**Pass `cleanTest`, or the gate can abstain and look like it passed.** One afternoon a consolidated gate reported `BUILD SUCCESSFUL in 1m 12s` — and two of the four test tasks were `UP-TO-DATE`, never executed, because Gradle judged their inputs unchanged. The same command with `cleanTest` took **10m 6s** and actually ran. A gate that finishes suspiciously fast has not passed, it has abstained. Read the task list, never just the exit code.

`--offline` speeds up a local run and works only because the dependencies are already cached. Drop it on a fresh machine's first run, or you will debug a resolution error that is not real.

Record the baseline in `docs/testing.md`, with counts and a date, so nobody has to guess whether a red is theirs:

| Suite | Expectation on a clean tree | Count | Measured |
|---|---|---|---|
| `:orders:test` | 0 red | 812 tests / 96 classes | 2026-09-07 |
| `:billing:test` | 0 red | 274 tests / 50 classes | 2026-09-07 |
| `:platform:test` | 0 red, holds `BeanNameCollisionTest` | 130 tests / 15 classes | 2026-09-07 |

**The cross-module collision test is not optional in a gate**, even for a change that looks like it touches one module. A module's test context never loads a sibling module, so two stereotyped classes wanting the same bean name pass every module suite and then refuse to boot the application. One test, in one module, that starts the full application context, is the only thing that can see it.

**Coverage** is a floor on new code with a ratchet, never a target. JaCoCo, wired into `check`:

```groovy
tasks.named('jacocoTestCoverageVerification') {
    violationRules { rule {
        element = 'CLASS'
        excludes = ['*.config.*', '*.dto.*', '*Application']
        limit { counter = 'LINE'; value = 'COVEREDRATIO'; minimum = 0.80 }
    } }
}
tasks.named('check') { dependsOn 'jacocoTestCoverageVerification' }
```

Raise the floor when the suite clears it; never lower it to make a build green. For reference, traditional quality gates warn under 80% and fail under 60% coverage on **new** code, same for condition coverage, with a 3% duplication ceiling. On AI-driven projects we do not treat a Sonar-style gate as mandatory: the number is easy to fake, and a green number you cannot trust is worse than an honest gap.

## 11. Day 1 / Week 1 — greenfield Spring service

| When | Do |
|---|---|
| Day 1, hour 1 | Add `spring-boot-starter-test` + Testcontainers. Write `AbstractIntegrationTest` (section 3). Write one test that boots the context and asserts `GET /actuator/health` is 200. Prove the harness before you trust its verdict. |
| Day 1, hour 2 | Put the module-scoped single-test command in `README.md` and `AGENTS.md`. Run it. Paste the output. |
| Day 1, rest | CI job running `./gradlew cleanTest build`, marked as a required check. |
| Day 2-3 | First real integration test on the first endpoint that writes: create, read back, assert the DTO. Then the 403 probe for a second tenant. |
| Day 4-5 | First Mockito test on the first pure rule you write (pricing, transition table). Add the ownership-both-directions test for every endpoint that returns a row. |
| Week 1 close | Baseline table in `docs/testing.md` with counts and a date. JaCoCo floor set at whatever you actually have, ratcheting up only. |

## 12. Day 1 / Week 1 — legacy Spring service with zero tests

| When | Do |
|---|---|
| Day 1, hour 1 | Get Testcontainers to boot the Spring context **at all**. Nothing else. Expect missing config, a bean that calls an external service at startup, a migration that assumes a schema. Fix until one empty test passes. |
| Day 1, hour 2 | Find and record the real single-test command. In a multi-module build, verify it is module-scoped. Record what is already red on a clean checkout: "`FooTest.bar` fails on a clean checkout — not your regression." |
| Day 2 | One characterization test on the riskiest endpoint — the one that moves money or changes permissions. Assert what it does today, not what it should do. That test is your safety net for every later change. |
| Day 3 | Ownership 403 probes on the top three endpoints that return someone's data. These find real bugs in legacy services more often than anything else on this list. |
| Day 4-5 | Adopt the rule: if you fix a bug, write the test that would have caught it. Do not schedule a coverage sprint. |
| Week 1 close | Baseline table with counts and a date; JaCoCo floor set to the current number and ratcheted on new code only. Never a big-bang rewrite of the test suite. |

## 13. Same idea in Node, Python, Go

| | Node / TypeScript | Python | Go |
|---|---|---|---|
| Runner | `vitest` or `jest` | `pytest` | `go test` |
| Single test | `npx vitest run -t 'name'` | `pytest -k 'name'` | `go test ./orders -run TestOrderStateMachine` |
| Container DB | `testcontainers` (node) | `testcontainers-python` | `testcontainers-go` |
| HTTP-level test | `supertest` against the app instance | `httpx.AsyncClient(transport=ASGITransport(app=app))` | `net/http/httptest` |
| Outbound HTTP stub | `msw` / `nock` | `respx` / `responses` | `httptest.NewServer` |
| Shared container | module-level singleton in a global setup file | session-scoped fixture in `conftest.py` | `TestMain` in the package |

The position does not change with the language: seed through the API, assert status plus machine-readable fields, test ownership in both directions, keep one container for the run.

---

## Sources & further reading

- Spring Boot reference, Testing (`@SpringBootTest`, `@DynamicPropertySource`): https://docs.spring.io/spring-boot/reference/testing/index.html
- Spring Framework TestContext framework, context caching: https://docs.spring.io/spring-framework/reference/testing/testcontext-framework.html
- Testcontainers for Java — Postgres module, singleton pattern, reuse: https://java.testcontainers.org/
- JUnit 5 user guide: https://docs.junit.org/current/user-guide/ | AssertJ: https://assertj.github.io/doc/ | Mockito: https://site.mockito.org/
- RFC 9457 (obsoletes RFC 7807), Problem Details for HTTP APIs: https://www.rfc-editor.org/rfc/rfc9457
- Michael Feathers, *Working Effectively with Legacy Code* — characterization tests
- Gerard Meszaros, *xUnit Test Patterns* — the vocabulary for the smells in section 9

## Related

- [testing-from-zero.md](./testing-from-zero.md) — layers, the smell catalogue, and how to drive an AI tool
- [e2e-testing-guide.md](./e2e-testing-guide.md) — the same ownership probes against a deployed assembly
- [enforcement/README.md](./enforcement/README.md) — instructions, hooks and CI gates that make these rules binding

_Last reviewed: 2026-09-07._
