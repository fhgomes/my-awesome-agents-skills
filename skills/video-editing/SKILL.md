---
name: video-editing
description: >-
  Cut, join, reformat (9:16 Reels/Shorts/TikTok, 1:1 and 4:5 LinkedIn) and burn
  captions into video with ffmpeg and faster-whisper. Use whenever the user asks
  to "cut the video", "make a clip", "join the segments", "version for
  Reels/Shorts/TikTok", "9:16", "blurred background", "burn subtitles",
  "CapCut-style word-by-word captions", "cold open", extract a segment or a
  frame, concat clips, or any command-line video editing. Also covers: delivery
  specs per platform (bitrate, max duration, safe zones, -14 LUFS), choosing
  WHICH segment becomes a clip (hook/coherence/emotion rubric), 9:16 reframing
  that follows the speaker (face-pan), the xfade transition catalog and which
  durations read well, the hook-to-content transition (punch-in + whoosh),
  color grading and correction (iPhone HLG, cross-source consistency, skin-tone
  protection) and GPU/NVENC detection at runtime (scripts/gpu_probe.py — NEVER
  hardcode card parameters). Ships ready scripts (word_captions.py,
  word_captions_map.py, face_pan.py, gpu_probe.py) — do not rewrite them from
  scratch. For long-form transcription (full SRT/TXT of a talk) use the
  media-transcription skill. Also triggers on the equivalent phrases in other
  languages.
---

# Video editing (ffmpeg + word-level captions)

## 0. Environment: detect, never assume

Machine-specific facts (GPU model, driver version, paths, which ffmpeg build
lives where) belong in the agent's **memory for that machine**, not in this
skill. The skill has to run unchanged on any computer.

- **GPU / encoder**: run `scripts/gpu_probe.py` first. It asks `nvidia-smi` and
  ffmpeg what exists *here* and prints the right encode arguments. Two machines
  with different cards (say a 4 GB Turing card and a Blackwell card) want
  different presets, codecs and session limits.

  ```bash
  python "$SKILL/scripts/gpu_probe.py"                       # readable report
  ARGS=$(python "$SKILL/scripts/gpu_probe.py" --encode-args --quality high)
  ```

- **Two ffmpeg builds is a common setup** and each has a job:
  - A Linux/WSL ffmpeg (often an older distro build, CPU-only) for filters,
    concat, extraction and `libass` burns. Invoke from Windows as
    `wsl.exe -d <distro> -- bash -c ...`.
  - A native Windows ffmpeg with NVENC for long encodes and burns
    (`h264_nvenc` runs roughly 8–15x faster than `x264 medium`). Point the
    scripts at it with the `FFMPEG_BIN` environment variable.
  - **NVENC does not exist inside WSL2** (GPU paravirtualization only exposes
    CUDA compute). Hardware encodes must run on the Windows side.
  - The **xfade transition catalog and available filters depend on the ffmpeg
    version**, not on extra libraries (see section 7). Check with
    `ffmpeg -h filter=<name>` on the build you are about to use.
- **NVENC parameters that validated well on a Turing (TU116) card**:
  `-c:v h264_nvenc -preset p5 -rc vbr -cq 22 -b:v 0 -bf 3`. TU116 supports
  B-frames in both H.264 and HEVC (confirmed by a real encode that produced
  44 B-frames in an HEVC test; the spec tables that say otherwise are wrong for
  this chip). `gpu_probe.py` tests B-frame support empirically instead of
  trusting a table.
- 🚨 **Always `-pix_fmt yuv420p -profile:v main` (or `high`) on NVENC.** Without
  it NVENC inherits the input pixel format: an iPhone or screen-recording `.MOV`
  comes in as `yuv444p` and leaves as *H.264 High 4:4:4 Predictive*, which
  Windows Media Player (`0x80004005`), Instagram and LinkedIn refuse to open.
  With a filter chain, also close it with `,format=yuv420p`. Always add
  `-movflags +faststart` and `-ac 2`. Delivery QA, one command, before sending
  any file:

  ```bash
  ffprobe -v error -select_streams v:0 -show_entries stream=profile,pix_fmt -of default=noprint_wrappers=1 OUT.mp4
  # must print profile=Main (or Baseline/High) and pix_fmt=yuv420p
  ```

