---
name: media-transcription
description: >-
  Transcribe audio and video into text and subtitles — locally (faster-whisper
  large-v3 on the GPU) or remotely (youtubetotranscript.com for YouTube
  videos). Use whenever the user asks to "transcribe", "get the text of this
  video/audio", "generate subtitles", "SRT", mentions Whisper, or wants the
  text of a talk, mentoring session, recorded meeting or YouTube video. Also
  use when comparing transcription quality or when a previous transcript has
  loops/hallucinations (the same word repeated over and over) — the fix is the
  large-v3 model. Ships a ready script (scripts/transcribe_gpu.py) — do not
  rewrite it from scratch. Also triggers on the equivalent phrases in other
  languages.
---

# Media transcription (local GPU + remote)

## Quick decision

| Situation | Path |
|---|---|
| Video is already on YouTube and only the text is needed | **Remote**: youtubetotranscript.com (no download, no GPU) |
| Local file (.mp4/.wav/.mp3), quality matters | **Local**: `scripts/transcribe_gpu.py` (large-v3 on GPU) |
| Private video on Google Photos/Drive | Download first (a browser-download skill), then local |

## Step 0 — extract the audio when the video is large (> 500 MB)

Whisper resamples everything to **16 kHz mono** internally. The whole video is
dead weight: I/O, cache and (on a network/external disk) slow reads.

Rule: **video file > 500 MB → extract the WAV first**. Below that, pass the
`.mp4` directly (PyAV decodes it; the extra step is not worth it).

```bash
ffmpeg -nostdin -y -i input.mp4 -vn -ac 1 -ar 16000 -c:a pcm_s16le output.wav \
  -loglevel error -stats
```

Measured: 14.58 GB of video → 197 MB of WAV = **~74x smaller**, with no loss
for the model (it is the maximum resolution it consumes). Rule of thumb: 16k
mono WAV ≈ **115 MB per hour** of audio.

After extracting, **check duration and level** before spending GPU time:

```bash
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1 output.wav
ffmpeg -nostdin -i output.wav -af volumedetect -f null - 2>&1 | grep -E "mean_volume|max_volume"
```

- Duration ≈ expected? If not, the video came truncated.
- `mean_volume` between ~−30 and −12 dB = normal speech. Near −90 dB = **silent
  audio** (do not transcribe: investigate the recording). `max_volume` at
  0.0 dB = clipping.
- **Do not use `-c copy` to cut WAV samples** — it produces a header-only file
  (78 bytes). Re-encode: `-ac 1 -ar 16000 -c:a pcm_s16le`.

### Detect the language first (do not assume)

`--language` defaults to `pt`, and running one hour in the wrong language is
one hour lost. If there is any doubt, cut ~90 s starting at 5 min (skips the
intro/silence) and listen to or transcribe the sample first:

```bash
ffmpeg -nostdin -y -v error -ss 300 -t 90 -i audio.wav -ac 1 -ar 16000 -c:a pcm_s16le sample.wav
```

An interview with a foreign company is almost always **en**, even when the
user describes the video in another language.

## Local — faster-whisper large-v3 on the GPU

Ready, validated script: `scripts/transcribe_gpu.py` in this skill.

```bash
python scripts/transcribe_gpu.py --out-dir "/path/to/out" --base "event-name" \
  --prompt "Talk about X; names: Alice, Bob; terms: Deep Work, RAG" \
  --language en video1.mp4 video2.mp4
```

### Detect the environment — NEVER hardcode a path or a GPU

This skill runs on different machines (Windows and Linux). **Always detect;
if you cannot find something, ask the user** instead of guessing a path.

1. **Python interpreter with faster-whisper** — the `python` on PATH may not be
   the one with the packages. Test before launching a long job:
   ```bash
   python -c "import faster_whisper, sys; print('OK', sys.executable)"
   ```
   If it fails, look for other interpreters (Windows: `py -0p`, `where python`;
   Linux: `which -a python3`, venvs in `~/.venvs`, `~/miniconda3/envs`).
   Found one? **Record it in the agent's memory for this machine** (see below).
   Not found? Ask — do not install anything on your own.

