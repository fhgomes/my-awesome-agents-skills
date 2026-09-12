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
   | Free VRAM | `compute_type` | What it unlocks |
   |---|---|---|
   | ≥ 10 GB | `float16` | Batched inference and a bigger `beam_size`; several hours of audio in one job |
   | 5–10 GB | `float16` | Comfortable large-v3, no tricks needed |
   | 2–5 GB | `int8_float16` (~1.9 GB) | What the script tries first; ~4x realtime |
   | < 2 GB | free memory first | Otherwise ask about CPU |

   No `nvidia-smi` (Mac/AMD/CPU-only): **ask before falling back to CPU** —
   large-v3 on CPU takes ~2 h+ per hour of audio.

   **The defaults in this skill are tuned for a small card (~4 GB), because that
   is where the traps live.** On a larger GPU you are leaving speed and quality
   on the table by keeping them. Worth raising, in this order:

   - `compute_type="float16"` — the single biggest win over `int8_float16`;
     fewer numerical artifacts on proper nouns and accented speech.
   - `batched=True` with a `batch_size` (faster-whisper ≥ 1.0, via
     `BatchedInferencePipeline`) — several times faster on long files; each
     batched segment needs its own VRAM, so start at 8 and raise while it fits.
   - `beam_size` 5 → 8–10 — modest accuracy gain for real compute; worth it on
     hard audio (crosstalk, accents, background noise), not on clean speech.
   - One job per GPU regardless of size. Two processes on the same card thrash
     and both crawl, whatever the VRAM.

   Apple Silicon: faster-whisper has no Metal backend. Either run on CPU with
   `compute_type="int8"` (workable on M-series for short files) or use a
   MLX-based Whisper port, which is a different tool, not a flag of this one.

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
- Even large-v3 gets proper nouns wrong, and it spells the wrong guess
  plausibly — see "The second pass: read it back in context" below. Never hand
  over a transcript without it.
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
3. **Sample read**: the beginning plus one stretch from the middle, to confirm
   the file is coherent before investing more time. This is a smoke test, not
   the review — the real one is "The second pass: read it back in context".

## Synthetic timestamps: correct text, unusable timing

A distinct failure from the hallucination loop above, and more dangerous
because **the text is right**. On a long recording the VAD can lose its
reference and the model falls back to slicing the rest of the file at a fixed
interval. You get a complete, accurate transcript whose timestamps are fiction.

Nothing in the text looks wrong. Reading the first blocks does not reveal it
either — the real timing usually survives the first minute or two, so a
spot-check at the top passes. The only reliable detection is statistical:

```bash
python - "$SRT" <<'EOF'
import re, sys, collections
t = open(sys.argv[1], encoding='utf-8').read()
d = []
for m in re.finditer(r'(\d\d):(\d\d):(\d\d),(\d\d\d) --> (\d\d):(\d\d):(\d\d),(\d\d\d)', t):
    g = [int(x) for x in m.groups()]
    a = g[0]*3600 + g[1]*60 + g[2] + g[3]/1000
    b = g[4]*3600 + g[5]*60 + g[6] + g[7]/1000
    d.append(round(b - a, 3))
c = collections.Counter(d)
top, n = c.most_common(1)[0]
print(f'blocks={len(d)} most common={top}s x{n} ({100*n//len(d)}%)')
print('SYNTHETIC' if n > len(d) * 0.5 else 'healthy')
EOF
```

Healthy speech gives a spread of durations (roughly 0.3–30 s, no single value
dominating). One value covering more than half the blocks means the timing is
synthetic from that point on. A real case: 1204 of 1250 blocks at exactly
2.000 s, real timing only up to 00:01:11 of a 45-minute file.

**Fix — regenerate the timing, keep the text.** Re-running the same transcriber
reproduces the problem. Use a word-level pass instead (in this repo,
`video-editing/scripts/word_captions.py`), which forces per-word timestamps and
does not depend on the same segmentation:

```bash
python ../video-editing/scripts/word_captions.py "$AUDIO"   --out-dir "$OUT" --base "$BASE" --language "$LANG"
```

Validate the output with the same statistic before trusting it.

**Remapping planned cuts.** If cut points were already chosen against the bad
SRT, do not shift them by hand. `scripts/remap_timestamps.py` re-locates each
one by **text anchor**: it reads the phrase around the old timestamp, finds
that phrase in the word-level SRT, and returns the real time.

```bash
python scripts/remap_timestamps.py --synthetic bad.srt --words good.srt   --cuts cuts.json --out remapped.json
```

Two things to expect. The drift is usually systematic, not random — a
consistent median offset across every cut is a good sign the remap is sound;
scattered offsets mean something else is wrong. And anchors fail on short or
generic phrases: those fall back to the median offset and **must be confirmed
by ear** before they reach an encoder. The script marks which is which.

Cheap prevention on any recording longer than ~20 minutes: run the statistic
right after transcribing, before anyone plans a cut on those numbers.

## The second pass: read it back in context

The three post-processing passes above are mechanical — they catch echo, loops
and broken timing. None of them catches the most common defect in a finished
transcript: **a word the model heard wrong but spelled plausibly.** ASR does not
mark those as uncertain. They arrive looking exactly like every correct word
around them, and they survive all the way into a quote or a burned caption
unless somebody reads the text as text.

Do this pass yourself before handing the files over. It is not optional polish;
it is where proper nouns get fixed.

**1. Proper nouns come from the END of the recording, not the beginning.**

In an interview the host introduces the guest at the top, fast and often over
background noise — exactly the conditions where ASR guesses. The guest spells
their own name near the end, answering "where can people find you?", slowly and
deliberately. The correct spelling is almost always down there.

Same for the organization: an acronym mangled at minute one is usually said
clearly later, or appears next to a URL or a handle the speaker reads out.

So: read the last minute first, build the name list, then go back to the top
and fix every earlier occurrence. Doing it in the other order means propagating
the wrong spelling.

**2. Let the domain decide between homophones.**

The model picks whichever spelling is more frequent in general text, not in
*this* conversation. A talk about software design gets "boundary context" where
the speaker said "bounded context" — the DDD term. A distributed-systems talk
gets "even driving" for "event-driven". Both are real English; only one exists
in the domain.

Grep for the terms of art you expect from the subject. When something reads
slightly off in a technical sentence, it usually is.

**3. Numbers, versions and units are worth a targeted check.**

They are short, unstressed and easy to mishear, and an error in one changes the
meaning of the sentence instead of just looking odd. Scan every digit against
what the sentence is claiming.

**4. Decide per item: fix, flag, or leave.**

- **Fix** what the context proves: a name the speaker spells later, a term of
  art, a version number that contradicts the sentence.
- **Flag** what you cannot prove, and hand the list to the user with the
  timestamp. A guessed spelling in a published quote is worse than a question.
- **Leave** disfluency alone. Repeated words, false starts and filler are how
  the person spoke; cleaning them turns a transcript into a paraphrase. Only
  strip them when producing a quote for publication, and say that you did.

**5. Apply every correction to the SRT and the TXT.**

They are generated separately, so a fix in one leaves the other wrong — and the
SRT is what gets burned into video. Change both, keep a `.bak`, and re-run the
degeneration grep afterwards to confirm nothing was broken by the edit.

Handing this pass to a second model works well (it is reading, not guessing at
audio), but give it the domain and the name list, and require it to return a
diff rather than a rewritten file. A model asked to "improve" a transcript will
silently smooth the speech, which is the one thing this pass must not do.

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