- A package-manager ffmpeg 8.x requires an NVIDIA driver ≥ 610 for NVENC
  ("nvenc API 13.1 required"). On an older driver, pin a 7.x build.
- `libass` finds system fonts by itself; on WSL pass
  `fontsdir=/mnt/c/Windows/Fonts` to reach the Windows fonts (otherwise it
  falls back to DejaVu). Use relative paths and `cd` into the folder first.
- Python + faster-whisper + CUDA usually live on the side that owns the GPU;
  see the media-transcription skill. Transcribe there, burn wherever ffmpeg is.
- WSL path mapping: `C:\Users\<you>\Videos` → `/mnt/c/Users/<you>/Videos`.
  Put intermediates in WSL `/tmp` (ext4 is faster than `/mnt/c`) and clean up
  at the end. **Do not leave assets in `/tmp` between commands**: the distro
  shuts down when idle and wipes `/tmp` on boot. Anything that must survive
  goes to a real folder.
- `bc` may be missing in the WSL distro. A script doing
  `$(echo "$X-0.15" | bc)` then returns an empty string and ffmpeg dies with
  `Unable to parse option value "" as duration`. **Pre-compute the constants
  at the top of the script** or use `awk "BEGIN{print $X-0.15}"`.

## 1. Golden rules (learned the hard way)

0. **Orchestration: a subagent NEVER leaves an encode running in the background
   and returns "waiting".** The process dies with the agent or workflow (a
   794 s segment died twice that way). Patterns that work: (a) long encodes run
   as a background task of the MAIN loop, which survives across turns and gets
   notified; (b) a subagent only runs foreground work (timeout ≤ 10 min: split a
   long encode into halves and concat); (c) a REAL detach inside WSL:
   `nohup bash /tmp/x.sh > /tmp/x.log 2>&1 &` plus a foreground waiter.
   Subagents take analysis, captions and QA (file work).
   GPU: transcriptions ALWAYS sequential (one whisper at a time on a 4 GB
   card); a CPU-only ffmpeg handles at most 2–3 parallel encodes (they share
   cores).
   Muting a spoken name: use a window with ≥ 0.15 s of slack on each side and
   RE-CHECK with `volumedetect` (AAC frame boundaries leak: the exact window
   measured −37 dB, the widened one −91 dB).
1. **Always `ffmpeg -nostdin`.** Without it ffmpeg reads stdin, enters
   interactive mode, and once produced a 305 MB debug log while the rest of the
   script was interpreted as keystrokes.
2. **Scripts go through a FILE, never a pipe**:
   `tr -d '\r' < /mnt/c/.../x.sh > /tmp/x.sh && bash /tmp/x.sh`. Piping into
   `bash` feeds ffmpeg's stdin (rule 1); `tr -d '\r'` strips Windows CRLF.
   With PARALLEL agents use a UNIQUE `/tmp` name per agent
   (`/tmp/clipA-x.sh`, `/tmp/clipB-x.sh`): two agents sharing `/tmp/x.sh`
   overwrote each other and one cut died mid-way ("command not found").
3. **Inline quoting does not survive** the Git Bash → `wsl.exe` → bash chain
   (`$VAR` expands empty, quotes vanish). Anything with a variable or a
   `filter_complex` goes into a script file.
4. **Phone video: raw ffprobe lies about orientation.** A `VID_*.mp4` reported
   as 1920x1080 may be VERTICAL (rotation lives in the display matrix). A
   re-encode applies the rotation by itself (autorotate). Before planning a
   9:16 filter, extract a frame and LOOK at it. If the source is already
   native 9:16, the blurred-background recipe is a no-op — skip it.
5. **Visual QA always**: after every render extract 2–3 frames at known
   timestamps and check framing, the right caption, and the format.
6. **Delivery QA always**: the `ffprobe` profile/pix_fmt check from section 0.

## 2. Recipe: cut with a splice (cold open + take)

Re-encode each segment with identical parameters, then concat without
re-encoding:

