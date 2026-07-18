# Constitution: Principles and Do-Not-Break

Best used when: creating or amending `docs/constitution.md`.
Read before editing: `analysis-checklist.md` findings (patterns, sensitive areas, quality/process, incidents).
Related docs: `structure-and-router.md` (the change workflow's self-review step is the compliance check against this file), `file-catalog.md`.

The constitution is the project's governance document: the principles and non-negotiables every agent must consider on EVERY change. It is the file the router marks "read when: ANY change (always)", so it competes for context on every task. Budget: 100 lines. Density over completeness. It holds only the WHAT-must-hold; the detail — techs, guidelines, conventions, testing rules — lives in the owner docs of the catalog, which it links to.

## Derivation process

1. **Collect explicit input.** If the user states principles ("TDD sempre", "zero downtime migrations", "accessibility obrigatória"), those enter as `[declared]`.
2. **Infer from the repo.** Derive candidate principles from evidence: CI gates, lint configs, test patterns, PR templates, consistent code patterns. Each cites its evidence and enters as `[inferred]`.
3. **Mine incidents.** Hotfix commits, rollbacks, post-mortem notes, and the user's war stories become Do-Not-Break entries with the incident cited.
4. **Fill the template precisely.** No placeholder left unresolved; anything unresolvable becomes `To Confirm`, never a plausible invention.
5. **Present for ratification.** Show the user the derived constitution highlighting every `[inferred]` and `To Confirm` item before finalizing. The number of principles is the project's decision, not the template's: 4 strong principles beat 12 weak ones.
6. **Version it.** Semantic versioning: MAJOR for principle removal/reversal, MINOR for new principle, PATCH for clarification. Record an amendment log line per change.
7. **Propagate amendments.** When the constitution changes, check dependent artifacts (core docs, guides, AGENTS.md working rules, PR template) for contradictions and sync them in the same change.

## Template

```markdown
# <Project Name> Constitution
Version: 1.0.0 · Ratified: <date> · Last amended: <date>

## Principles
<3-7 numbered principles. Each: name, one-paragraph rule, and its rationale or evidence.
Declared by the team or inferred from the repo — tag which.>

1. **<Name>** — <rule>. Evidence: <CI config / observed pattern / team declaration>. [declared|inferred]

## Non-negotiable standards
<Hard constraints an agent must never violate. Testing philosophy, architectural
boundaries, security baselines, compatibility promises. Each verifiable. Each links
to the owner doc that holds the HOW (conventions.md, testing.md, security-guide.md...).>

## Do Not Break
<Critical invariants: business rules, API contracts, DB schema assumptions,
integrations, background jobs. Where an incident motivated the rule, cite it —
"validated by incident <date>: <one-line consequence>" — a rule with a scar gets
followed; a bare prohibition gets rationalized away. Inferred items marked:>
- <invariant>. [To Confirm]

## Compliance check
Before finishing any change, verify it against every principle and Do-Not-Break item.
A change that violates the constitution requires explicit human approval, not a workaround.

## Amendments
- 1.0.0 (<date>): initial ratification.
```

## Quality bar

- Every principle is checkable: an agent reading a diff can answer "does this comply?" If it cannot, the principle is a platitude — cut or sharpen it.
- Every `[inferred]` principle cites concrete evidence. No evidence, no principle.
- Do Not Break with no repo signal: infer candidates from the sensitive-areas categories in `analysis-checklist.md` and mark ALL `To Confirm`. Empty is worse than uncertain.
- If the repo already keeps a constitution elsewhere (e.g. Spec Kit's `.specify/memory/constitution.md`): do NOT create a competing file. Route AGENTS.md to the existing one, improve it in place if invited, and keep Do-Not-Break content there.
