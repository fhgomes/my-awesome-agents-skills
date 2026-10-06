---
name: magic-questionnaire
description: >-
  Design and build "magic questionnaires": short, one-question-per-screen
  qualification wizards that feel like a diagnosis instead of a form — used
  before a free call or booking, as an application gate for a program or
  high-ticket service, as SaaS onboarding/segmentation, or as an interactive
  lead magnet. Covers discovery (what decision the questionnaire drives, who is
  a fit and who is not), question design (pain-ladder answers, label +
  sub-label, one axis per question, never copy a competitor's questions),
  the mirror loop (a reactive line per answer, one just-in-time "problem /
  solution" education block), scoring and routing to several honest endings
  (book / nurture / polite not-a-fit), anonymous-first capture with email at
  the end, partial-answer persistence, the visual contract (single accent,
  big tap targets, progress bar, Back on every step), accessibility, analytics
  per step, and E2E tests per route. Ships a JSON config format, a validator
  that proves every route is reachable, and a dependency-free HTML demo. Use
  whenever the user asks to "create a questionnaire like this", "build an
  onboarding wizard", "qualification form before booking", "application form
  for my mentorship/program", "quiz funnel", "intake wizard", "lead magnet
  quiz", "segment users on signup", "pre-call survey", "make the form feel
  less like a form", or shares screenshots of a step-by-step survey they liked
  and wants their own version. Also triggers on the equivalent phrases in
  other languages.
---

# Magic questionnaires

A magic questionnaire is a **diagnosis performed in public**: one question per
screen, each answer reflected back immediately, ending in a route that fits
the person. Done right, the respondent feels *seen* before they ever talk to a
human — and the business receives a structured profile instead of a paragraph.

Done wrong, it is a long form wearing a progress bar. The difference is almost
entirely in the **content design**, not the UI. Spend your effort there.

## 0. The one rule that matters most

**Never copy another product's questions.** When the user shows a wizard they
liked, copy the *mechanics* (layout, mirror loop, progress, routing) and
redesign the *questions* from the user's own business. A competitor's
questions measure the competitor's axis — the thing *they* sell. Asked by
someone else, they measure the wrong thing.

Always split the analysis of a reference into two columns: **mechanics to
reuse** and **content to redesign**. Say this split out loud to the user.

## 1. Discovery — answer these before writing a single question

Ask the user (or derive from their docs) and write the answers down:

1. **What decision does this questionnaire drive?** Book a call? Which plan?
   Which onboarding path? Accept/decline an application? If there is no
   decision, there is no questionnaire — there is a survey, and surveys
   don't convert.
2. **Who is a fit, and who is explicitly not?** You need both lists. A
   questionnaire that cannot say "not a fit" qualifies nobody.
3. **What is the core problem, in the respondent's words?** Not the
   business's jargon. "I do senior work but I'm paid as mid-level", not
   "strategic invisibility".
4. **What are the 3–5 real blockers?** These become answer options. The best
   source is real conversations, sales calls, support tickets, intake notes.
5. **Volume vs. quality.** Self-serve, high-volume products want completion
   and segmentation. High-ticket, low-volume services want qualification and
   a pre-diagnosed lead. This changes gating, length and endings (section 5).
6. **What happens to the data?** Who reads it, where it is stored, what
   pre-fills downstream (booking form, CRM, onboarding profile).

If the user cannot answer 1 and 2, stop and help them answer — building the
UI first is the classic waste.

## 2. Question design

Full guide with worked examples: [references/question-design.md](references/question-design.md).

- **4–6 questions.** Fewer feels trivial, more feels like work. One optional
  free-text question at most, near the end.
- **One axis per question.** Seniority, problem awareness, blocker,
  commitment, goal. If an answer could belong to two axes, split or cut.
- **Order: easy → identity → pain → blocker → aspiration.** Open with
  something anyone can answer in two seconds; put the most revealing question
  after momentum exists (questions 3–4).
- **Answers are a pain ladder**, ordered from "fine" to "stuck". Including
  the bottom rung ("Completely blocked", "Honestly, I don't know if anyone
  sees it") gives permission to admit the problem. Honest answers are the
  point.
- **Every answer is label + sub-label.** The label is the claim, the
  sub-label is what it means in practice. The sub-label is where the
  respondent recognizes themselves.
- **Every question has a "why we ask" subtitle.** One line. It turns
  intrusion into service.
- **First question doubles as the fence.** Out-of-fit respondents should be
  identifiable at step 1 or 2, so you can exit them with dignity instead of
  wasting their time.
- **3–4 options per question.** 2 is a yes/no (fine occasionally), 5+ is a
  menu nobody reads.
- **No email, no name, no phone until the end.** Ask for contact after value
  has been felt.

## 3. The mirror loop (what makes it "magic")

Two mechanics, both content-driven:

1. **Reactive line per answer** (not per step). After a selection, a tinted
   strip under the options reacts to *that* answer: validation for strong
   answers, normalization for painful ones ("This is the most common pattern
   I see — and the most fixable."). Never sarcastic, never alarmist. Write
   one for every option; a missing reaction feels broken.
2. **One just-in-time education block.** On the single question where the
   respondent's answer reveals the core problem, show a two-panel
   **The problem** → **The solution** explainer. It teaches a mechanism and
   positions the offer in the same breath — a pitch that reads as help. Use
   it **once**. Twice is a sales page.

No unsourced statistics in either ("98% of companies…"). They undermine the
"we see you" tone and are easy to fact-check.

## 4. Visual and interaction contract

Full contract and tokens: [references/ui-contract.md](references/ui-contract.md).

- Single centered card, `max-width ~36rem`, generous padding, soft shadow.
- Thin progress bar pinned to the card top + a quiet "Step N of M" label
  below the card.
- **One accent color**, used for exactly three things: progress fill,
  selected state, primary CTA. Everything else grayscale. Use the product's
  existing accent, not the reference's.
- Whole option row is the click target. Selected = accent border + accent
  tint + filled radio dot.
- Layout follows label length: long labels → one column list; short labels
  → 2×2 grid.
- Primary CTA disabled until an answer is chosen. **Back on every step**, no
  skip.
- Accessible: options are a `radiogroup` with `radio`s, arrow-key
  navigation, visible focus, focus moves to the new question heading on step
  change, `prefers-reduced-motion` respected.

## 5. Scoring, routing and endings

Details, data model and event schema: [references/routing-and-data.md](references/routing-and-data.md).

- Each option may add points on one or more named dimensions (`fit`,
  `urgency`, …) and may force a route (`exit`). Keep the arithmetic trivially
  explainable.
- Route rules are evaluated in order: forced route first, then score
  thresholds, then a default. **Every route must be reachable** — the bundled
  validator proves it.
- **Design at least three endings**, all of them honest:
  - **Fit** → the main CTA (book the call, start the trial, apply).
  - **Early but real** → nurture (send the guide, join the newsletter).
  - **Not a fit** → say so kindly, with one genuinely useful pointer. This
    ending is a feature: it protects the business's calendar and earns
    trust.
- The ending screen should **read back** the respondent's profile in one or
  two sentences ("You're delivering above your title, and the gap is the
  story, not the skill."). The read-back is the deliverable that makes the
  whole thing feel magic.

### Gating by business type

| Business | Gate | Length | Main ending |
|---|---|---|---|
| High-ticket service / program | Questionnaire before booking (or beside it, if volume is low) | 5 questions + 1 optional text | Book a call, pre-diagnosed |
| Self-serve SaaS | Right after signup, skippable after Q1 | 3–5 questions | Personalized first screen / plan |
| Lead magnet | Questionnaire *is* the magnet | 5–8 questions | Read-back free, full report behind email |

Never put a payment gate or a credit meter inside the questionnaire of a
high-ticket offer — micro-charges anchor the buyer to the wrong price scale.

## 6. Data and persistence

- Persist answers **per step**, keyed by an anonymous session id. A drop-off
  at step 3 is still a signal (and still a lead if contact was captured
  earlier for some reason).
- Store `question_id → option_id`, never the display text; the copy will
  change.
- Emit one analytics event per step view and per answer, plus completion and
  route. Funnel drop-off per step is the main tuning signal.
- Downstream: the answers should pre-fill or replace the free-text "tell us
  about yourself" field of the booking/intake form, so the human reviewer
  triages a structured profile.

## 7. Build procedure

1. Write the questionnaire as config (format: [examples/questionnaire.example.json](examples/questionnaire.example.json)).
   Content first; no UI code until the content passes review.
2. Validate it:

   ```bash
   python scripts/validate_questionnaire.py path/to/questionnaire.json
   ```

   It checks structure, the per-option reaction lines, the "no contact data
   before the last step" rule, a single education block, and that **every
   route is reachable** by some combination of answers.
3. Preview it with the dependency-free demo: copy
   [examples/wizard.html](examples/wizard.html), paste the config into its
   `<script type="application/json" id="questionnaire">` block, open it in a
   browser. Review the content *in the UI* with the user — reactions read
   differently on screen.
4. Port to the real stack. The config stays the source of truth; the
   component reads it. Map the contract tokens to the existing design system.
5. Ship behind a feature flag. Measure step drop-off and route split for a
   week before tuning questions.

## 8. Tests

- One E2E test **per route**: drive the answers that reach it, assert the
  ending screen and the persisted payload.
- Back navigation preserves earlier answers.
- CTA disabled with no selection; keyboard-only completion works.
- Reload mid-way restores the current step (if persistence is client-side).
- Contact capture appears only at the end.

## 9. Anti-patterns (refuse or flag)

- Copying a reference's questions verbatim.
- A questionnaire whose every path ends in the same CTA (it qualifies
  nobody).
- Email or phone at step 1.
- Unsourced scare statistics.
- More than one education block.
- Hard walls that make paying customers feel locked out — prefer nudges.
- Free text as the first question.
- Shipping without knowing which decision it drives.

## Deliverables checklist

- [ ] Discovery answers written (decision, fit / not-fit, core problem, blockers, volume vs. quality, data destination)
- [ ] Reference analysis split into *mechanics to reuse* vs. *content to redesign*
- [ ] Questionnaire config with reactions for every option and one education block
- [ ] Validator passes (all routes reachable)
- [ ] Content reviewed in the demo with the user
- [ ] Endings: fit / early / not-a-fit, each with a read-back
- [ ] Persistence per step, analytics events, downstream pre-fill
- [ ] E2E test per route, accessibility checks
