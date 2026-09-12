# Interview mode — creating a new character from scratch

Triggers: "create a new character", "I want to define an avatar", "/consistent-visual-generation new <name>",
"interview me about the character", or any character request that does not yet have a Character Bible.

Rules of the mode:
- **One round at a time**, with AskUserQuestion (2 to 4 questions per round, options + "Other").
  Never dump all 6 rounds at once. Never invent an answer: if the user does not know, mark it
  `"to_be_defined"` and move on.
- **References first.** Before round 1, ask for images (local path, folder, Drive link, or "I have
  none"). If images come in: open each one (Read), describe in 3 lines what you see in terms of
  identity and style, and use that to pre-fill the options in the rounds. A reference is a source of
  composition and style; identity only becomes canonical after the user confirms it in the
  interview.
- **Always separate three things**: identity (what never changes), render style (the finish), and
  allowed variations (outfit, scene, makeup, mood).
- At the end, generate the files in the "Outputs" section and ask whether to generate the character
  sheet now.

## Round 0 — context

1. Character name and what it is for (brand mascot, personal avatar, content character, assistant
   with a face).
2. Where it lives: destination repo/folder and Drive folder (or "create the standard structure").
3. References: "send me images or links; or say 'I have none'". If it is an avatar of the user
   themselves, ask for 2 to 3 photos (frontal, 3/4, full body) and let them know the photos will only
   be used as an identity reference, never published.

## Round 1 — fixed identity (identity locks)

- Apparent age and gender. Species/type if not human.
- Hair: color (with negations: "vivid copper, NOT auburn"), length, default hairstyle, allowed
  variants.
- Eyes: color and shape. Skin: tone and undertone. Freckles/marks: yes or no, where.
- Face: shape, nose, mouth, brows, one or two "signatures" (mole, scar, gap in the teeth).

## Round 2 — body and marks

- Relative height and proportion (heads tall), body type, with an explicit limit on what counts as
  exaggeration.
- Tattoos, piercings, scars, luminous marks: **each with side and exact spot** (inner right wrist,
  left forearm). Rule: laterality is always described from the viewer's point of view in the prompt
  ("her RIGHT hand, on the VIEWER'S LEFT").
- For each mark, capture three things beyond the location, or it will come out wrong:
  - **Stroke shape**: "a single arc, one pen stroke, ends in a point". Saying where is not enough;
    without the shape the generator branches it, forks it, mirrors it on the other side.
  - **Intensity by comparison with something real**: "like a real vein, only with the hue changed",
    "like a tattoo healed for years". An abstract adjective ("subtle", "discreet") does not converge,
    because the generator has no ruler.
  - **Does it emit light or not?** If it does not, **never use the word "glow"** to describe it: it
    becomes literal light. Use "tint", "reads as", "the hue is wrong".
- If the character wears clothes, ask whether a **non-anatomical mark** fits: embroidered monogram,
  pin, embroidery on the collar. It reappears without drift, while a skin mark usually needs several
  calibrations.
- Signature accessories (glasses, earring, necklace, watch) and which ones are mandatory in every
  image.

## Round 3 — render style

- Show 4 options with a short description and ask for 1: (a) polished 2D digital painting,
  semi-realistic; (b) anime/editorial; (c) stylized 3D, Pixar-like; (d) photorealistic. If there is
  a style reference, describe what it is and suggest it.
- Palette: 3 to 5 dominant colors, temperature (warm/cool), saturation (high/medium/low).
- Default lighting (golden hour, studio light, diffuse) and background detail level (subordinate,
  medium, rich set).
- What must NOT happen (e.g. never photorealistic, never flat vector, never black outlines).

## Round 4 — wardrobe and world

- Style direction (smart-casual, executive, sporty, fantasy) and clothing palette.
- 3 to 6 approved looks, one per line. **Vary by layer, not by color**: blazer, no blazer, knitwear,
  overcoat. A look that changes color in every scene destroys identity recognition.
- For each look, note what gets **covered**: a monogram on the chest disappears under knitwear, a
  mark on the neck disappears under a high collar. Without this the prompt asks for the impossible
  and the generator invents.
- Default environment (home office, city, studio, abstract) and recurring elements (plant, painting,
  window). Things forbidden in the scene (animal, logo, text).

## Round 4b — personality and visual translation

Do not skip it. Without it the generator slips into superhero poses, theatrical gestures and
advertising smiles, and you will fight that in every generation.

- In one sentence: what this character is (executive and dry, warm and playful, technical and
  patient).
- **How that becomes an image.** For each trait, write the concrete visual equivalent:
  posture ("shoulders back without tension"), gesture ("measured and short, never theatrical"),
  smile ("always closed and one-sided" or "open and easy"), gaze ("direct and sustained").
- What the character would **never** do in an image (laugh with an open mouth, pose with hands on
  hips, stare down from above). That becomes a line in the `negative_prompt`.

## Round 5 — expression and visual personality

- 3 default expressions (e.g. confident smile, one-sided smile, focus).
- Makeup/face finish: baseline and 2 to 4 variants.
- Signature poses (2 to 4) and the framings the library will have (circular avatar, half body, full
  body).

## Round 6 — confirmation

Show a summary table (identity | style | variations | prohibitions) and ask "confirm, or what
changes?". Only then generate the files.

## Outputs (generate all of them)

Everything inside `characters/<name>/` (see the full tree in section 2 of SKILL.md):

```
identity/<name>_character_bible_v1.json      # from templates/character_bible_template.json
prompts/canonical/_canonical-identity-block.txt   # English, locks + marks with laterality AND shape
prompts/canonical/_style-block.txt            # English, the STYLE TO MATCH paragraph (short!) + AVOID
prompts/canonical/sheet-<name>.txt            # character sheet prompt (front + 3/4 + body, name written)
reference-library/{canonical,sheets,materials}/   # empty folders, already following the convention
reference-library/<name>_reference_library.json   # index; image_file points to the current version
docs/canonical-checklist.md                   # items derived from the answers
docs/file-convention.md                       # the naming convention, written for the project
docs/canonical-versions-history.md            # empty, with the convention
```

The Bible v1 has to come out of the interview already with:
- `personality` with the visual translation of each trait (round 4b), not just adjectives;
- each mark with **location, stroke shape and intensity by comparison** (round 2);
- the wardrobe saying what each look **covers**;
- `negative_prompt` fed by the "what the character would never do" from rounds 3, 4 and 4b.

Then: "Generate the character sheet in ChatGPT now?" If yes, follow the cycle in SKILL.md (fresh
chat, style reference attached if there is one, download, checklist, upload to Drive). The approved
sheet becomes Image 1 for the following generations, remembering that a style-ref only works with a
different composition.

**Commit the Bible before generating the first image.** It is the point you will want to return to.
