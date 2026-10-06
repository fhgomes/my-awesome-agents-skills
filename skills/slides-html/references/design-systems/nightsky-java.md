---
name: nightsky-java
description: Deep-navy "night sky" tech-talk system extracted from a real 47-card conference deck (Java + AI architecture talk, 2026). Frosted dark cards floating over a navy starfield, Roboto 500/400, indigo accent for structure and amber for the one word that matters. Built for code-heavy Java/AI/architecture talks with tables, code blocks, diagrams and a running visual joke (a mascot that peeks into code slides).
scheme: dark
formality: medium
density: medium-high (speaker-led, but self-contained slides)
best_for: conference tech talks and meetups, RAG/AI/Java architecture, anything with real code on screen, mentoring decks
avoid_for: light/print-first handouts, playful pastel brands, decks with no code or data
reference_deck: private (a 2026 conference talk, 47 cards; slide numbers in the type table refer to its order)
reference_images: not bundled — the recipes below are written to be sufficient on their own
---

# Nightsky Java — design system

Read this whole file before generating a deck in this style. It is a recipe, not
content to copy: keep the palette, type, card grammar and slide layouts; replace
every word and image with the user's material.

## 1. Visual thesis

One dark frosted card per slide, floating on a navy starfield. Everything lives
inside the card. Structure is indigo; emphasis is amber; danger is pink. Type is
Roboto because the deck has to read from the back of a conference room and the
hero of the slide is usually a code block or a table, not a headline. Photos and
a mascot (in the source deck, the speaker's two cats) peek into corners of code
slides as the recurring human touch that keeps 40 slides of Java from feeling
like documentation.

## 2. Colors

```css
:root {
  /* surfaces */
  --bg-image: url("assets/bg-navy.png");        /* navy starfield, cover, fixed */
  --bg-fallback: #05061a;
  --card-bg: rgba(0, 0, 24, 0.75);               /* #000018bf */
  --card-border: rgba(230, 230, 230, 0.25);
  --card-blur: blur(20px) saturate(170%);
  --surface: #0d0d25;                            /* code blocks, table bg */
  --surface-muted: #0f163e;
  --box-bg: #182567;                             /* solid boxes, callout note */
  --box-border: #313e80;

  /* text */
  --heading: #ffffff;
  --body: #cfd0d8;
  --body-muted: rgba(207, 208, 216, 0.5);
  --caption: rgba(207, 208, 216, 0.5);

  /* accents */
  --accent: #5a6ed8;          /* indigo: structure, numbers, labels, links, eyebrow */
  --accent-dim: #7387f1;
  --accent-deep: #243799;     /* palette-2: darker box variant */
  --amber: #f59e0b;           /* the ONE emphasized word in a title, formulas, URLs */
  --cyan: #06b6d4;            /* "vector" lane, highlighted table row, positive tag */
  --pink: #f20374;            /* danger, security, "defense-in-depth", warnings */
  --violet: #8b5cf6;          /* secondary emphasis, "hybrid" concepts */
  --slate: #94a3b8;           /* de-emphasized meta text */

  /* code syntax (GitHub dark) */
  --code-fg: #e6edf3; --code-keyword: #ff7b72; --code-title: #d2a8ff;
  --code-builtin: #ffa657; --code-number: #79c0ff; --code-string: #a5d6ff;
  --code-comment: #8b949e; --code-name: #7ee787;

  /* callouts */
  --callout-note-bg: #182567; --callout-note-icon: #8392e2;
  --callout-info-bg: #022349; --callout-info-icon: #8dd4fb;
  --callout-warning-bg: #4b3f02; --callout-warning-icon: #f5f380;
  --callout-caution-bg: #450707; --callout-caution-icon: #ef8784;
  --callout-success-bg: #183a13; --callout-success-icon: #8ce29f;
}
```

Palette for charts / sequences (in order): `#5a6ed8`, `#243799`, `#000024`,
`#000030`, then amber `#f59e0b` and cyan `#06b6d4` as highlight colors.

**Accent discipline.** Indigo is free to use. Amber, cyan, pink and violet are
scarce: at most two of them on a slide, and each has a meaning (see above). A
title gets at most one amber word or phrase ("Calling the LLM is the
<amber>Smallest</amber> Part of the System"). The one sanctioned exception is
the takeaways grid (slide type 25), where each box title takes a different
accent (indigo-dim, cyan, amber, violet) so the four points read as four
distinct things; that slide has no other colored text.

## 3. Typography

Fonts: **Roboto** 500 for headings, 400 for body (Google Fonts or local woff2).
Mono: `ui-monospace, "SF Mono", Menlo, Consolas, monospace`.

Sizes are authored for the 1920×1080 stage (base 26px; the original deck ran
base 15.75px at a 1161px-wide card, scale ×1.65).

| Role            | Size   | Weight | Line-height | Notes                                   |
| --------------- | ------ | ------ | ----------- | --------------------------------------- |
| Cover title     | 78px   | 500    | 1.15        | white, left aligned, 2 lines max        |
| Slide title h1  | 62px   | 500    | 1.25        | white; one amber phrase allowed         |
| h2 / section    | 48px   | 500    | 1.25        |                                         |
| h3 (box title)  | 30px   | 500    | 1.3         | white or accent-colored inside boxes    |
| h4 (label)      | 26px   | 500    | 1.3         | white                                   |
| Body lg         | 32px   | 400    | 1.6         | default paragraph in this deck          |
| Body            | 26px   | 400    | 1.6         | dense slides, table cells               |
| Small / caption | 21px   | 400    | 1.5         | captions, table meta, source lines      |
| Eyebrow / label | 20px   | 400    | 1.2         | UPPERCASE, letter-spacing 0.08em, indigo |
| Code            | 24px   | 400    | 1.5         | mono; 22px when the block is > 14 lines |
| Display formula | 64px   | 500    | 1.1         | amber, centered, mono or Roboto         |

Headings never use letter-spacing tricks; the deck's character comes from the
card and the color rules, not from display type.

## 4. Spacing and the card

```css
.slide { background: var(--bg-fallback) var(--bg-image) center / cover fixed; }
.card {
  position: absolute; inset: 40px;                /* 1840×1000 card on the stage */
  border-radius: 16px;
  background: var(--card-bg);
  border: 1px solid var(--card-border);
  backdrop-filter: var(--card-blur);
  padding: 72px 80px;                             /* 48pt base × padding factor */
  display: flex; flex-direction: column; justify-content: center; gap: 32px;
}
```

- Column gap: 48px. Grid gap between boxes: 24px.
- Block rhythm: 26px between paragraphs (1× base), 40px before a new h3 group.
- A slide is vertically centered inside the card unless it has a table or a code
  block that fills the card, in which case the title sits at the top with 40px
  below it.
- Two-column widths used in the original: 62/38 (title + code tree), 50/50,
  55/45, 67/33 (table + notes), 79/21 and 83/17 (code + peeking cat), 16/84 (cat
  + code). Pick the ratio by what the wide column needs, never split 50/50 by
  default.

## 5. Components

**Solid box** (grid cards, key takeaways)
`background: var(--box-bg); border: 1px solid var(--box-border); border-radius: 12px; padding: 24px 28px;`
h4 in white (or in a semantic accent for takeaways), 1–2 lines of body 26px in
`--body`. Grids of 2×3 or 2×2; a 4-column row for demo scripts.

**Outline box with side line** (comparison lanes, pros/cons, definitions)
`background: var(--surface-muted); border: 1px solid var(--box-border); border-left: 6px solid <lane color>; border-radius: 12px; padding: 24px 28px;`
Lane title in the lane color (cyan for "vector", amber for "lexical"), body in
`--body`, a mono snippet line in the lane color at 21px.

**Numbered step (vertical)**
A 56px indigo square (`--accent`, radius 12px) holding the number in white 26px,
followed by an outline box with the step text. Stack of 2–3 with 24px gap.

**Process step (horizontal circles)**
5 circles, 170px, 3px indigo ring, icon inside in `--accent-dim`, label 26px
below, arrows implied by spacing (no arrow glyphs). Used for the "gates" slide.

**Pill label**
`background: var(--accent); color: #cfd0d8; border-radius: 999px; padding: 6px 14px; font-size: 20px; text-transform: uppercase;`
Semantic variants: cyan `✓ both`, indigo `vector only`, outline muted `demoted`.

**Callout note** (aside)
`background: var(--callout-note-bg); border-radius: 12px; padding: 24px 28px;`
with a 28px icon in `--callout-note-icon` at the left. Body 26px. Use one per
slide at most, for the "what tutorials hide" kind of remark.

**Code block**
`background: var(--surface); border-radius: 12px; padding: 26px 32px; font: 400 24px/1.5 mono; color: var(--code-fg); overflow: hidden;`
Syntax colors from the GitHub-dark tokens above. Never scroll: if it does not fit
at 22px, split the block across two slides with the same title (the original
does exactly this for guardrails).

**Table**
Full-width, `--surface` background, 1px `--box-border` row separators, header row
in `--body` 21px uppercase-ish weight 500, cells 26px. One highlighted row per
table at most: `background: var(--cyan); color: #04202a;` (the "chosen model"
pattern). Right-align numeric columns; bold the value that wins.

**Display formula**
Centered amber text at 64px on its own line above a supporting table.

**Photo with caption**
Photo with `border-radius: 12px`, caption below in 21px `--caption` with an
emoji lead ("🏍️ Moto Rider"). Three photos in a row for the "who I am" beat.

**Peeking cat / mascot**
A cut-out image anchored to a card corner, overlapping the code block edge by
~40px, 260–320px tall, no border. Appears on code-heavy slides only, never on
tables or diagrams. This is the deck's signature; keep it if the talk has a
mascot, drop it (do not replace with clip-art) if it does not.

**QR block**
White rounded square (radius 12px, 20px padding) holding the QR, URL in amber
21px underneath. Big QR 560px for the main link, small 260px for the secondary.

**Quote** (review comment, testimonial, the line that started the talk)
36px white Roboto 400, `border-left: 6px solid var(--accent); padding-left: 28px;`
with a 21px `--caption` cite line below. Same side-line grammar as the lanes;
no quotation-mark glyphs, no italics.

**Three lanes**
The two-lane pattern extends to three (`grid-template-columns: repeat(3, 1fr)`,
gap 24px) when the content is genuinely triadic (three levels of a spec, three
options). Lane colors then: indigo, cyan, violet. Four lanes is a grid, not lanes.

**Grid 2×2**
Same box as the 2×3 grid with `grid-template-columns: 1fr 1fr`. Used for
takeaways and for "four pillars" slides; each box gets an `N ·` prefix in its h4
when order matters.

## 6. Slide types (layout recipes)

The Ref column is the slide number in the source deck (not bundled); it is
there so a reader with access to the deck can look the layout up.

| #  | Type                          | Layout                                                                                      | Ref |
| -- | ----------------------------- | ------------------------------------------------------------------------------------------- | --- |
| 1  | Cover                         | 62/38: title 78px + subtitle 32px + author line with amber handle + event logo; right: code tree in a code block | 01 |
| 2  | Full-bleed image              | Card holds one image edge to edge (screenshots, generated agenda art); no title             | 03 |
| 3  | Concept + callout             | 50/50: h1 + eyebrow + body left; callout note right; optional mini terminal diagram below   | 04 |
| 4  | Single code block             | h1 top, one code block filling the card (prompt anatomy, JSON, service class)               | 09 |
| 5  | Solid-box grid                | h1 with amber word + 2×3 solid boxes (h4 + one line)                                        | 06 |
| 6  | Comparison table              | h1 + table with one cyan highlighted row                                                    | 08 |
| 7  | Code + peeking cat            | 79/21 or 83/17: code block left, mascot cut-out right overlapping the block                 | 10, 32 |
| 8  | Photo triptych                | h1 + 3 columns, each photo + emoji caption + one line                                        | 14 |
| 9  | Two lanes                     | h1 + two outline boxes with side lines in the two lane colors, mono example under each      | 15 |
| 10 | Code + numbered steps         | 56/44: code left, 3 vertical numbered steps right                                           | 16 |
| 11 | Formula + table + note        | h1, amber display formula, 3-column table, callout line below                               | 18 |
| 12 | Labelled mini-tables          | 50/50 two small tables with pill tags; no h1, h4 lane titles in lane colors                 | 19 |
| 13 | Ranked table with tags        | h1 + table where the last column is a pill (`✓ both`, `vector only`, `demoted`)             | 20 |
| 14 | Diagram                       | h1 + one wide diagram image (flow, architecture); dark image with indigo/cyan lines         | 20, 17 |
| 15 | Section with image right      | image-layout right: h1 + one-line subtitle left, illustration bleeding to the right edge    | 21 |
| 16 | Code + arrow bullets          | 50/50: code left; right column of `→ label` + explanation pairs                             | 22 |
| 17 | Code + stacked outline boxes  | 50/50: SQL left; 3 outline boxes right with h4 + line                                       | 23 |
| 18 | Shout section                 | 57/43: uppercase h1 left, big mascot photo right                                            | 24 |
| 19 | Screenshot pair               | h1 + two phone screenshots side by side (memes, chat logs)                                  | 25 |
| 20 | QR slide                      | h1 with amber URL + centered QR block                                                       | 27 |
| 21 | Gates / process circles       | h1 + pink subtitle + 5 icon circles with labels                                             | 29 |
| 22 | Layered table                 | h1 + dense table with pill column (layer / mechanism / where / position)                     | 30 |
| 23 | Pros / cons                   | 50/50: current state boxes left; numbered ✅ Pros / ⚠️ Cons cards right; ✗ list footer       | 37 |
| 24 | Demo beat                     | h1 + one question line; optional 4-column numbered grid of demo prompts                     | 38, 39 |
| 25 | Takeaways over image          | image-layout behind: circuit/starfield art at 35% + 2×2 solid boxes, each h4 in a different accent | 40 |
| 26 | About me                      | image-layout left: portrait photo bleeding left 30%; name 62px, role in amber, stack line in slate, 3 emoji bullets | 41 |
| 27 | Closing QR                    | behind image + amber h1 + big QR / small QR with links                                       | 42 |
| 28 | Closing without QR            | eyebrow ("THANK YOU"), cover-size h1 ("Questions?"), one closing line, then the speaker handle (`@handle`) in amber at display size (64px) and a 21px name/role line | — |
| 29 | Quote slide                   | h1 + quote component + cite line; optional callout with the consequence                     | — |
| 30 | Three lanes                   | h1 + three side-line boxes (indigo / cyan / violet), each with h4 + 2 lines                   | — |

Sequence used by the original (worth reusing for a 40-minute talk): cover →
about-me screenshot → agenda art → concept → prompt anatomy → grid → embedding
art → table → code ×3 → table → code → evidence table → photos → lanes → steps →
diagram → formula → mini-tables → ranked table → code → flow → section → code +
bullets → SQL + boxes → shout → memes ×2 → QR → mascots → gates → layered table
→ code ×6 (before / data / after) → pros-cons → demo ×3 → takeaways → about-me →
closing QR.

## 7. Motion

Subtle. Each slide's blocks fade up 20px over 1s with `cubic-bezier(0.22, 1, 0.36, 1)`
and a 0.15s stagger. No
parallax, no particles: the starfield is a static image and the blur does the
depth. Honor `prefers-reduced-motion`.

## 8. Do / don't

- Do put every slide inside the card; the only exceptions are "behind" and
  "left/right" image layouts where the image bleeds to the card edge.
- Do keep code real and runnable-looking; comments in code explain the "why".
- Do end tables and code blocks before the card padding; split rather than shrink.
- Don't use gradients on text, glows, or neon; the palette is matte.
- Don't introduce a second sans or a display font.
- Don't use amber for decoration; if nothing on the slide deserves emphasis, use none.
- Don't center everything: titles are left-aligned; only formulas, QR blocks and
  the "shout" slide center.