2. **GPU and VRAM** — decides the `compute_type` and the expected speed:
   ```bash
   nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv
   ```
   | Free VRAM | Choice |
   |---|---|
   | ≥ 5 GB | `float16` (fastest) |
   | 2–5 GB | `int8_float16` (~1.9 GB) ← the script tries this first |
   | < 2 GB | free memory first; otherwise ask about CPU |

   No `nvidia-smi` (Mac/AMD/CPU-only): **ask before falling back to CPU** —
   large-v3 on CPU takes ~2 h+ per hour of audio.

3. **ffmpeg/ffprobe** — `which ffmpeg` (or, from Windows into WSL:
   `wsl -e bash -c "which ffmpeg"`). Needed for Step 0.

- Required packages: `faster-whisper nvidia-cublas-cu12 nvidia-cudnn-cu12`.
- The script already solves the classic Windows problem: `cublas64_12.dll not
  found` at encode time — it needs PATH plus a ctypes preload of the NVIDIA pip
  DLLs before the import (`os.add_dll_directory` alone is not enough).
- On a 4 GB card `float16` does NOT fit (needs ~4.5 GB); `int8_float16`
  (~1.9 GB) runs at **~4.3x realtime** (50 min ≈ 12 min), with `int8` as the
  fallback.
- **Busy GPU = crawling transcription**: with a browser downloading/playing
  video, speed dropped from 4.3x to 0.1x. Check `nvidia-smi` first; if VRAM is
  nearly full, warn the user and/or wait for downloads to finish.
- **The VRAM thief is rarely a single app**: it is the sum of dozens with
  hardware acceleration — chat clients (~720 MB), browser/WebView, an IDE,
  Docker Desktop, the GPU vendor overlay, messaging apps. Measured on the same
  audio and machine: **2.3x with everything open → 5.1x after closing** (more
  than 2x gain). Always worth asking the user whether those can be closed
  before a long job.
- **Ignore the first `[prog]` lines**: they start at ~0.3–0.8x (warm-up) and
  climb. Only trust the number after ~2 min; the final value comes in `[done]`.
- Sequence: first download/close video tabs (a photo-gallery site may keep the
  video LOOPING!), only then transcribe. If it already degraded, closing the
  tabs does NOT recover the live process (allocations stay pinned in WDDM
  shared memory) — kill and relaunch; parts already written are not lost.
- If the GPU fails outright: **ask before falling back to CPU** (the user may
  prefer to wait or close apps).

Quality (what actually moves the needle):
- Model: `small` hallucinates on live speech (loops of the same word);
  large-v3 eliminates them. Model > hardware for quality; the GPU only buys
  speed.
- `--prompt` (initial_prompt): pass the event title, proper nouns and expected
  jargon — it is the cheap lever for getting names right. **Side effect**: in
  silent/noisy stretches (start of the recording, pauses) Whisper may ECHO the
  prompt verbatim as if it were speech. Always grep the result for prompt
  phrases and remove those segments (renumber the SRT, regenerate the TXT).
- Always `vad_filter=True`, `beam_size=5`, explicit `language`.
- Accepts `.mp4` directly (PyAV decodes it) — no need to extract a WAV for
  small files (see Step 0 for large ones).
- Even large-v3 gets proper nouns wrong — recommend a review or run an LLM
  correction pass.
- Quick QA: scan the SRT in 30 s windows for repeated bigrams (degeneration) —
  if present, the audio has a bad stretch or the model slipped.

First run downloads the model (~3 GB, Hugging Face cache) — needs internet and
~80 s extra.

## Remote — YouTube

- **youtubetotranscript.com**: paste the YouTube URL, copy the transcript. For
  quick text without precise timestamps. No download, no GPU.
- Alternatives: YouTube's own "Show transcript" panel;
  `yt-dlp --write-auto-sub --skip-download <url>` when you need the `.vtt`.
- Limit: YouTube's automatic transcript has auto-caption quality (worse than
  large-v3). For the user's own talk, when it deserves care, download the
  video and run locally.

## Record the environment in memory (once per machine)

