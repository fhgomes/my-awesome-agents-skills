# slides-html

HTML slide decks as a single self-contained file on a fixed 1920×1080 stage,
generated from reusable **design-system** files so every deck of a speaker
looks like it belongs to the same series.

## Purpose

Conference and meetup speakers end up with decks scattered across tools and
styles. This skill makes the agent produce decks that (a) run anywhere a
browser runs, offline, with no build step; (b) never reflow on a projector or
a phone, because the whole stage scales as one unit; and (c) inherit a named
visual system (palette with accent rules, type scale in stage pixels,
components, slide-type recipes) instead of a fresh "AI look" every time.

## Features

- **Deck skeleton** (`assets/deck-skeleton.html`): stage CSS, keyboard / swipe
  / wheel navigation, `#n` deep links, fullscreen, one-slide-per-page print,
  staggered reveal animation, `prefers-reduced-motion`.
- **Design systems** (`references/design-systems/`): a documented format
  (visual thesis, colors with accent discipline, typography table, card CSS,
  components, slide-type table, motion, do/don't) plus `nightsky-java`, a
  dark frosted-card system for code-heavy Java/AI talks with 30 slide recipes.
- **Style round**: three real title-slide previews (house system, safe preset,
  wildcard) when no system is chosen, in the spirit of
  [frontend-slides](https://github.com/zarazhangrui/frontend-slides).
- **Import**: PPTX via `scripts/extract-pptx.py` (text, images, notes), PDF
  via `pymupdf`.
- **Export**: PDF or per-slide PNGs with `scripts/export-pdf.sh` (Playwright),
  or plain browser print.
- **Verification protocol**: metrics first (card overflow, off-stage
  elements, reveal opacity, slide count via one `browser_evaluate`), then a
  handful of screenshots — and which browsers silently freeze CSS transitions.

## Quick Start

```text
Build a 10-slide speaker-led deck in English, nightsky-java style, from
talk-notes.md. Save it under ~/slides-html/decks/my-talk/.
```

The agent copies the skeleton, confirms the outline (slide number, title,
type), writes the slides with real code from your project, verifies them in a
Playwright-driven browser and writes a deck README.

Serve and present:

```bash
python -m http.server 8766 --directory ~/slides-html
# open http://localhost:8766/decks/my-talk/index.html — arrows, F = fullscreen, P = print
```

Export:

```bash
bash scripts/export-pdf.sh ~/slides-html/decks/my-talk/index.html
```

## Requirements

- Python 3 with `python-pptx` (PPTX import) and `pymupdf` (PDF import/render),
  installed on demand.
- Node + Playwright for `export-pdf.sh` (installed on first run), or any
  browser automation that can resize to 1920×1080 and run JavaScript for
  verification.

## Credits

Stage model, presets, animation notes and the PPTX/PDF scripts are adapted
from [zarazhangrui/frontend-slides](https://github.com/zarazhangrui/frontend-slides)
(MIT, see `references/LICENSE-frontend-slides.txt`).

## See Also

- `references/design-systems/README.md` — how to extract a system from an
  existing deck (PPTX theme XML, PDF renders, HTML `:root`).
- [consistent-visual-generation](../consistent-visual-generation/SKILL.md) —
  for mascots and illustrations that must stay on-model across slides.
