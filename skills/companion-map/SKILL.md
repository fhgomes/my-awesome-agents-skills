---
name: companion-map
description: >
  Map the companion repositories of a system (back end, front end, E2E tests, the internal services it
  calls, shared libraries) into one cross-linked harness, so a coding agent working in any of them knows
  the others exist, what each one owns and where to look. Use ALWAYS when the conversation involves:
  "map the companion repos", "the agent only sees one repo", "multi-repo context", "cross-repo impact",
  "which repo owns this", "who calls this service", "front end and back end are in different repos",
  "the E2E tests live in another repo", "give the AI the whole system", a migration or refactor that
  crosses repository boundaries, or a harness / AGENTS.md that stops at the repo edge.
  Also trigger on: "companion repositories", "sibling repos", "ecosystem map", "contract between repos",
  "cross-pointers", "workspace harness". Also triggers on the equivalent phrases in other languages.
---

# Companion Map: one harness for the whole system

A coding agent that sees one repository answers "what does this change touch?" with half the system
missing. This skill gives it the rest: every companion repository gets a card, the cards get an index
with the call graph, and each repo's `AGENTS.md` gets pointers to the cards it needs. Nothing here is
generated from imagination. Every line is backed by a file you can open.

## When to run it

- Before a migration, upgrade or contract change that crosses repositories.
- When the agent keeps proposing changes that break a consumer it cannot see.
- When onboarding an agent (or a person) to a system that lives in three or more repos.

## What you produce

```
<workspace>/
  harness/
    companions/
      INDEX.md              the map: every repo, its role, who calls whom
      <repo-name>.md        one card per companion repository
  <repo-a>/AGENTS.md        gains a "Companions" block with pointers
  <repo-b>/AGENTS.md        same
```

`<workspace>` is the folder that holds the checkouts side by side. If the repos cannot sit side by side,
keep `harness/` in the repo people open most and write the other locations as clone URLs.

## Procedure

### 1. Find the companions (evidence first, then ask)

Search the repo you are in for references that leave it. Record the file and line of each hit.

| Signal | Where to look |
|---|---|
| Base URLs and hosts | `application*.yml`, `.env*`, `environment*.ts`, Helm values, proxy config |
| Generated or hand-written clients | WSDL/OpenAPI files, `*Client`, `*Gateway`, `*Adapter`, Feign/Retrofit/RestTemplate/WebClient usage |
| Shared libraries | build files: internal group ids, private registries, git submodules, `file:` dependencies |
| Front end to back end | API base path constants, HTTP services, proxy rewrites |
| Tests that live elsewhere | CI pipelines that clone or trigger another repo, `baseUrl` in Cypress/Playwright configs |
| Async links | topic, queue and exchange names; schedulers that call out |

Then show the list to the user and ask two things only: which of these exist as repositories they can
check out, and what is missing. People know about the repo that no config file mentions.

### 2. Write one card per companion

Use `assets/companion-card.md`. Open the companion repository to fill it; do not fill a card from the
caller's point of view alone. A card answers:

- **Role**: one sentence. What breaks for a user if this repo is down.
- **Entry points**: where a request, a job or a user action comes in (controllers, routes, consumers).
- **Provides**: the contracts others consume, with the file that defines each one.
- **Consumes**: what it calls in other companions, with the calling file.
- **Run and test**: the commands that work today, copied from its own docs or CI, not invented.
- **Do-not-break**: behaviour consumers depend on that no test protects (field formats, ordering,
  null versus empty, time zones, defaults applied by a client library).
- **Open questions**: what you could not verify. An honest gap beats a confident guess.

### 3. Write the index

`harness/companions/INDEX.md` holds a table (repo, role, location, card) and the call graph as plain
text arrows, one per line, each with its evidence:

```
orders-web  -> orders-backend    REST /api/orders/**   (orders-web/src/app/core/api.ts:12)
orders-backend -> catalog-service  SOAP ItemPort.getItem (orders-backend/.../CatalogClient.java:41)
```

An arrow without evidence does not go in. Put it under "Unverified" instead.

### 4. Cross-point the repos

Add a short block to each repo's `AGENTS.md` (create the file if the repo has none). Keep it a router:
when to leave this repo, and which card to read.

```markdown
## Companions

This repo is one part of a larger system. Map: ../harness/companions/INDEX.md

| When you touch | Read first |
|---|---|
| anything under `client/catalog/` | ../harness/companions/catalog-service.md |
| a response DTO used by the UI | ../harness/companions/orders-web.md |
| an endpoint path or status code | ../harness/companions/orders-e2e.md |
```

### 5. Prove it works

Ask the agent, from inside one repo, a question it could not answer before, for example: "I am
changing the response of `GET /api/orders/{id}`. List every screen and every E2E spec affected, with
file paths." If the answer has paths in the other repos, the map works. If it does not, the pointers
are missing or too vague; fix them and ask again.

## Rules

- Evidence or nothing: every role, arrow and contract cites a file. Mark the rest as unverified.
- Cards describe today, not the plan. Target architecture goes in a spec, not in the map.
- No secrets and no production hosts in cards. Name the environment, not the URL.
- Keep cards short enough to read in one sitting (about one screen). Link out for detail.
- Re-run step 1 when a client, a base URL or a dependency on another repo is added or removed.

## Works well with (optional)

- A single-repo harness skill, to give each repository its own router and conventions first.
- `reverse-trace`, which uses this map to follow one call across repositories up to the screen.