```bash
set -e
IN=/mnt/c/Users/<you>/Videos/ORIGINAL.mp4
OUT=/mnt/c/Users/<you>/Videos
mkdir -p /tmp/work && cd /tmp/work

# -ss/-to AFTER -i = frame-accurate on the original timeline
ffmpeg -nostdin -y -i "$IN" -ss 00:03:28.0 -to 00:03:31.5 \
  -c:v libx264 -preset slow -crf 18 -r 30 \
  -c:a aac -b:a 192k -ar 48000 -ac 2 p1.mp4 -loglevel error
ffmpeg -nostdin -y -i "$IN" -ss 00:00:24.0 -to 00:01:38.0 \
  -c:v libx264 -preset slow -crf 18 -r 30 \
  -c:a aac -b:a 192k -ar 48000 -ac 2 p2.mp4 -loglevel error

printf "file 'p1.mp4'\nfile 'p2.mp4'\n" > concat.txt
ffmpeg -nostdin -y -f concat -safe 0 -i concat.txt -c copy "$OUT/FINAL.mp4" -loglevel error
```

Check the final duration with ffprobe (sum of the segments ± 0.1 s). A
complete, parameterized version of this pipeline lives in
`examples/interview-clip-pipeline/`.

## 3. Recipe: 9:16 with blurred background (horizontal sources only!)

```bash
ffmpeg -nostdin -y -i in.mp4 -filter_complex \
"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=30[bg];[0:v]scale=1080:-2[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2" \
-c:v libx264 -crf 20 -preset slow -c:a copy out-reels.mp4
```

For a low-resolution horizontal source it is cheaper to apply this pad while
cutting each segment (one encode) — see `02b-cut-blurpad.sh` in the examples.

## 4. Recipe: 1:1 or 4:5 for LinkedIn from the 9:16 cut (blur sides + captions, one encode)

LinkedIn's desktop feed crops the 9:16 preview; 1:1 (1080x1080) or 4:5
(1080x1350) perform better. Reuse the 9:16 `.ass` via sed (this preserves the
QA corrections — do NOT re-transcribe):

```bash
# 1:1
sed 's/PlayResY: 1920/PlayResY: 1080/; s/,88,/,64,/; s/,60,60,400,1/,60,60,90,1/' \
  CLIP-words.ass > CLIP-LINKEDIN-words.ass
# 4:5
sed 's/PlayResY: 1920/PlayResY: 1350/; s/,88,/,72,/; s/,60,60,400,1/,60,60,140,1/' \
  CLIP-words.ass > CLIP-LINKEDIN45-words.ass
```

Format and captions in a single filter chain (one encode generation less):

```bash
cp CLIP-LINKEDIN-words.ass /tmp/li.ass
ffmpeg -nostdin -y -loglevel error -i CLIP.mp4 -filter_complex \
"[0:v]scale=1080:1080:force_original_aspect_ratio=increase,crop=1080:1080,gblur=sigma=30[bg];[0:v]scale=-2:1080[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,ass=/tmp/li.ass:fontsdir=/mnt/c/Windows/Fonts" \
-c:v libx264 -crf 18 -preset slow -c:a copy CLIP-LINKEDIN-SUB.mp4
```

## 5. Recipe: 9:16 that follows the speaker (face-pan) — alternative to the blurred background

For a 16:9 interview or podcast with TWO people and a static camera: instead
of shrinking the frame into the middle of the canvas, frame whoever is
speaking full-screen with a hard cut. `scripts/face_pan.py` (ported from
clipify, MIT) — no OpenCV, no ML: it measures the brightness
(`signalstats.YAVG`) of two mouth/chin ROIs and infers the speaker from the
variation.

```bash
# 1) extract a frame and LOOK to find the ROIs (rules 4/5)
python "$SKILL/scripts/face_pan.py" probe --video IN.mp4 --at 5

# 2) check the drawn boxes (iterate at most twice — it is tolerant)
python "$SKILL/scripts/face_pan.py" probe --video IN.mp4 --at 5 \
  --left 100,300,500,400 --right 1300,300,500,400

# 3) build the filter chain
VF=$(python "$SKILL/scripts/face_pan.py" build --video IN.mp4 \
      --left 100,300,500,400 --right 1300,300,500,400)

# 4) burn together with the captions (one encode)
ffmpeg -nostdin -y -i IN.mp4 -vf "$VF,ass=/tmp/subs.ass:fontsdir=/mnt/c/Windows/Fonts" \
  -c:v libx264 -crf 18 -preset slow -c:a copy OUT.mp4
```

