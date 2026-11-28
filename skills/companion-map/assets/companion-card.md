# <repo-name>

> Card for the companion map. Fill every section from files in this repository. Cite `path:line`.
> Leave a section as "not verified" rather than guessing.

**Role:** <one sentence: what a user loses if this repo is down>

**Location:** `../<repo-name>/` · clone: `<url>` · default branch: `<branch>`

**Stack:** <language, framework, build tool, runtime>

## Entry points

| Kind | Where | Notes |
|---|---|---|
| HTTP | `<path to controllers or routes>` | <base path> |
| Jobs / consumers | `<path>` | <schedule or queue> |
| UI routes | `<path to router>` | <only for front ends> |

## Provides (others depend on these)

| Contract | Defined in | Consumed by |
|---|---|---|
| `<endpoint, operation, event or library API>` | `<path:line>` | `<companion>` |

## Consumes (this repo depends on these)

| Contract | Called from | Owner |
|---|---|---|
| `<endpoint, operation or event>` | `<path:line>` | `<companion>` |

## Run and test

```bash
<command to build>
<command to run locally>
<command to run the tests>        # how long it takes: <time>
```

Source of these commands: `<README, Makefile or CI file>`.

## Do-not-break

- <behaviour consumers rely on that no test protects>

## Open questions

- <what could not be verified, and who would know>