After detecting interpreter/GPU/ffmpeg, **save it in the agent's memory for
this machine** (e.g. a `reference`-type memory file: interpreter path, VRAM,
measured throughput, traps). **Read that memory before detecting again** — and
if something no longer matches (path moved, GPU replaced), update the file
instead of creating another.

Golden rule: **machine-specific fact → memory. Procedure → skill.** That is
how the skill keeps running on any PC, Windows or Linux.

## Before launching a long job: fail fast (an expensive lesson)

An earlier version of the script transcribed everything in memory and only
wrote at the end. **Any write error discovered late throws away hours of
GPU.** Once, `--out-dir` did not exist and 100 min of audio (~18 min of GPU)
were lost in the `open()` of the SRT.

The script now fixes this (`os.makedirs` + write test + input check before
loading the model, and incremental streaming to `.srt.partial`), but when
assembling ANY long pipeline, validate first:

- [ ] `--out-dir` exists **and is writable** (create it with `mkdir -p`)
- [ ] input files exist and are not empty/silent (Step 0)
- [ ] `--language` matches the actual audio
- [ ] enough free VRAM (otherwise ask to close apps)

If the process dies mid-way, look for the `.srt.partial` in the out-dir — it
holds everything transcribed so far.

## Standard post-processing (always run all three)

1. **Prompt-echo grep**: search the SRT for initial_prompt phrases; remove
   identical segments, renumber, regenerate the TXT (echo appears in
   silence/noise).
2. **Degeneration scan**: 30 s windows with a bigram repeated ≥ 8x = a
   hallucination loop. **It DOES happen on large-v3**, so always run:
   ```bash
   grep -v "^[0-9]*$" x.srt | grep -v -- "-->" | grep -v "^$" | uniq -c | sort -rn | head
   ```
   Signs that it is hallucination and not real speech: timestamps turning into
   artificial intervals of exactly 1.000 s, and the sentence **duplicated
   inside the same segment**. Repetition ≤ 4x is usually natural speech —
   check the context.

   **Fix (recover the text, do not discard the stretch):**
   1. `volumedetect` on the window: normal level (~−16 dB) = real speech is
      there, recoverable; ~−90 dB = truly silent, just remove it.
   2. Cut the window with margin on both sides (`-ss` X `-t` ~35 s) and
      re-transcribe **without `--prompt`** — the initial_prompt contributes to
      the loop.
   3. Replace the bad segments with the recovered text, **renumber the SRT**
      and regenerate the TXT. Keep a `.srt.bak` before overwriting.

   Real case: 9 segments (00:25:01–00:25:10) repeating the same sentence became
   1 correct segment; the recovered speech joined its neighbors perfectly.
3. **Sample read**: the beginning plus one stretch from the middle; note
   suspicious terms (wrong proper nouns) as a review to-do for the user.

## Partitioned recordings (several videos of the same session)

- Sort by the timestamps in the file names (`VID_YYYYMMDD_HHMMSS`); transcribe
  each part separately (the per-part SRT doubles as subtitles for that video).
- Build a unified transcript with a **global timeline**: each part's offset =
  (HHMMSS of the part − HHMMSS of part 1); mark the gaps without recording
  between parts. The result is a single navigable file, "the session
  transcript".
- If the process dies mid-way (OOM/thrash/kill): parts already on disk are not
  lost — relaunch only the remaining parts with a resume script (same
  numbering) and assemble the unified file from what already existed.

## Running in the background (10+ min jobs)

- Launch in the background with a log monitor (tail the log filtering
  `\[done|Error|Traceback`) plus a "dead man" timer (`sleep N` in the
  background) to re-evaluate even if the log goes quiet — a silent hang does
  not notify.
- Healthy throughput on a 4 GB card: ~4–5x realtime. If it drops below 1x,
  check `nvidia-smi`: another app is eating VRAM. Closing the app does NOT
  recover the already-degraded process (allocations pinned in shared memory) —
  kill it and use the resume.

## After transcribing

Hand the files (txt + srt) to wherever the user keeps their notes or knowledge
base (an Obsidian vault, a docs folder) and let them decide about committing
or syncing. Tell the user when the files are ready and which terms need a
review.
