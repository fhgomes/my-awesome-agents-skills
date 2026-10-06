# Design systems: what they are and how to write one

A design system file is the recipe that lets this skill regenerate a deck that
looks like it belongs next to an existing one. One file per system, in this
folder, named `<slug>.md`. The frontmatter is the selection index: read every
file's frontmatter to shortlist, then read only the chosen file in full.

Reference images (12–15 rendered slides, one per slide type) live in the user's
decks root, not in the skill: `$DECKS_ROOT/design-systems/<slug>/assets/`.
Look at them when the words are ambiguous; they are the ground truth.

## Frontmatter

```yaml
---
name: <slug>
description: one paragraph — the visual thesis in plain words (surfaces, type, accent logic, mood)
scheme: dark | light | mixed
formality: low | medium | high
density: low | medium | high (and whether it is speaker-led or reading-first)
best_for: contexts where it shines
avoid_for: contexts where it fights the message
reference_deck: path to the deck it was extracted from (or "authored")
reference_images: path glob of the rendered slides
---
```

## Sections (keep this order, keep the headings)

1. **Visual thesis** — 4–6 sentences a designer could sketch from. Name the one
   device that makes the system recognizable (the frosted card, the yellow
   poster block, the hairline grid...).
2. **Colors** — a `:root` block with semantic names, then the **accent
   discipline**: which colors are free, which are scarce, and what each scarce
   one means. This rule is what keeps generated decks from turning into
   rainbow dashboards.
3. **Typography** — fonts and weights, then a table of roles with px sizes
   authored for the 1920×1080 stage, line-heights and notes. If the source used
   relative units, convert them (source base px × 1920 / source width).
4. **Spacing and the card/canvas** — margins, paddings, gaps, column ratios
   actually used, and the CSS for the slide container.
5. **Components** — every reusable block with its CSS and when it is used:
   boxes, labels, callouts, code, tables, steps, photos, mascots, QR.
6. **Slide types** — a table: number, name, layout recipe in one line, reference
   image. Add the sequence the source deck used if it is a good talk arc.
7. **Motion** — entrance pattern, easing, what is deliberately absent.
8. **Do / don't** — the eight or so rules that distinguish a faithful deck from
   a generic one.

## Extracting from an existing deck

- **PPTX**: `python scripts/extract-pptx.py deck.pptx out/` gives text, images
  and notes per slide; theme colors and fonts are in `ppt/theme/theme1.xml`
  inside the zip (`a:clrScheme`, `a:fontScheme`); layouts in `ppt/slideLayouts/`.
- **PDF only**: render pages to PNG, then read colors off the images
  (PIL, most common colors per page) and infer type roles from relative sizes.
  Mark such systems `reference_deck: pdf-only` so the next reader knows the px
  values are estimates.
- **HTML deck made by this skill**: the `:root` block and the section comments
  are the system; lift them directly.

Always write the do/don't list from what the source deck actually avoids, not
from general taste: the point of a system is fidelity to one voice.

## Authoring a new system

Start from `references/style-presets.md` (12 safe presets, MIT, from
frontend-slides) or from a wildcard design the user picked in the preview
round. Fill the same eight sections. A system that has not been rendered at
least once is a draft: generate a 6-slide sample, screenshot it, and only then
save it here.
