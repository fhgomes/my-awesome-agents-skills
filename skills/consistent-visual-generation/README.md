# consistent-visual-generation

Generate characters, avatars and mascots that stay visually consistent across AI image generations — Character Bible, canonical references, checklist and side-by-side comparison.

## Purpose

Keep a character looking like itself across dozens of generations (ChatGPT / GPT Image 2 today; Nano Banana, Midjourney, Flux as alternatives). The lever that actually matters: style and identity travel as a reference IMAGE with a different composition, while text carries only the scene — a long style block in text makes ChatGPT refuse the request as an "edit".

## Features

- **Interview mode** — `interview.md`: 6 short rounds to build a Character Bible from scratch, references read before round 1
- **Character Bible template** — `templates/character_bible_template.json`: identity locks, personality with visual translation, marks with stroke shape and intensity by comparison, wardrobe that records what each look covers
- **Prompt recipe** — the style-reference header that avoids the "classified as an edit" refusal, plus the photographic vocabulary that quietly pushes toward photorealism
- **Folder and version convention** — version in every canonical filename, `history/` never deleted, current-version pointer in the library index
- **Canon promotion** — what to do when the user approves a variant that diverges from the Bible (promote first, generate later)
- **Browser ops** — operating ChatGPT via claude-in-chrome: unsticking black frames, downloading at full size, uploading to Drive, safe parallelism

## Quick Start

```
/consistent-visual-generation new <name>     # interview mode for a new character
```

Existing character: attach the approved reference as Image 1, open the prompt with the style-reference header from section 3 of SKILL.md, and run every real test in a fresh chat.

## See Also

- [SKILL.md](SKILL.md) — Full skill (mental model, folder structure, prompt recipe, browser ops, canon promotion)
- [interview.md](interview.md) — Interview rounds for a new character
- [templates/character_bible_template.json](templates/character_bible_template.json) — Character Bible template
