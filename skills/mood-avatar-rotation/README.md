# mood-avatar-rotation

Turn a character's canonical reference images into a mood-based avatar rotation for a chat bot — face-aware square crops, a mood -> roles manifest, and a daily switch script that draws by role without repeating.

## Purpose

A character with dozens of canonical images often ends up with an avatar that cycles through the same three hand-made crops. This skill processes the whole reference library into avatar-ready crops, derives roles (focus, briefing, profile, cozy, playful, event, scolding) from the library's tags and collections, and rotates the bot's per-server Discord avatar by day context — so every canonical gets used and the agent can cite which reference it is wearing.

## Features

- **Batch download** — pulls a batch folder from Google Drive (only missing files), or works on PNGs you drop in place
- **Face detection that survives real art** — 3 frontal Haar variants on the upscaled top of the image, each candidate validated by an eyes-with-glasses cascade (rejects wall frames, plants, armpits)
- **Hand-checked overrides** — fix a face box in `faces_<batch>.json`, mark it `hand-checked`, and re-runs keep it
- **Zoom by framing** — native avatars go in whole, half-body and full-body get different distances; per-image `side_in_faces`, `face_y`, `crop: full`
- **Contact sheet** — every crop inside a circle, the way Discord shows it, to check before shipping
- **Mood manifest** — `moods.json` maps mood -> file, `reference_id`, library entry, roles, framing; legacy crops preserved
- **Rotation rules** — busy calendar -> `focus`, Monday -> `briefing`, otherwise a draw avoiding the last 8; force by mood slug or `reference_id`
- **Per-server avatar** — `PATCH /guilds/{id}/members/@me`, idempotent, with state, JSONL history and `--json` output for agent wrappers
- **No hardcoded paths** — everything via flags or env vars (`AVATAR_BASE`, `AVATAR_LIBRARY`, `DISCORD_GUILD_ID`, `DISCORD_BOT_TOKEN`, `AVATAR_EVENTS_CMD`, `AVATAR_TZ`)

## Quick Start

```bash
python3 -m venv /tmp/cvenv && /tmp/cvenv/bin/pip install "opencv-python-headless<5"
pip install Pillow
export GOOGLE_DRIVE_TOKEN="$(gcloud auth print-access-token)"

# build crops + moods.json from a Drive batch
scripts/avatar_build.py --base path/to/avatars --library path/to/reference-library.json \
    --batch v1 --folder <drive_folder_id> --cv-python /tmp/cvenv/bin/python

# look at every crop before going live
scripts/avatar_build.py --base path/to/avatars --contact-sheet /tmp/contact.png

# preview, then apply the mood of the day
export AVATAR_BASE=path/to/avatars DISCORD_GUILD_ID=<server_id> DISCORD_BOT_TOKEN=<token>
scripts/avatar_rotate.py --list
scripts/avatar_rotate.py --dry-run
scripts/avatar_rotate.py
```

## See Also

- [SKILL.md](SKILL.md) — Full procedure (design, face detection, zoom table, roles, agent wiring, new batches, pitfalls)
- [scripts/avatar_build.py](scripts/avatar_build.py) — Drive -> faces -> crops -> manifest
- [scripts/avatar_rotate.py](scripts/avatar_rotate.py) — daily / on-demand avatar switch
- [consistent-visual-generation](../consistent-visual-generation/README.md) — producing the Character Bible and canonical references this skill consumes
