# magic-questionnaire

Design and build one-question-per-screen qualification wizards that feel like a diagnosis instead of a form.

## Purpose

Step-by-step onboarding surveys convert because every answer is reflected back to the respondent and the ending fits them. Most teams copy the *look* of a wizard they liked and keep the content generic — or worse, copy the reference's questions, which measure someone else's business. This skill puts the effort where it pays: discovery, question design, the mirror loop and honest routing, then a small, explicit UI contract.

Use it for pre-call qualification, application forms for programs and high-ticket services, SaaS onboarding and segmentation, and interactive lead-magnet assessments.

## Features

- **Discovery first** — the six questions to answer before writing a single question (the decision it drives, fit and not-fit, the core problem in the respondent's words, real blockers, volume vs. quality, where the data goes)
- **Question design** — axes, pain-ladder answers with label + sub-label, "why we ask" subtitles, fence on step 1, contact data only at the end; worked examples for a coaching program, a self-serve SaaS and a lead-magnet assessment
- **The mirror loop** — a reaction line per answer and exactly one just-in-time "problem / solution" education block
- **Routing** — additive scores per dimension, forced exits, ordered rules, at least three honest endings (fit / early / not-a-fit) and a personal read-back
- **UI contract** — single-accent tokens, list vs. grid layouts, progress, navigation, accessibility (radiogroup, arrow keys, focus management, reduced motion)
- **Data and analytics** — per-step persistence, id-based payload with versioning, event schema and the weekly tuning loop
- **Tooling** — `scripts/validate_questionnaire.py` (stdlib-only; structure, content rules, and proof that every route is reachable with the route distribution) and `examples/wizard.html` (dependency-free demo driven by the same JSON config)

## Quick Start

```bash
# 1. Start from the example config and rewrite the content for your business
cp examples/questionnaire.example.json my-questionnaire.json

# 2. Validate structure, content rules and route reachability
python scripts/validate_questionnaire.py my-questionnaire.json

# 3. Preview: paste the config into the <script id="questionnaire"> block of
#    a copy of examples/wizard.html and open it in a browser
```

## See Also

- [SKILL.md](SKILL.md) — the full procedure, anti-patterns and deliverables checklist
- [references/question-design.md](references/question-design.md), [ui-contract.md](references/ui-contract.md), [routing-and-data.md](references/routing-and-data.md)
