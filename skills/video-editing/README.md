# video-editing

CLI video editing with ffmpeg + word-level captions via faster-whisper (GPU or CPU).

## Purpose

Battle-tested recipes for producing short-form interview cuts (Reels/Shorts/TikTok 9:16, LinkedIn 1:1 and 4:5) entirely from the command line — no GUI editor. The skill is machine-agnostic: GPU/encoder parameters are detected at runtime and machine facts are meant to live in the agent's memory, never in the skill.

## Features

- **Frame-accurate cuts + concat** — re-encode segments with identical params, concat without re-encode (cold open + take)
- **Word-level captions (CapCut style)** — `scripts/word_captions.py` (GPU) generates burned-in `.ass` + `.srt`; `scripts/word_captions_map.py` (CPU int8) transcribes the ORIGINAL once and derives captions for every cut via `--segments` (no re-transcription, no splice hallucinations)
- **Hook→content transition** — animated zoom punch-in (`zoompan` with per-frame easing), per-segment white flash, low-end whoosh (`assets/whoosh-lowend-260ms.wav`, generator in `scripts/make_whoosh.sh`), plus the taste calibration between "invisible" and "perceptible" versions
- **xfade catalog** — which transitions exist per ffmpeg version (43 in 4.4 vs 58 in 9.0), which ones read well in a human review and at what duration, the offset rule, and why synthesized SFX lost to recorded libraries
- **Format recipes** — 9:16 blurred-background pad, 1:1 and 4:5 LinkedIn reusing the 9:16 `.ass` via sed
- **Speaker-following 9:16 reframe** — `scripts/face_pan.py` crops full-frame onto whoever is talking, with hard cuts. No OpenCV, no ML: it measures per-frame brightness (`signalstats.YAVG`) of two mouth/chin ROIs and infers the speaker from the variation, with hysteresis so the cut doesn't flicker during silence. Ported from [clipify](https://github.com/louisedesadeleer/clipify) (MIT). Requires a static camera within the cut.
- **Platform delivery specs** — [`references/platform-specs.md`](references/platform-specs.md): bitrate/duration/file-size per platform, −14 LUFS normalization, and safe-zone tables with a `drawbox` QA command that paints the UI-occluded areas onto a frame. Safe-zone numbers are community-measured medians (no platform publishes pixel specs) — verify before campaign delivery.
- **Clip scoring rubric** — [`references/clip-scoring.md`](references/clip-scoring.md): pick *which* segment becomes a cut, scoring hook / standalone coherence / emotion / value density / payoff, plus cheap mechanical pre-filters (audio peaks, laughter, awkward pauses). Adapted from [claude-shorts](https://github.com/AgriciDaniel/claude-shorts) (MIT).
- **Color grading & correction** — [`references/color-grading.md`](references/color-grading.md): chain order, four measured grade recipes, iPhone HLG→SDR tonemap, and `.cube` LUT blending. Leads with *when not to grade*. Includes a skin-tone drift test measured across three skin tones, which found that the contrast **curve** — not saturation — is what distorts skin, and that it distorts light and dark skin in opposite directions.
- **GPU/NVENC auto-detection** — `scripts/gpu_probe.py` asks `nvidia-smi` and ffmpeg what exists *on this machine* and emits the right encode args. Never hardcode card params: different cards want different presets and codecs. Empirically tests B-frame support instead of trusting a spec table (which caught a wrong assumption: TU116 *does* support HEVC B-frames). Set `FFMPEG_BIN` to point the scripts at a specific build.
- **Delivery QA** — the NVENC `yuv444p` trap (files that players and platforms refuse) and the one-line `ffprobe` check that catches it
- **Hard-earned rules** — `ffmpeg -nostdin` always, scripts via file (never pipe), unique temp names per parallel agent, phone-video rotation traps, visual QA by frame extraction, orchestration of long encodes

## Example

[`examples/interview-clip-pipeline/`](examples/interview-clip-pipeline/) — a parameterized version of the production pipeline (probe → transcribe once → cut → transition → burn captions → QA), including HDR→SDR tonemap (hable) for iPhone HLG footage and a blur-pad variant for low-res horizontal sources. Set the variables at the top of each script; treat as reference, not plug-and-play.

## Requirements

- ffmpeg with libass (a Linux/WSL build for filters; on WSL, Windows fonts via `fontsdir=/mnt/c/Windows/Fonts`)
- For NVENC encodes: a native ffmpeg with NVENC (on Windows hosts NVENC is not available inside WSL2 — GPU-PV only exposes CUDA compute); set `FFMPEG_BIN`
- Python + faster-whisper (CUDA for the GPU path; CPU int8 fallback works)
- See the [media-transcription](../media-transcription/) skill for the transcription setup

## Credits

Recipes and rules are original (learned in production). Two components are ported from other MIT-licensed skills, noted inline above:

- [clipify](https://github.com/louisedesadeleer/clipify) by Louise de Sadeleer — the ROI-brightness speaker-detection approach behind `face_pan.py`
- [claude-shorts](https://github.com/AgriciDaniel/claude-shorts) by AgriciDaniel — platform export specs, safe zones, and the segment scoring rubric

## See Also

- [SKILL.md](SKILL.md) — Full skill (recipes, golden rules, transition research)
