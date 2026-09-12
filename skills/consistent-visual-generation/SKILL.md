---
name: consistent-visual-generation
description: >-
  Procedure for generating CONSISTENT characters, avatars and visual assets with generative AI
  (ChatGPT / GPT Image 2 today; Nano Banana, Midjourney, Flux as alternatives), using a Character
  Bible, canonical references, a checklist and side-by-side comparison. Use WHENEVER the user asks to
  create or maintain a character/avatar/mascot with a stable visual identity ("create an avatar for
  me", "keep the style", "canonical reference", "character sheet", "it came out too photorealistic",
  "it drifted from the reference", "character consistency", "style reference", "generate it in
  ChatGPT and upload it to Drive"), or when a generation drifted in style, color, hair, makeup or
  tattoos. Covers operating ChatGPT through the browser (unsticking the render, downloading,
  uploading to Drive), the folder convention and the version-in-filename convention, what to do when
  the user approves a variant (canon promotion), and the lessons on calibrating subtle marks (stroke
  shape, intensity by comparison, never "glow" for something that does not emit light). The central
  lesson: describing style in a long text block makes ChatGPT refuse the request as an "edit", so
  style travels as a reference IMAGE, and that only works when the requested composition differs
  from the attached image. Also triggers on the equivalent phrases in other languages.
---

# Consistent visual generation

This skill is the portable version of the method: it works for any character, in any repository.

## 0. Two modes

- **New character** (no Character Bible yet): enter **interview mode**, described in `interview.md`
  (same folder as this skill). Six short rounds of questions with AskUserQuestion, references read
  before round 1, and at the end the files generated from `templates/character_bible_template.json`.
  Only generate images after that.
- **Existing character** (already has a Bible + canonical block + approved reference): go straight
  to the cycle in section 5 using the recipe in section 3.

How the user triggers it: "create a new character called X", "I want to define my brand's avatar",
"interview me to define the character's style", or `/consistent-visual-generation new X`. With
references: "here are the references: <paths or links>". Without references: "I have no reference,
let's define it from scratch".

## 1. Mental model (what the Sept 2026 research and the tests proved)

1. **Image carries identity and style; text carries the scene.** GPT Image 2 is an LLM-based model
   that pattern-matches the description. The more identity text, the more it drifts. A character
   sheet (front + 3/4 view, name written on it) plus a short scene prompt is the 2026 industry
   standard.
2. **Photographic vocabulary votes for photo.** "golden hour", "window light", "depth-blurred",
   "believable anatomy and fabric materials", "natural freckles", "AVOID porcelain skin" push toward
   photorealism even with "illustration, NOT a photograph" in the prompt. Negation works as an
   instruction, but it is one vote against thirty.
3. **A long style block in text makes ChatGPT refuse** ("the image tool classified this as an
   edit"). Tested 4 times in fresh chats, with a control and bisection. Imperative instructions about
   parts of the image ("paint the skin", "build the hair", "keep the eyes crisp") read as
   "retouching". **Solution: attach an approved image as a style reference** and open the prompt
   with "Image 1 is attached ONLY as a rendering-style reference ... Create a brand new illustration
   from the written description below". With an image, the router goes to edit mode on purpose.
4. **JSON does not improve the model**; it improves us (one single place to edit). The OpenAI
   cookbook is neutral on format.
5. **Fresh chat for every real test.** A used chat is contaminated and gives false positives.
6. **Fix the prompt, do not converse.** If an element is missing (tattoo, glasses), the cause is in
   the prompt or in a pose that hides that body part. Adjust and run in a fresh chat.
7. **A style image only works with a DIFFERENT composition.** Attaching a sheet and asking for the
   same sheet makes the model treat it as an edit and return the same image with the same defects,
   even with the "ONLY as a rendering-style reference" header. A style-ref carries the finish from
   one scene to another, never to redo the same scene. (Observed while regenerating a character sheet
   with a style reference.)
8. **Correct laterality does not guarantee SHAPE.** Saying "only on his left temple" got the side
   right, but the line kept forking until the prompt described the drawing: "a single arc, one pen
   stroke, ends in a point, never Y nor V, no second segment". Describe the stroke, not just where.
9. **For a subtle mark, anchor it to something real and swap ONE attribute.** Abstract intensity
   ("subtle", "low contrast", "clearly visible") does not converge, because the generator has no
   ruler. "Like a real vein, only with the hue changed" hands it the ruler. It took three calibration
   rounds on one character's vein-like mark to get there.
10. **Never use "glow" for something that should not emit light.** The word becomes literal light,
    especially where the surface is well lit and facing the camera. Use "tint", "reads as", "the hue
    is wrong".
11. **A prompt with contradictory instructions makes the model invent a third thing.** Asking for
    "diffuse under the skin" and "very low contrast" at the same time produced a dark line drawn on
    top, the opposite of both. Before blaming the generator, reread the prompt looking for a
    contradiction.
12. **Unusual iris color without turning into robot eyes:** demand the human structure of the iris
    (radial fibers, darker limbal ring, black pupil, catchlight) and explicitly forbid a flat,
    self-lit iris. Describing only the color makes the model paint a uniform disc, which reads as a
    contact lens.
13. **The Character Bible needs a PERSONALITY block with a visual translation.** Without it the
    generator slips into superhero poses, theatrical gestures and advertising smiles. "Executive and
    dry" is not enough: write what that becomes in the image ("measured, short gesture", "always a
    closed, one-sided smile", "shoulders back without tension").
14. **A non-anatomical identity mark is more stable than a mark on the body.** An embroidered
    monogram on the clothing reappeared in every generation without drift, while skin marks needed
    three calibrations. If the character wears clothes, consider a monogram before inventing a scar.

## 2. Minimum structure per character

A character repository holds **one folder per character**, with the shared method at the root:

```
docs/                                  # method that applies to ANY character (pipeline, procedure,
                                       # generators, lessons). Do not mix with character-specific.
characters/<name>/
  identity/<name>_character_bible_vN.json        # rules everything; an image is not a source of identity
  prompts/canonical/_canonical-identity-block.txt   # injected into every prompt (marks with laterality
                                                    # from the viewer's point of view)
  prompts/canonical/_style-block.txt              # short STYLE TO MATCH paragraph + AVOID
  prompts/canonical/ref_NNN-<description>.txt     # one prompt per reference
  prompts/canonical/archived-variants/            # prompts from discarded lines
  reference-library/
    canonical/                         # the approved ones
      history/                         # previous versions, never deleted
    sheets/                            # character sheets
      history/
    materials/                         # comparisons, detail crops, contact sheets
    variants/<line>/                   # discarded lines, with their OWN PREFIX in the filename
    <name>_reference_library.json      # index: points to which file is the current version
  docs/canonical-checklist.md          # ~30 items
  docs/canonical-versions-history.md   # lineage: version -> prompt -> result -> why
  docs/file-convention.md              # the convention below, written for the project
  docs/drive-assets.md                 # Drive links, per reference and per version
```

### Naming convention (applies in the repo and in Drive)

```
<type>_<id>_v<N>[_<description>].png
```

- `ref_001_v3.png`, `sheet_<name>_v5_blue-eyes.png`, `comp_<name>_v4-v5.jpg`
- `v<N>` is the version that generated **that image**, not the Character Bible's version.
- **No canonical file without a version in its name.** Without it there is no way to know which
  prompt generated it.
- The pointer to "which one is current" lives in the `image_file` field of the reference library,
  **not in the filename**. That way nothing needs renaming when a new version arrives, and nothing
  gets overwritten.
- Discarded variants carry their own prefix (`synthetic_ref_001_v1.png`). Without it they collide
  with the canonical ones: two folders with `ref_001.png` is a trap for any script that lists by name.

**Never delete a previous version**: move it to `history/` at the same moment you promote the new one.

### When promoting an image, do all six

1. It passed the checklist. 2. The filename carries the version. 3. The previous one went to
`history/`. 4. `reference_library.json` points to the new file. 5. `canonical-versions-history.md`
got the line with what changed and why. 6. It was uploaded to Drive and the link went into
`drive-assets.md`.

## 3. The prompt recipe that works (ChatGPT, Sept 2026)

```
Image 1 is attached ONLY as a rendering-style reference: match its visual medium, finish, color
treatment and level of stylization. Do not copy its composition, pose, hands, or scene layout; do
not reuse it as a base image. Create a brand new illustration from the written description below.

STYLE TO MATCH FROM IMAGE 1: <one paragraph: medium, skin, hair, makeup, palette, background>

Create a <format> character portrait.

COMPOSITION / CHARACTER / POSE / EXPRESSION / HAIR / GLASSES / WARDROBE / MAKEUP / BACKGROUND
TATTOOS (exact laterality, "her RIGHT hand, on the VIEWER'S LEFT")
IDENTITY LOCKS (hair, eyes, skin, face, age, body, accessories; color by negation:
  "vivid copper, NOT dark auburn, NOT burgundy")
AVOID: <short list, no "porcelain skin", no repeating photograph/DSLR/pores>
```

Do not use: a long RENDERING STYLE block in text, "depth-blurred", "practical lights", "canonical",
"approved variation", post-production verbs (grade, treatment, finish, sharpness, color cast).
Always include a HAIR block (without it the hair comes out loose).

## 4. Operating ChatGPT through the browser (claude-in-chrome)

- **Chat** tab, not Work (the Work field does not accept the insertion).
- Insert text: `#prompt-textarea` focused + `document.execCommand("insertText", false, text)`.
- Attach: `find` "file upload input" and `file_upload` with a local path.
- Send: click in the DOM, `[...document.querySelectorAll('button')].find(b=>/send prompt/i.test(b.getAttribute('aria-label')||'')).click()`.
  Proof of sending: URL becomes `/c/<id>`, the field clears, the Stop button appears.
- Wait 1 to 3 min. Poll with `await new Promise(r=>setTimeout(r,25000))` (never more than 30 s per
  call; CDP times out at 45 s).
- **Black frame = image ready but not rendered.** Click the frame (or the card in the Outputs
  panel). If that does not resolve it: F5 on the chat URL. Degraded tab (screenshot "0 width" or
  timeout): new tab and `tabs_context_mcp({createIfEmpty:true})`.
- "Something went wrong / Retry" 95% of the time: F5 first; the image usually already exists.
- Download: `fetch(img.src)` → blob → `<a download>`; take the image with the LARGEST vertical
  position (DOM order is not conversation order). Move it out of `~/Downloads`.
- **`naturalWidth === 0` does not mean the image does not exist.** It can be in the DOM with a valid
  `src` and not decoded yet. Filter by `getBoundingClientRect().width > 200` instead of
  `naturalWidth`, and `fetch(img.src)` downloads normally even with the black frame on screen. This
  avoids waiting for a render for nothing. Validate the blob with `if (bl.size < 50000) throw` so you
  do not save a placeholder.
- Upload to Drive at full resolution: open the folder, click "New", fire
  pointerdown/mousedown/pointerup/mouseup/click on the `[role=menuitem]` "File upload", make the
  `input[type=file]` visible, `find` + `file_upload`. Move/rename existing files: Drive MCP
  (`update_file` with `parentId`/`title`), far more reliable than dragging in the UI.
- **Drive's "New" menu toggles on every click** and closes if the previous click opened it. If
  `[role=menuitem]` comes back empty, click once on the folder's empty area, then on "New". The
  shortcut `alt+c` followed by `u` also opens the picker, but fails if focus is outside the list.
- The `input[type=file]` is **consumed on every upload**: for a second batch, reopen the menu.
  Uploads of up to 4 files at a time (~7 MB) went through without issue.
- Always read coordinates from the DOM (`getBoundingClientRect`); never reuse them from another
  session.
- Parallelism: **3 tabs is the safe ceiling**. Above that ChatGPT returns "Too many requests" and the
  batch breaks midway, leaving references without a pair. **Do not close tabs in the middle of a
  batch**: closing one tears down the automation's tab group and the others become orphans. If the
  group is lost, `tabs_context_mcp({createIfEmpty:true})` recreates it.
- A generation can genuinely fail ("Something went wrong while generating your image"), which is
  different from the black frame. Check with a screenshot before insisting on F5.
- Validated on 6 of 6 references of one character: the style-image recipe matches the approved
  finish in all of them, with the right tattoos and hairstyle.

## 5. Cycle of one reference

1. Library entry → prompt (`ref_NNN-*.txt`) with the canonical block and HAIR.
2. Fresh chat, style image attached, prompt inserted, sent.
3. Download, build a side-by-side (old | previous version | new) with PIL, measure colorfulness
   (Hasler & Süsstrunk) and fine detail (FIND_EDGES) if the doubt is about style/color.
4. Run the checklist. Missing element → fix the prompt → fresh chat.
5. Approved: upload to Drive, move the previous one to `history/_vK`, record it in
   `canonical-versions-history.md` and in the lessons table.

## 6. When the user approves a variant (canon promotion)

**An expensive mistake, observed in practice:** the user approved a variant ("approved"), and I kept
generating eight references from the **old** Character Bible. Eight images thrown away.

An "approved" on an image that diverges from the Bible **is not** approval of that image alone: it
is a change of canon. Before generating anything after an "approved", stop and do this:

1. **Ask yourself: does this image match the current `identity_lock`?** If it diverges in any lock
   (ethnicity, skin, hair, eyes, material), the canon has changed. There is no "approved but not
   canonical" when the user is going to ask for more images of it.
2. **Promote before generating.** Write the new Bible (`_vN+1`), with `supersedes` pointing to the
   previous one and `source` saying which image became canon and why.
3. **Archive the previous one**, do not delete it: `identity/archived-variants/`, prompts in
   `prompts/canonical/archived-variants/`, images in `reference-library/variants/<line>/` with their
   own prefix.
4. **Rewrite the canonical identity block** from the new Bible. It is what goes into the prompts; if
   it stays stale, every generation comes out wrong and looks like a generator problem.
5. **Only then** generate. And commit before generating: the canon promotion is the point you will
   want to be able to return to.

Warning sign in the conversation: if the user says "approved" and your next action is to generate an
image without having touched the Bible, you are probably about to generate from the wrong canon.
