# House style: Instagram vs LinkedIn (what a real channel shipped)

`platform-specs.md` holds the generic platform limits. This file holds the
**defaults of one interview-clip channel**, taken from the scripts in
`examples/interview-clip-pipeline/` and from `ffprobe` of six clips that went
live (three interview cuts, a Reels and a LinkedIn version of each). Treat it
as the default when the user asks for "the Instagram one and the LinkedIn
one" and says nothing else. A request from the user overrides any line here;
another channel may well prefer other values.

## One rule

Instagram gets the 9:16 cut. LinkedIn gets the **same** cut, re-laid out with
blurred sides, with the same captions resized and a softer transition. Never
re-cut or re-transcribe for LinkedIn: derive it from the 9:16 (`04-render-linkedin.sh`).

## Same on both

| Item | Value |
|---|---|
| Video | H.264 High, `yuv420p`, 30 fps, libx264 `-crf 18 -preset slow`, `-movflags +faststart` |
| NVENC trap | always `-pix_fmt yuv420p -profile:v main` (or `high`), and close filter chains with `format=yuv420p`; otherwise phone/screen sources leave as H.264 4:4:4 and Instagram/LinkedIn refuse the file |
| Audio | AAC stereo 192k / 48 kHz (what the six live clips have), `loudnorm=I=-14:TP=-1:LRA=11`, 2-pass for delivery |
| Captions | word-level, UPPERCASE, burned in, in the language of the audience (this channel: always English, even when the speech is in another language; the speech stays as recorded) |
| Structure | cold open of 2–4 s with the strongest line, then the full take; a credentials intro becomes a burned caption on the first frame; false starts and a trailing "Okay." stay out |
| Delivery QA | `ffprobe ... stream=profile,pix_fmt` must say `High`/`Main` and `yuv420p`, plus the safe-zone frame from `platform-specs.md` |

## What changes

| | Instagram (Reels) | LinkedIn |
|---|---|---|
| Canvas | 1080×1920, 9:16 | **4:5, 1080×1350** (default), or 1:1, 1080×1080 |
| Why | native Reels format | the desktop feed crops a 9:16 preview |
| Layout | the cut as is (blur pad only if the source is horizontal) | foreground scaled to the canvas height, background = same video scaled up, cropped, `gblur=sigma=30` |
| Caption style (from the 9:16 `.ass`) | font 88, `MarginV 400` | 4:5: font 72, `MarginV 140` · 1:1: font 64, `MarginV 90` |
| Safe zone | top 210 px, bottom 340, left 40, right 100 (community medians: check a real frame) | no UI overlay rule; keep captions off the bottom edge |
| Hook→take transition | zoom 100→112% over the last 0.3 s of the hook + white flash 0.15 s out / 0.15 s in + low-end whoosh at −6 dB | zoom 100→110% + same flash + whoosh at −9 dB |
| Max length | 90 s in the table (3 min since 2025); one live Reels went out at 1:47 | 10 min / 5 GB |
| Bitrate seen on live files | 5.0–10.1 Mbps | 3.1–3.2 Mbps |
| File tag | `<name>-REELS-<lang>-FINAL.mp4` | `<name>-LINKEDIN45-<lang>-FINAL.mp4` (4:5) or `<name>-LINKEDIN-<lang>-FINAL.mp4` (1:1) |

## 4:5 or 1:1 on LinkedIn

- `04-render-linkedin.sh` still defaults to 1:1 (`RATIO=11`); pass `RATIO=45` for 4:5.
- **Prefer 4:5.** 1:1 was vetoed on a small source (382×850): inside a square
  the foreground gets too small, and 4:5 keeps it larger.
- 1:1 is fine when the source is sharp; earlier clips from the same channel
  went out in 1:1.
- A source pinned on someone else (a call recording where the speaker you
  want is a 220 px thumbnail) is not publishable in either format: a preview
  there only approves the cut and the text.

## Preferences, not hard rules (pick when the user has not)

- **Reels bitrate:** CRF 18 is what has been shipped. Instagram re-encodes
  anyway, so `-b:v 4500k -maxrate 5000k -bufsize 10M` (the table in
  `platform-specs.md`) gives the same result with a file 2–3× smaller. Use it
  when size matters (slow upload, storage quota); keep CRF 18 when the same
  master also goes to YouTube.
- **Reels audio:** the table says AAC 128k / 44.1 kHz; the shipped files use
  192k / 48 kHz. Both are accepted; pick one and keep it consistent across the archive.
- **Transition strength:** the "invisible" version (static 10% punch in Reels,
  6% in LinkedIn, whoosh at −12/−15 dB) was rejected in review as "too dry".
  Ship the animated zoom + flash combo above unless the user asks for something subtler.
- **Punch-out variant** (hook at ~112–115%, take at 100%) keeps the long take at
  native resolution: a good default for long clips.
- **Versions:** move older renders to a `_superseded/` subfolder, never next
  to the FINAL file.

## What the post text does (not the video, but asked together)

- Pick one language for public copy and keep it on both platforms.
- Instagram: the author's own text trimmed to fit 2,200 characters, delivered
  in full. LinkedIn: hook in the first two lines (the question or the thesis),
  context after.
- CTA = newsletter + the guest's link. Do not sell a service in a clip post.
