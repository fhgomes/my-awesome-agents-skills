---
name: mood-avatar-rotation
description: >-
  Turns a character's reference library (the canonical images in Drive + the reference-library
  JSON) into a mood-based avatar rotation for a chat agent (Discord today): downloads the batch,
  finds the face in each image, crops a square whose zoom varies with the framing, generates a
  mood -> entry -> roles manifest (focus, briefing, profile, cozy, playful, event, scolding) and
  wires it all into a switch script that draws by role, avoids repeats and accepts a
  `reference_id`. Use when the user asks "put all 40 photos in the rotation", "the avatar is always
  the same 3", "crop the canonicals for the avatar", "create moods from the library", "the avatar
  cron only has X options", or when a new batch of canonicals arrives and needs reprocessing. Also
  when a crop came out wrong ("it cropped the armpit, not the face", "too much zoom"). Works for
  any character that has a Character Bible + reference library. Also triggers on the equivalent
  phrases in other languages.
---

# Mood avatar rotation

## The problem it solves

The character has 40 canonical images in Drive and a `reference_library.json` with an entry for
each one — but its chat avatar rotates between 3 hand-made crops. The agent "doesn't know" about
the other 37, the cron flips a coin and the user always sees the same face. This skill is the fix:
every canonical becomes a mood, every mood carries roles, and the rotation draws from all of them.

## The design (what lives where)

```
avatars/
  src/<batch>/           original PNGs downloaded from Drive (do not version: ~2 MB each)
  faces_<batch>.json     face box per image, in % of width/height + "source"
  crop/<slug>.png        512x512, one per mood — this is what goes to Discord
  moods.json             manifest: mood -> file, reference_id, entry, roles, framing
  .state.json            last applied (mood + reference_id)
  history.jsonl          one line per switch, with reference_id
reference-library/
  <character>_reference_library.json   the source of the tags/collections that become roles
```

Three pieces, three responsibilities:

| Piece | Does | When it runs |
|---|---|---|
| `scripts/avatar_build.py` | Drive -> src -> faces -> crop -> moods.json | on every new batch, or to redo a crop |
| `scripts/avatar_rotate.py` | picks the mood of the day and applies it on Discord (`PATCH /guilds/{id}/members/@me`) | daily cron (e.g. 07:00); and on demand by the agent |
| the agent's surface (e.g. a `<character>-api avatar ...` wrapper) | lists, filters, forces by mood or `reference_id` | when someone asks in conversation |

The mood **slug** comes from the canonical filename: `ref_043-avatar-coffee-chat_v6.png` ->
`coffee-chat`. That assumes the convention `<ref_id>-<framing>-<description>_v<N>.png`, with framing
one of `avatar`, `half-body`, `full-body` (version in the filename as in
`consistent-visual-generation`). The `reference_id` prefix is a regex (`--ref-pattern`, default
matches `ref_043` and `<name>_ref_043`). With another convention, adjust `slug_of()` and
`framing_of()`.

Both scripts take paths and IDs from flags or environment variables — nothing is hardcoded:

| Setting | Flag | Env var |
|---|---|---|
| avatars directory | `--base` | `AVATAR_BASE` (default `./avatars`) |
| reference library | `--library` | `AVATAR_LIBRARY` |
| reference_id regex | `--ref-pattern` | `AVATAR_REF_PATTERN` |
| Drive access token | — | `GOOGLE_DRIVE_TOKEN` (only with `--folder`) |
| Discord server | `--guild` | `DISCORD_GUILD_ID` |
| bot token | `--token-env NAME` | `DISCORD_BOT_TOKEN` by default; optional dotenv via `--env-file` / `AVATAR_ENV_FILE` |
| calendar event count | `--events-cmd` | `AVATAR_EVENTS_CMD` (a command that prints an integer) |
| timezone for "today" / Monday | — | `AVATAR_TZ` (IANA name; default system local) |

## Step by step

### 1. Drive index before anything else

The library needs a `drive_id`/`drive_url` per entry and a lean file -> link index. Without it the
agent cannot cite the photo it used. List the folder through the Drive API, match on the
`reference_id` in the filename, and write it back into the library. Entries with no file in the
batch stay **without a link, explicitly** — an empty link is visible, a substitute image is not.

### 2. Download and find the face

```
python3 -m venv /tmp/cvenv && /tmp/cvenv/bin/pip install "opencv-python-headless<5"
export GOOGLE_DRIVE_TOKEN="$(gcloud auth print-access-token)"   # or any OAuth token with Drive read
./scripts/avatar_build.py --base path/to/avatars --library path/to/reference-library.json \
    --batch v6 --folder <drive_folder_id> --cv-python /tmp/cvenv/bin/python
```

OpenCV **4.x** (5.0 removed `CascadeClassifier`). If the host has no cv2, use a throwaway venv;
cropping only needs Pillow. The detector is frontal Haar in 3 variants over the **top of the image
upscaled 3x**, and each candidate only counts if the **eyes-with-glasses** cascade finds at least
one eye inside the box. Without that validation it picks wall frames, cushions, plants and —
literally — an armpit in a raised-arm pose. Even with it, it is wrong about 10–20% of the time.

