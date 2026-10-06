---
name: slides-html
description: >-
  Build, import and restyle HTML slide decks: a single self-contained file on
  a fixed 1920×1080 stage that scales to any screen, zero dependencies, driven
  by reusable design-system files (palette with accent discipline, type scale
  in stage pixels, components, slide-type recipes). Use whenever the user
  wants a presentation, deck, slides, a talk outline turned into slides, a
  PPTX/PDF deck converted to HTML, a deck restyled ("make it look like my
  other deck", "in the nightsky style"), a design system extracted from an
  existing deck (colors, fonts, slide types) so future decks look the same, a
  PDF or per-slide images exported from an HTML deck, or an HTML deck reviewed
  or fixed (overflow, layout, fonts). Ships a working deck skeleton, the
  nightsky-java design system and a PDF exporter — do not rewrite these from
  scratch. Also triggers on the equivalent phrases in other languages.
---

# slides-html

Decks are single HTML files with inline CSS/JS, authored on a fixed 1920×1080
stage that scales as a whole to any screen (letterbox, never reflow). Assets
(images, local fonts) sit in a sibling `assets/` folder. Decks live under one
root the user chooses (`DECKS_ROOT`, for example `~/slides-html`), one folder
per deck: `$DECKS_ROOT/decks/<slug>/index.html`.

Design comes from a **design system** file (`references/design-systems/*.md`):
palette with accent discipline, type scale in stage pixels, card/canvas CSS,
components, slide-type recipes and do/don'ts. `nightsky-java` is the bundled
house style for code-heavy tech talks (extracted from a real 47-card
conference deck). Read each system's frontmatter to choose; read the whole
file before generating.

Method and base files come from `zarazhangrui/frontend-slides` (MIT, see
`references/LICENSE-frontend-slides.txt`), adapted: no hosting step, design
systems instead of ad-hoc previews when a house style exists, metrics-first
browser verification.

## 0. Detect the mode

| The user wants…                                          | Mode                | Go to |
| -------------------------------------------------------- | ------------------- | ----- |
| a new deck from a topic, notes or a markdown outline     | **Generate**        | §1    |
| a PPTX or PDF converted                                  | **Import file**     | §4    |
| "make it look like deck X" / "extract the style"         | **Design system**   | §5    |
| changes to an existing HTML deck                         | **Enhance**         | §6    |
| a PDF / images of a deck                                 | **Export**          | §7    |

## 1. Generate: brief

Ask everything at once (one message, or the structured-question UI if there is
one): purpose and audience, language of the slides, length, whether content
exists (outline file, notes, rough bullets, topic only), density (speaker-led:
one idea per slide, 1–3 bullets; reading-first: self-contained slides, 4–8
bullets), and images available (folder path, or none).

If the user already named a design system or said "like my other deck", skip
the style round. Otherwise offer three one-slide previews (§2). Do not ask
about inline editing, sharing or export up front.

When content comes from a document (talk notes, an article, a README), read
it fully and build the slide outline from its headings; confirm the outline
in one message (slide number, title, type from the design system's table)
before writing HTML. Outlines longer than 25 slides get a section structure
with "shout"/section slides between parts.

## 2. Style round (only when no design system is chosen)

Generate three real title slides for this deck into `decks/<slug>/.previews/`
(style-a/b/c.html): one from a design system in `references/design-systems/`,
one safe preset from `references/style-presets.md`, one wildcard designed for
the brief. Never print internal labels ("option A", "preview", template names)
on the slide. Open them in the browser (§8) and ask which one, or "mix".

Design-system slot first: an existing system means consistency across talks,
which is what a speaker with a recurring audience needs more than novelty.

## 3. Generate: build the deck

1. Copy `assets/deck-skeleton.html` to `decks/<slug>/index.html`. Keep every
   block marked `KEEP` (stage CSS, reveal animation, controller). Replace the
   `THEME` block and the `DESIGN SYSTEM` components with the chosen system's
   CSS. Copy the system's background/logo assets into `decks/<slug>/assets/`
   (nightsky-java: `assets/nightsky-bg-navy.png` from this skill → `assets/bg-navy.png`).
2. Write slides in outline order. Each `<section class="slide" data-label="…">`
   is one slide type from the system's table; put content blocks in `.reveal`
   for the staggered entrance. Comment each slide with `<!-- N. TYPE — title -->`.
3. Code on slides is real code: read it from the project or the source notes,
   trim to the lines that carry the point, keep comments that explain the why.
   Highlight tokens with the `pre.code` span classes.
4. Speaker notes go in an HTML comment at the end of each slide
   (`<!-- notes: … -->`), never on the slide.
5. Fit rule: nothing scrolls, nothing overflows the card, nothing overlaps. If
   a code block does not fit at the system's minimum code size, split it into
   two slides with the same title (the reference deck does this six times). If
   a table has more than 8 rows, split or summarize.
6. Verify in the browser (§8): every slide at 1920×1080, then one narrow
   viewport to confirm letterboxing. Check `scrollHeight <= clientHeight` on
   every `.card` and that no two absolutely positioned panels intersect.
7. Write `decks/<slug>/README.md`: talk, date, design system, source content
   path, and how to regenerate. If the decks root keeps an index README, add
   the deck to its table.

Density and slide count: speaker-led talks run about one slide per minute of
talk, with code slides counting double because they need narration; reading
decks can be a third of that.

## 4. Import PPTX / PDF

`python scripts/extract-pptx.py deck.pptx out/` (needs `python-pptx`) gives
per-slide text, images and notes. For PDF, render pages with `pymupdf` and
read the text layer. Present the extracted outline, pick a design system (§2),
then generate (§3) preserving order, images and notes.

## 5. Design system: extract or author

Read `references/design-systems/README.md`. Extraction is mostly measuring:
theme colors, computed type sizes scaled to 1920, actual column ratios,
components, one reference render per slide type. Save as
`references/design-systems/<slug>.md` in this skill, keep a copy with 12–15
`ref-slide-NN.png` renders under `$DECKS_ROOT/design-systems/<slug>/`, and
list it in the decks-root README.

## 6. Enhance an existing deck

Read the deck fully first. Adding content is the main risk: count what the
slide already holds against the density it was designed for, and split into a
continuation slide instead of shrinking type. After any change, re-verify (§8)
and keep the `KEEP` blocks intact. A deck is a snapshot of the skeleton at the
time it was generated: if the skeleton has since gained a fix (print rule,
hashchange, a new component), port only what the deck needs, and do not
retrofit the controller unless navigation is broken.

A design system can lack a component the content needs (a quote, a third
lane, a closing slide without a QR). Extend it in the same grammar (same
radii, side-line, palette meaning), note the addition in the deck README, and
propose adding it to the system file so the next deck does not reinvent it.

## 7. Export

- PDF: `bash scripts/export-pdf.sh decks/<slug>/index.html [out.pdf] [--compact]`
  (Playwright screenshots each `.slide` at 1920×1080 through a local server;
  first run downloads Chromium). Animations are flattened; say so.
- PNG per slide: same script leaves the screenshots in a temp folder; copy
  them to `decks/<slug>/slides-png/` when the user wants images (carousels,
  thumbnails).
- Print: the skeleton has `@media print` rules, so Ctrl+P → Save as PDF also
  works without Playwright.

## 8. Verifying in the browser

Local files are often blocked in embedded browsers; serve the deck instead
(`python -m http.server 8766 --directory $DECKS_ROOT`, then open
`http://localhost:8766/decks/<slug>/index.html#<n>`).

Which browser: a **Playwright**-driven page (`browser_navigate`, resize to
1920×1080, `browser_evaluate`, `browser_take_screenshot`) is the reliable one
for decks: the page is an active tab, transitions run, screenshots are real.
Embedded preview panes and background browser tabs pause CSS transitions
(`getAnimations()` stuck at `currentTime 0`) and their screenshots time out or
come back blank, which looks like a broken deck when it is not. Keep the
screenshot folder out of version control.

Verification is metrics first, pixels second. In one `browser_evaluate`,
step through every slide (dispatch `keydown` ArrowRight, wait ~1.4s) and
collect: `.card` `scrollHeight` vs `clientHeight`, elements whose rect leaves
the 1920×1080 stage, minimum `.reveal` opacity (must reach 1), slide count.
Then screenshot the cover, the densest code slide, the table slide and the
takeaways, and look at them. Navigating to `#n` on an already open page
switches slides through `hashchange`; on a fresh load the controller reads the
hash.

## Supporting files

| File                                              | Purpose                                                   | Read when                       |
| ------------------------------------------------- | --------------------------------------------------------- | ------------------------------- |
| `assets/deck-skeleton.html`                       | Working deck: stage CSS, controller, reveal, sample components (nightsky-java) | §3 always                       |
| `assets/viewport-base.css`                        | The mandatory stage CSS on its own (already inside the skeleton) | fixing a foreign deck           |
| `assets/nightsky-bg-navy.png`                     | Background image of the nightsky-java system              | §3 with nightsky-java           |
| `references/design-systems/README.md`             | What a design system file contains; how to extract one    | §2, §5                          |
| `references/design-systems/nightsky-java.md`      | House style for code-heavy tech talks                     | §3 with nightsky-java           |
| `references/style-presets.md`                     | 12 safe presets (fonts, palettes, signature elements)     | §2 safe slot                    |
| `references/html-template.md`                     | Architecture notes, inline editing pattern, image pipeline | §3 when adding editing/images  |
| `references/animation-patterns.md`                | Entrance/background/interactive effects by feeling        | §2 wildcard, §3 motion          |
| `scripts/extract-pptx.py`                         | PPTX → JSON + images                                      | §4                              |
| `scripts/export-pdf.sh`                           | Deck → PDF via Playwright                                 | §7                              |
