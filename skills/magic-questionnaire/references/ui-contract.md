# UI contract — tokens, components, accessibility

Load this when implementing or reviewing the questionnaire UI. Values are
Tailwind-flavored for convenience; map them to the product's design system.
`accent` is the product's existing brand accent.

## Layout

| Element | Spec |
|---|---|
| Page | Very light tinted background, card vertically centered on desktop, top-aligned on mobile, 16px side gutter |
| Card | `max-w-xl`, `rounded-3xl`, `shadow-lg`, `border border-gray-100`, `p-8 sm:p-10`, white |
| Progress | 4–6px bar flush with the card top; fill = `accent`; width = `step / total`; `transition: width 500ms ease-out` |
| Step label | "Step N of M", small, gray, **below** the card |
| Icon (optional) | One emoji or illustration above the title, ~40px |
| Title | `text-2xl sm:text-3xl font-bold`, centered |
| Subtitle ("why we ask") | `text-sm sm:text-base text-gray-500`, centered |

## Option (list layout — long labels)

- Whole row is a `button`/`radio`: `rounded-2xl border-2 px-4 py-4 w-full text-left`.
- Left: `w-10 h-10 rounded-xl` icon tile (`bg-gray-100`) with an emoji.
- Middle: label (`font-semibold`) over sub-label (`text-sm text-gray-500`).
- Right (selected only): 24px ring with a 12px filled dot, both `accent`.
- Idle: `border-gray-200 bg-white`, hover `border-gray-300 bg-gray-50`.
- Selected: `border-accent bg-accent/10`, label in `accent`, icon tile `bg-accent` with white glyph.

## Option (grid layout — short labels)

- `grid grid-cols-2 gap-3`; each cell centered: emoji, label, sub-label.
- Same idle/selected states. Collapse to one column below ~360px.

## Reactive strip

- Appears under the options after a selection; replaces its text on change.
- `rounded-xl px-4 py-3 text-sm text-center`, `bg-accent/10 text-accent`.
- `aria-live="polite"` so screen readers announce it.
- Fade/slide in ≤ 200ms; none under `prefers-reduced-motion`.

## Education block

- Two stacked panels under the options, shown only after the triggering answer.
- **The problem**: warm-red tint (`bg-red-50 border-red-100 text-red-700`), warning glyph.
- **The solution**: green tint (`bg-green-50 border-green-100 text-green-700`), sparkle glyph.
- Bold panel title, 2–3 sentences of body.

## Navigation

- Row at the bottom: `Back` (outlined, ~1/3 width) + primary CTA (filled `accent`, ~2/3 width).
- Step 1 has no Back; CTA is full width.
- CTA: `rounded-xl py-3.5 font-semibold`, `disabled:opacity-40 disabled:cursor-not-allowed`, disabled until an answer exists.
- CTA label: "Continue →" on question steps, a specific verb on the last ("See my result →").

## Final steps

- **Contact capture** (last step before the result): one or two fields only
  (email; name optional), with a sentence saying exactly what will be sent.
- **Result screen**: profile read-back (1–2 sentences), route title, route body,
  one primary CTA, optional secondary link. No progress bar.

## Accessibility

- Options container: `role="radiogroup"` with `aria-labelledby` = question title.
- Each option: `role="radio"`, `aria-checked`, roving `tabindex` (only the
  selected or first option is tabbable).
- Arrow Up/Down/Left/Right move selection; Space/Enter select; Enter on a
  selected option advances.
- On step change, move focus to the new question title (`tabindex="-1"`).
- Contrast ≥ 4.5:1 for sub-labels — light gray on white often fails; check it.
- Emoji are decorative: `aria-hidden="true"`.
- Respect `prefers-reduced-motion` for the progress bar and strips.

## Responsive

- No horizontal scroll at 320px.
- Tap targets ≥ 44px tall.
- Grid layouts collapse to one column on very narrow screens.
- Sticky bottom navigation on mobile is acceptable if the card is taller than the viewport.