Validated on a synthetic video: the switch was detected at 3.033 s against a
ground truth of 3.000 s (one frame of error, from the smoothing window).

- ROI = **mouth + chin**, avoiding hands and microphone (a gesturing hand
  fools it).
- `--margin 1.15` is the hysteresis: only switch when the other side exceeds
  the current one by 15% — without it the cut flickers during silence. Raise
  it if unstable.
- `--min-dur 1.0` discards switches too short to read on screen.
- **Only works with a static camera within the cut.** If the camera moves or
  there is a shot change, the method breaks — use the blurred background.
- Single speaker: not needed, a centered `crop` does it.

## 6. Recipe: CapCut-style word-level captions (automated)

A normal transcription SRT (10–15 s sentence blocks) looks UGLY burned into a
Reel. The path: regenerate word-level and burn.

1. **Transcribe the ALREADY-CUT video** (never the original — timestamps are
   born correct on the final timeline, no re-sync):

   ```bash
   python "$SKILL/scripts/word_captions.py" CLIP.mp4 --out-dir OUTDIR \
     --base CLIP --language en --prompt "expected proper nouns and jargon"
   ```

   Produces `CLIP-words.ass` (ready to burn: 1080x1920, Arial Black 88,
   UPPERCASE, `MarginV 400` = above the Reels UI) and `CLIP-words.srt` (same
   blocks, for review or CapCut). Flags: `--max-words 3 --max-dur 1.2 --res
   --font --font-size --margin-v --no-upper`. GPU: 77 s of video ≈ 13 s. Check
   `nvidia-smi` first (a busy GPU crawls; see media-transcription).

