# Delivery specs per platform (Reels / TikTok / Shorts / LinkedIn)

Adapted from `claude-shorts` (MIT, AgriciDaniel) + local validation 2026-08-09.
Encode params are NOT hardcoded here: run `scripts/gpu_probe.py` and use
what it returns — different cards want different presets and codecs.

## Encode table

All of them: **1080x1920, 9:16, H.264 High@4.2, yuv420p, `-movflags +faststart`**.

| | YouTube Shorts | TikTok | Instagram Reels |
|---|---|---|---|
| Max duration | 60s (3 min in 2025+) | 60s (10 min with account) | 90s (3 min in 2025+) |
| Video bitrate | 12M target / 14M max | CRF 18, max 10M | 4.5M target / 5M max |
| Bufsize | 24M | 20M | 10M |
| Audio | AAC 192k / 48kHz | AAC 128k / 44.1kHz | AAC 128k / 44.1kHz |
| Max size | 256 MB | 287 MB | 250 MB |

LinkedIn: prefer **1:1 (1080x1080)** — the desktop feed crops the 9:16
preview (already the recorded decision in SKILL.md). Max 10 min / 5 GB.

## Loudness: -14 LUFS EVERYWHERE

Every platform normalizes to ~-14 LUFS. If you deliver louder, THEY turn it
down (and only the distortion remains). Normalize first:

```
-af loudnorm=I=-14:TP=-1:LRA=11
```

- `I=-14` integrated target · `TP=-1` true peak (anti-clip headroom) · `LRA=11` loudness range

For serious delivery, use **2-pass** `loudnorm` (the 1-pass version is off by
~1 LU): measure with `-af loudnorm=I=-14:TP=-1:LRA=11:print_format=json -f null -`,
then feed back `measured_I/measured_TP/measured_LRA/measured_thresh`.

## Safe zones (where the platform UI covers the video)

⚠️ **No platform publishes official pixel specs.** The numbers below are the
median of 10+ community measurements at 1080x1920, and the bottom margin
varies with the caption/description size. Treat them as a starting point and
CHECK against a real frame before delivering a campaign.

| Zone | TikTok | YT Shorts | IG Reels | Universal |
|---|---|---|---|---|
| Top | 150px | 150px | 210px | 210px |
| Bottom | 320px | 350px | 340px | 450px |
| Left | 60px | 60px | 40px | 60px |
| Right | 120px | 150px | 100px | 150px |

**Word-level captions**: `MarginV 400` (the `word_captions.py` default) clears
TikTok (320) and IG (340) and covers YT Shorts (350). For a cross-platform post
with no rework, **450px+** is the safe bet. The current value of 400 is correct
for today's use — only raise it if you post the SAME file to all three.

## Verifying the safe zone without guessing

Draw the guides on a frame and LOOK (rule 5 of SKILL.md — visual QA, always):

```bash
ffmpeg -nostdin -y -ss 3 -i IN.mp4 -frames:v 1 -vf \
"drawbox=x=0:y=0:w=1080:h=210:color=red@0.35:t=fill,\
drawbox=x=0:y=1470:w=1080:h=450:color=red@0.35:t=fill,\
drawbox=x=0:y=0:w=60:h=1920:color=orange@0.3:t=fill,\
drawbox=x=930:y=0:w=150:h=1920:color=orange@0.3:t=fill" /tmp/safezone.jpg
```

Nothing essential (face, caption, logo) may fall inside the painted areas.

## Final encode: use the probe

```bash
# the right params for THIS machine
ARGS=$(python "$SKILL/scripts/gpu_probe.py" --encode-args --quality high)

ffmpeg -nostdin -y -i IN.mp4 $ARGS \
  -af loudnorm=I=-14:TP=-1:LRA=11 \
  -c:a aac -b:a 128k -ar 44100 \
  -movflags +faststart OUT.mp4
```

Per-platform bitrate (when you want to hit the table instead of CRF/CQ):
swap `-cq N -b:v 0` for `-b:v 4500k -maxrate 5000k -bufsize 10M` (Reels),
`-b:v 12M -maxrate 14M -bufsize 24M` (Shorts).

## Hardware notes (measured 2026-08-09)

- **Example: a GTX 1650 SUPER** (TU116, 4 GB): h264_nvenc + hevc_nvenc,
  **B-frames OK on both** (confirmed by a real encode: 44 B-frames in an HEVC
  test — the "TU116 has no B-frames in HEVC" table that circulates online is
  wrong for this chip). No AV1. Max ~3 parallel encodes. `-preset p5`.
  ⚠️ NVENC **does not exist inside WSL2** — NVENC encodes run on the Windows
  ffmpeg; WSL handles filters/concat/libass on the CPU.
- **Example: an RTX 5060** (Blackwell) on another machine: 9th-gen NVENC,
  **AV1** and 4:2:2, `-preset p6` with headroom, more simultaneous sessions.
  Don't assume — run the probe there too; `--codec av1` is only worth it if the
  destination accepts it (YouTube accepts AV1; TikTok/IG: stay on H.264).
- No NVIDIA (or codec missing): the probe falls back on its own to
  libx264/libx265/libsvtav1 on the CPU.
