# Routing, data model and analytics

Load this when defining scoring, endings, persistence or events.

## Config format

The questionnaire is a single JSON document — the source of truth for both
the demo and the production component. See
[../examples/questionnaire.example.json](../examples/questionnaire.example.json).

```jsonc
{
  "id": "intro-call-qualifier",          // stable, used in storage and events
  "version": 3,                          // bump on any content change
  "steps": [
    {
      "id": "stage",                     // stable key, never the display text
      "type": "single",                  // "single" | "text" | "contact"
      "layout": "list",                  // "list" | "grid" (single only)
      "emoji": "🧭",
      "title": "Where are you right now?",
      "why": "So we only recommend what fits your stage.",
      "options": [
        {
          "id": "beginner",
          "emoji": "🌱",
          "label": "Just starting out",
          "hint": "First job or under 2 years",
          "reaction": "Early is fine — we'll point you to the right starting place.",
          "score": { "fit": 0 },
          "route": "not-a-fit",          // optional: forces this ending
          "educate": false               // optional: true shows the education block
        }
      ]
    },
    { "id": "aspiration", "type": "text", "optional": true, "title": "...", "why": "...", "placeholder": "..." },
    { "id": "contact", "type": "contact", "title": "...", "why": "...", "fields": ["email", "name"] }
  ],
  "education": { "problem": "...", "solution": "..." },
  "routes": [
    { "id": "book",      "when": { "fit": { "gte": 5 } }, "title": "...", "body": "...", "cta": { "label": "...", "href": "..." } },
    { "id": "nurture",   "when": { "fit": { "gte": 2 } }, "title": "...", "body": "...", "cta": { "label": "...", "href": "..." } },
    { "id": "not-a-fit", "default": true,                 "title": "...", "body": "...", "cta": { "label": "...", "href": "..." } }
  ],
  "readback": [
    { "when": { "fit": { "gte": 5 } }, "text": "..." },
    { "default": true, "text": "..." }
  ]
}
```

## Routing algorithm

1. Sum `score` per dimension over all selected options.
2. If any selected option has `route`, the **earliest step's** forced route
   wins. (Fence questions come first, so the fence decides.)
3. Otherwise walk `routes` in order; the first whose `when` matches wins.
   `when` is an AND of `{dimension: {gte|lte|eq: n}}` conditions.
4. Otherwise the route marked `default: true`. Exactly one default.

The same matching logic picks the `readback` entry.

Keep it this simple. If the user wants weights, decision trees or ML, push
back: the routing must be explainable to the person reading the result and to
whoever tunes it next month.

## Reachability

A route nobody can reach is dead copy; a route everybody reaches means the
questionnaire qualifies nobody. The validator enumerates answer combinations
(capped, with sampling past the cap) and reports how many reach each route.
Treat a route share above ~80% as a smell to discuss with the user.

## Persisted payload

```json
{
  "questionnaire_id": "intro-call-qualifier",
  "questionnaire_version": 3,
  "session_id": "anon-uuid",
  "answers": { "stage": "mid-above-title", "awareness": "knows-not-why", "aspiration": "free text…" },
  "scores": { "fit": 6 },
  "route": "book",
  "contact": { "email": "…", "name": "…" },
  "started_at": "ISO-8601",
  "completed_at": "ISO-8601 | null",
  "last_step": "contact"
}
```

- Save after **every** answer (upsert by `session_id`), not only on submit.
- Store option ids, never labels.
- Keep `questionnaire_version` so old answers stay interpretable after copy
  changes.
- Contact data is personal data: state the purpose on the contact step,
  store it with the same protections as any lead, and let partial
  (anonymous) sessions expire.

## Analytics events

| Event | Properties |
|---|---|
| `questionnaire_started` | id, version, session_id, entry source |
| `questionnaire_step_viewed` | step_id, step_index |
| `questionnaire_answered` | step_id, option_id (or `text_length` for text) |
| `questionnaire_back` | from_step_id |
| `questionnaire_completed` | route, scores |
| `questionnaire_cta_clicked` | route, cta href |

Tuning loop: look at drop-off per step and route split weekly. A step with an
outsized drop is usually a question that feels intrusive (move it later or
add a better "why we ask") or an option set nobody recognizes themselves in.

## Downstream hand-off

- Pre-fill the booking / intake form with the structured answers; replace
  the "tell us about yourself" free-text field where possible.
- Show the reviewer the read-back plus the answers as labeled chips — that is
  what makes triage take seconds instead of minutes.
- If the respondent later becomes a customer, seed their profile from the
  same payload so they are never asked twice.