2. **QA the .srt** (read it in full — it is short): typical errors are
   acronyms ("SSD" → "SDD") and tokenizer hyphens ("CO -WORKER"). Fix with sed
   **in both files** (.srt AND .ass). Leave real speech repetitions ("that
   that") — that is how the person spoke.

3. **Burn** (on WSL, `fontsdir` gives libass the Windows fonts):

   ```bash
   cp "$OUT/CLIP-words.ass" /tmp/subs.ass
   ffmpeg -nostdin -y -loglevel error -i "$OUT/CLIP.mp4" \
     -vf "ass=/tmp/subs.ass:fontsdir=/mnt/c/Windows/Fonts" \
     -c:v libx264 -crf 18 -preset slow -c:a copy "$OUT/CLIP-SUB.mp4"
   ```

4. Visual QA: frames at 2–3 timestamps with known text from the .srt.

5. **Restructuring a cut that already has corrected captions** (swap/remove a
   segment, shorten the intro): do NOT re-transcribe — edit the existing blocks
   by script (remove a time range, shift the rest by the exact measured
   delta). Re-transcribing reintroduces splice hallucinations (every cut
   boundary generates garbage) and loses the manual corrections. Whisper also
   SWALLOWS a short cold open when spliced (merges it with the following
   sentence) — always check the first blocks against what was said.

6. **Better flow (validated on 5 clips): transcribe the ORIGINAL once and
   DERIVE each clip's captions** with `scripts/word_captions_map.py`
   (`--words-json` plus `--segments "a-b,c-d"` in seconds of the original
   timeline → remaps the words onto the concatenated timeline, in segment
   order). Advantages: the SAME word timestamps plan the cut points on exact
   word boundaries; zero splice hallucination; the cold open is never
   swallowed; N clips of one video = 1 transcription. TRAP: check for a
   STRETCHED word at the boundary (a 1 s name almost got cut in half — check
   the real start of the first word in the JSON, not the SRT block). Runs on
   CPU int8 (~0.23x realtime) — use it when the GPU is busy (`nvidia-smi`
   showing a game or another CUDA process = do NOT load a CUDA model).

## 7. xfade transitions: catalog depends on the ffmpeg version

⚠️ **The list of `xfade` transitions is a function of the ffmpeg VERSION, not
of an extra library.** The filter gained effects on every release. Measured
on two builds of the same machine:

| Binary | Version | Transitions |
|---|---|---|
| WSL distro package | 4.4.2 (2022) | **43** |
| Windows package-manager build | **9.0** (2026) | **58** |

The **15 exclusive to 9.0** (absent in 4.4): `zoomin`, `coverleft/right/up/down`,
`revealleft/right/up/down`, `hlwind`, `hrwind`, `vuwind`, `vdwind`, `fadefast`,
`fadeslow`. On Linux a recent ffmpeg is enough — nothing else to install.
👉 **For transitions use the newest ffmpeg available** (it usually also has
NVENC). Leave filters/concat/audio to the other build. Count on a new machine:
`ffmpeg -h filter=xfade | grep -cE "^\s+[a-z]+\s+[0-9]+\s+\.\.FV"`

### What read well in a review with a human viewer (22 samples watched)

**Approved at normal speed (0.3–0.5 s):**
`zoomin` · `coverleft` · `revealleft` · `slideleft` (push) · `hblur` · `squeezeh`

**With reservations:** `fadefast`. **Rejected:** `dissolve` (grainy).

### Exact DURATION per transition (second round: 0.6 / 0.9 / 1.2 s of each)

| Transition | Approved duration | Note |
|---|---|---|
| `circleopen` | **1.2 s** | |
| `diagtl` | **1.0 s** | use sparingly |
| `hlwind` | **0.9 s** | "looks nice" |
| `circlecrop` | **0.8 s** | |
| `pixelize` | **0.8 s** | rated "really nice" in round 1 |
| `radial` | **0.75 s** | |
| `vuwind` | ❌ avoid | preferred top-to-bottom → use **`vdwind`** |

⚠️ **Wind direction:** `vuwind` goes UP, `vdwind` goes DOWN. Same logic for
`hlwind`/`hrwind`. Vary the transition with the video instead of always using
the same one. The "slow" ones look bad at 0.3 s — the effect needs time to read.

### Offset rule (cause #1 of "the transition did not show up")

`offset = duration_of_clip_A − transition_duration`

### Swapping an xfade for a hard cut CHANGES the total duration

An xfade overlaps; a hard cut adds. The timeline grows by the crossfade time
and EVERY caption after the cut drifts. Shift the `.ass` by the measured delta
with a script and re-validate overlap and duration before burning.

### drawtext on a Windows ffmpeg needs an explicit fontfile

Without fontconfig, `drawtext` fails with `Cannot load default config file`,
and the drive colon must be escaped:
`drawtext=fontfile='C\:/Windows/Fonts/arialbd.ttf':text='...'`

### Transition sound: ffmpeg-synthesized SFX was REJECTED

Five procedurally generated sounds (airy whoosh, low impact, dry click, bright
swoosh, riser — only `anoisesrc`/`sine` + filters) were auditioned paired with
the transitions and **all five were rejected** as sounding synthetic.
**Lesson:** filtered noise and sine waves sound fake next to recorded SFX. Do
not insist on synthesizing whoosh/impact in ffmpeg; the next attempt should be
a **library of real sounds** (Freesound CC0, Pixabay, Mixkit): download,
normalize the peak, pair. The only synthesized sound that passed was the
low-end whoosh of the hook transition (section 8), and even then the viewer
asked for "a bit of effect" afterwards.

⚠️ **Always normalize before comparing SFX**: the five came out between −2.9
and −26 dB peak, and without normalizing the listener judges volume, not
timbre. `loudnorm` is NOT for 0.1–3 s clips (it gets lost and widens the
spread) — use direct gain: measure `max_volume` with `volumedetect` and apply
`volume=<delta>dB`.

## 8. Recipe: hook→content transition (researched with three assistants that converged)

The 2025–2026 retention-editing pattern for a cold open → take (same scene) is
NOT a flashy transition — it is a **permanent snap punch-in + subtle low-end
whoosh**:

- **Visual**: on the cut frame the take enters zoomed in ("camera B" effect)
  and STAYS zoomed. Reels 9:16: ~10%; LinkedIn 1:1: ~6% plus raising the
  framing ~20 px (moves the eye line). Hard cut, no animation.
- **Sound**: a LOW-END whoosh (deep/muffled, never bright). Starts ~80 ms
  before the cut, peaks exactly on the cut, tail ~180 ms. Level ~18 dB below
  the voice PEAKS (measure with `volumedetect`; phone voice: mean ~−11, max
  ~0 dBFS → whoosh at −12 dB of the generated file; LinkedIn −15 dB).
- **AVOID (dated "2021 CapCut/Hormozi template", unanimous across sources)**:
  strong white flash, glitch/RGB, artificial whip pan, zoom > 15%, riser, bass
  drop, VHS, film burn, bright "ninja sword" whoosh.

Ready asset: `assets/whoosh-lowend-260ms.wav` (internal peak at ~80 ms →
`adelay = (t_cut − 0.08) * 1000`). Generator: `scripts/make_whoosh.sh`.

Filter chain (preserves the timeline → the `.ass` stays valid; punch via
trim/concat):

```
[0:v]trim=0:3.5,setpts=PTS-STARTPTS[v1];
[0:v]trim=3.5,setpts=PTS-STARTPTS[vz];
[vz]crop=w=980:h=1744:x=50:y=68,scale=1080:1920,setsar=1[v2];   # 10%: 1080/1.1→980 (even), y centered −20
[v1][v2]concat=n=2:v=1:a=0[vc];
[vc]ass=/tmp/subs.ass:fontsdir=/mnt/c/Windows/Fonts[vout];
[1:a]adelay=3420|3420,volume=-12dB[wh];
[0:a][wh]amix=inputs=2:duration=first:normalize=0[aout]
```

Validate audio without listening: `showspectrumpic` of the cut region (whoosh
= low-end smear + a transient column at the cut); punch: frames before/after
the cut.

**Taste calibration**: the "invisible" version from the research (static 10%
punch + whoosh at −19 dB) was rejected by the content owner as "too dry, there
is NOTHING there". When the user asks for a PERCEPTIBLE but smooth transition,
go straight to the validated combo: animated zoom 100→112% over the last 0.3 s
of the hook (`zoompan`, power-2 easing) + white flash ramp 0.15 s + 0.15 s +
whoosh at −6 dB (Reels) / zoom 10% and whoosh at −9 dB (LinkedIn). The
"cartoonish" things to avoid are a BRIGHT sound and effects of 1 s+; a short
soft flash and an audible low whoosh are the growth-editing standard. The full
chain is in `examples/interview-clip-pipeline/03-render-reels.sh`; zoom+flash
go BEFORE the `ass` filter and, in 1:1, BEFORE the layout (so the flash covers
the whole frame).

Refinements from the research workflow (4 agents, recipes EXECUTED on 4.4.2):

- **Punch-OUT variant** (hook at ~112–115% → take at 100%): same effectiveness,
  and the LONG take stays at native resolution (upscale only during the 3.5 s
  hook) — sharper; the hook feels more "intimate/tense". Consider it the
  default for long videos.
- Peak rule: the SFX PEAK lands on the cut frame (tolerance +1–2 frames); the
  file starts 80–300 ms earlier. Level: 6–19 dB below speech PEAKS (more
  present for hype, lower for a professional interview).
- Dosage: max 2–3 punch-ins per minute; one "bold" transition in the first
  5 s and that is it.
- Advanced: J-cut (take audio enters ~300 ms before the video cut, finer
  seam); riser 0.8–1.5 s under the end of the hook peaking at the cut (never
  competing with speech).
- ANIMATED zoom in ffmpeg 4.4: `crop` with `t` expressions does NOT animate —
  use `zoompan=d=1`. Static punch per segment: trim + fixed crop + scale +
  concat (fine). **4.4.2 `zoompan` has NO `in_time`/`it`** (verified:
  `ffmpeg -h filter=zoompan | grep -c in_time` → 0). Ease per FRAME with `on`:
  a 0.3 s segment at 30 fps = 9 frames → `z='min(1.12,1+0.12*pow(on/8,2))'`
  + `x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2':s=1080x1920:fps=30,setsar=1`.
- White flash: **NEVER apply the fade-out/fade-in pair on the GLOBAL timeline
  after concat** (trap: it produced a 100% white video): `fade=t=out` HOLDS
  the color until the end after `st+d`, and `fade=t=in` paints EVERYTHING
  before `st` white. The right way is PER SEGMENT, before concat: at the end
  of the hook segment `...,fade=t=out:st=HOOKLEN-0.15:d=0.15:c=white[vb]` and
  at the start of the body `...,fade=t=in:st=0:d=0.15:c=white[vc]` (`st=0` has
  no "before" to paint). Bonus: the fade-in masks a clipped word tail at the
  start of the body. Never the 15-frame CapCut preset.
- Alternative "airy" whoosh (sweep): `anoisesrc` + `asendcmd` sweeping a
  lowpass 300→4600→900 Hz over 400 ms (more swoosh, less thud than the bundled
  asset). **Executed and validated recipe** (for "something similar but
  different" from the default asset) — 420 ms, peak at ~200 ms:

  ```bash
  ffmpeg -nostdin -y -v error -f lavfi -i "anoisesrc=d=0.42:c=pink:a=0.9:r=48000" \
    -af "asendcmd='0.00 lowpass frequency 300; 0.08 lowpass frequency 1800; 0.20 lowpass frequency 4600; 0.32 lowpass frequency 1600; 0.42 lowpass frequency 900',lowpass=f=300,volume=1.0,afade=t=in:st=0:d=0.05,afade=t=out:st=0.26:d=0.16,highpass=f=90" \
    -c:a pcm_s16le whoosh-airy.wav
  ```

  Since the peak sits at ~200 ms (not 80 ms like the bundled asset), the
  `adelay` is `(t_cut − 0.20) * 1000`. Measure the level first: whoosh at
  −6 dB when the speech peak is around −3 dBFS (phone interview).

## 9. Delivery: platform specs (Reels / TikTok / Shorts / LinkedIn)

See **`references/platform-specs.md`** — bitrate, max duration, file size,
safe zones and the QA command that paints the guides onto a frame.

The three facts that bite most:

1. **−14 LUFS everywhere.** Deliver louder and the platform turns it down,
   leaving only the distortion: `-af loudnorm=I=-14:TP=-1:LRA=11`.
2. **Bottom safe zone.** `MarginV 400` (the `word_captions.py` default) passes
   on TikTok/IG/Shorts. For the SAME file on all three, raise it to 450.
3. **Reels' bitrate is low** (4.5M) compared to Shorts (12M) — sending 12M to
   IG only fattens the file; it re-encodes anyway.

## 10. Color: when (and when NOT) to grade

See **`references/color-grading.md`** — chain order, measured recipes and the
skin-tone test.

The summary that avoids mistakes:

1. **Most clips need no grade.** Well-exposed footage does not; a bad grade is
   worse than none. The case that calls for it is **joining different
   sources** in one clip (cold open from one take, body from another).
2. **Correcting ≠ grading.** Wrong white balance and iPhone HLG are fixed by
   correction (`hable` tonemap), before and independent of any look.
3. **Skin is the judge.** Measured: the warm grade drifts ≤ 2.3° on any skin
   tone (safe); the punch grade drifts up to 9.9° on light skin and pushes
   dark skin the OPPOSITE way — two participants end up misaligned. And the
   villain is the **contrast curve**, not saturation (`saturation=1.3` alone
   drifts ~1.5°). Softening the curve cuts almost half the drift.
4. `colortemperature` is inverted: **a lower number = a warmer image**.

## 11. Editing decisions for Reels (already taken)

- A credentials intro (15–25 s) does NOT go into the clip — it becomes a
  burned caption on the first frame (e.g. "Open-source contributor").
- Cold open: 2–4 s of the strongest sentence, then the full take.
- False starts and trailing "Okay." stay out.
- A static title/caption overlay is better done in CapCut or another editor;
  what is worth automating here is the word-level caption (section 6).
- Picking WHICH segment becomes a clip: `references/clip-scoring.md`.