### 3. CHECK by looking — the step you never skip

```
./scripts/avatar_build.py --base path/to/avatars --contact-sheet /tmp/contact.png
```

Generates the sheet with every crop **inside the circle**, the way Discord shows it. Read the
image. A face outside the circle is the only error the user sees, and they see it immediately.

Wrong? Fix it in `faces_<batch>.json` and mark `"source": "hand-checked"` — a re-run keeps what was
hand-checked and only re-detects the rest:

```json
"ref_021-full-body-hot-day-tying-hair_v6.png": {
  "center_x_pct": 48.6, "center_y_pct": 11.3, "face_height_pct": 9.2, "source": "hand-checked"
}
```

To find the right coordinates, **do not guess from a thumbnail** — that got 5 of 8 wrong. Run the
detector with eye validation on just that image and read the candidates, or render the image with
a % grid and read it at a decent resolution.

### 4. Zoom: not everything is a close-up

A profile bubble does not require a face close-up. Variation in distance is what makes the
rotation feel alive. Default per framing (`ZOOM` in the build script):

| Framing | Square side | Face at … from the top |
|---|---|---|
| `avatar` (image already square, composed as an avatar) | whole image | — |
| `half-body` | 4.5 × face height | 36 % |
| `full-body` | 4.0 × face height | 38 % |

Per-image override in `faces_<batch>.json`: `"side_in_faces": 3.0`, `"face_y": 0.42`, or
`"crop": "full"`. The first pass used 3.0 / 42 % for everything and the feedback was "too much
zoom, always the same little format".

### 5. Roles: what the draw consults

The manifest derives **roles** from the library's `category_tags` + `collections` (the `ROLES`
table in the build script — example signals, adapt them to your library's vocabulary). The rotate
script does not know slugs; it knows roles:

- day with 5+ calendar events -> draws among the `focus` moods (glasses + tablet/whiteboard/
  notebook/desk)
- Monday -> among the `briefing` moods (whiteboard)
- otherwise -> general draw **avoiding the last 8** in `history.jsonl`

The other roles (`profile`, `cozy`, `playful`, `event`, `scolding`) exist for the agent to pick in
conversation ("put on a coffee one" -> `avatar list "coffee"`). A mood with no signal at all falls
into `general`.

Old crops (made by hand before the batch) are kept in the manifest as **legacy**, with
`reference_id: null` — do not delete what the user has already seen live.

Forcing a specific photo: `avatar_rotate.py --mood coffee-chat` or `--mood ref_043` — a
`reference_id` is resolved to its mood through the manifest.

### 6. Wire it into the agent

If the agent **has no filesystem tool** (only a single sandboxed command surface), a file in a repo
is useless to it — the library and the index become **subcommands** of that surface
(`ref list|search|get|catalog`, `avatar list|roles|status|<mood|reference_id>`), typically calling
`avatar_rotate.py --json --origin agent`. Then update the agent's instructions file (e.g.
`AGENTS.md`): the commands, the rule to cite the `reference_id`, and delete any stale "only 3 of
the 40 are ready" note. Test **one real switch** (HTTP 200) before telling the user.

### 7. New batch

```
./scripts/avatar_build.py --base path/to/avatars --library path/to/reference-library.json \
    --batch v7 --folder <v7_folder_id> --cv-python /tmp/cvenv/bin/python
./scripts/avatar_build.py --base path/to/avatars --contact-sheet /tmp/contact.png   # look
```

Moods from the previous batch whose file still exists stay in the manifest. If the library
renumbered references (it happens between batches: e.g. 039/040/041 became 029/030), the old slugs
survive as legacy without a `reference_id`.

## Pitfalls

- `cv2 5.x` has no `CascadeClassifier`; pin `<5`.
- A golden-hour scene that is entirely orange: segmenting by hair color (e.g. red hair) catches the
  whole background. Do not try.
- Do not trust the face Haar found just because it found one; eye validation drops most false
  positives, and the contact sheet drops the rest.
- Slugs longer than 32 chars: the mood regex in the agent's surface (e.g. `MOOD_RE`) has to accept
  them (48 is a safe limit).
- `history.jsonl` without `reference_id` in old lines: `list` shows `null`, that is not a bug.
- The daily cron and the on-demand switch are independent: if the agent switches in the afternoon,
  the cron switches again the next day. Say so in the agent's persona/instructions.
- Use the per-server avatar endpoint (`PATCH /guilds/{id}/members/@me`), not `PATCH /users/@me`:
  it leaves the bot's global profile alone and avoids the opaque global-avatar cooldown.
- Keep the bot token in the environment or a dotenv file with restricted permissions — never in
  the manifest, the history or the agent's instructions.

## See Also

- [consistent-visual-generation](../consistent-visual-generation/SKILL.md) — how the Character
  Bible, the canonical references and the version-in-filename convention this skill consumes are
  produced.
