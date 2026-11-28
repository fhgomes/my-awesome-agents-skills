# Reverse trace: <sink>

- **Sink:** `<full signature>` in `<path:line>`
- **Why it is changing:** <one line>
- **Snapshot:** `<repo>@<commit>` · `<repo>@<commit>` · `<repo>@<commit>`
- **Searched:** <repositories and folders> · **Not searched:** <what was out of reach>

## Paths

### Path 1: <screen or job as a user would name it>

| Hop | Where | Evidence |
|---|---|---|
| Sink | `<Class.method>` | `<path:line>` |
| Caller | `<Class.method>` | `<path:line>` |
| Caller | `<Class.method>` | `<path:line>` |
| Entry point | `<GET /api/...>` | `<path:line>` |
| Front-end call | `<service.method>` | `<path:line>` |
| Component | `<component>` | `<path:line>` |
| Screen | `<name>` at `<route>` | `<path:line>` |

**Tests:** `<test file>` (<what it asserts>)
**Coverage:** `covered` | `happy-path` | `not-covered`
**Action:** <run existing test / add cases / manual steps>

### Path 2: ...

## Unverified hops

- <hop, why it could not be confirmed, who would know>

## Summary

| Coverage | Paths |
|---|---|
| covered | <n> |
| happy-path | <n> |
| not-covered | <n> |
