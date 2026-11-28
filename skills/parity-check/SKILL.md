---
name: parity-check
description: >
  Prove that an old integration path and its replacement return equivalent data before any caller is
  switched: expose the old client's final output and the new path's output side by side, call both
  with the same inputs (a k6 script is included), and compare the results field by field as the
  consumer sees them. Use ALWAYS when the conversation involves: replacing SOAP with REST, swapping a
  client library or SDK, moving to a new API version, "are the two responses the same", "parity test",
  "shadow comparison", "did the migration change the data", "the screen works but the data is wrong",
  "compare old and new endpoint", or a migration where UI tests pass but nobody checked the payload.
  Also trigger on: "contract parity", "dual run", "side-by-side diff", "golden comparison", "k6 compare",
  "DTO diff". Also triggers on the equivalent phrases in other languages.
---

# Parity Check: same input, same data, old path versus new path

UI tests prove the screen works. They rarely prove the data behind it is the same. When an integration
is replaced (SOAP to REST, one client library to another, v1 to v2 of an API), the dangerous changes are
the quiet ones: a field renamed, an empty list that became null, a date that moved a time zone, a long
that became an int, a default the old client applied that the new path does not. A parity check calls
the old path and the new path with the same input and compares what the consumer would see.

## When to run it

- Before switching any caller from the old integration to the new one.
- For every operation in the migration inventory, reads first, writes after.
- Again after each fix, until the diff is empty or every remaining difference is accepted in writing.

## Setup: two routes, one comparison

1. **Old path route.** A test-only route in the application that executes the **old client exactly as
   production does** (same configuration, same mappers) and returns its final output as JSON. Compare
   what the application ends up with, not the raw SOAP envelope: the old client library applies
   conversions and defaults that consumers rely on.
2. **New path route.** The same operation through the new client or adapter, returning the DTO the
   callers will receive after the switch.
3. **Same input set.** A list of real identifiers and parameters from a non-production environment:
   common cases, empty results, the largest payload you can find, records with optional fields missing.
4. **Compare as the consumer.** Normalize only what the consumer does not see (field order, whitespace).
   Everything else is a difference.

Keep both routes out of production builds (profile, feature flag or separate test module).

## What to compare (the checklist)

| Area | Typical silent change |
|---|---|
| Attribute names | `supplierName` vs `supplier_name`, renamed or moved fields |
| Nesting | an object flattened, or a nested DTO that became an id |
| Lists | missing versus empty, order changed, duplicates removed |
| Null versus empty | `""` versus `null` versus absent field |
| Dates and times | time zone, offset, precision, local date versus instant |
| Numbers | long versus int overflow, decimal scale, rounding, numbers as strings |
| Defaults | values the old client library filled in when the source was empty |
| Codes and enums | padding, case, unknown values, a new value the consumer cannot map |
| Errors | the status and error shape for "not found", "forbidden" and timeouts |

## Procedure

1. Pick one operation from the inventory and write its input list.
2. Run the script (`assets/parity-read.k6.js`) against a non-production environment:

   ```bash
   k6 run -e BASE=https://staging.example.test -e OLD=/test/old/items -e NEW=/api/v2/items \
          -e IDS=A-100,A-101,A-102 assets/parity-read.k6.js
   ```

3. Read every difference. For each one decide: bug in the new path (fix it), deliberate change (record
   who accepted it and why), or noise the consumer never sees (add it to the normalizer, with a comment).
4. Re-run until the diff is empty. Keep the script in the repository next to the migration.
5. **Writes come last and only outside production.** Run the old and the new write against two isolated
   copies of the same data, then compare the read-back of both, not the write responses.

## Rules

- Same input, same environment, same moment. Do not compare a staging call with a cached file.
- The old path is the reference. A difference is a bug until someone accepts it.
- Never weaken the comparison to make the run green. Normalize only what no consumer can observe.
- No production hosts, no production credentials, no personal data in the input list or the reports.
- Parity is per operation. "Most fields match" is a failed run.

## Works well with (optional)

- `reverse-trace`, to know which operations and paths matter most before writing input lists.
- `companion-map`, to find the consumers whose expectations define "equivalent".
