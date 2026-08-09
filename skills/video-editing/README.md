# video-editing

CLI video editing with ffmpeg (WSL) + word-level captions via faster-whisper GPU/CPU. Skill content in PT-BR.

## Purpose

Battle-tested recipes for producing short-form interview cuts (Reels/Shorts/TikTok 9:16, LinkedIn 1:1) entirely from the command line — no GUI editor.

## Features

- **Frame-accurate cuts + concat** — re-encode segments with identical params, concat without re-encode (cold open + take)
- **Word-level captions (CapCut style)** — `scripts/word_captions.py` (GPU) generates burned-in `.ass` + `.srt`; `scripts/word_captions_map.py` transcribes the ORIGINAL once and derives captions for every cut via `--segments` (no re-transcription, no splice hallucinations)
- **Hook→content transition** — animated zoom punch-in (zoompan with per-frame easing), per-segment white flash, low-end whoosh (`assets/whoosh-lowend-260ms.wav`, generator in `scripts/make_whoosh.sh`)
- **Format recipes** — 9:16 blurred-background pad, 1:1 LinkedIn reusing the 9:16 `.ass` via sed
- **Hard-earned rules** — `ffmpeg -nostdin` always, scripts via file (never pipe), phone-video rotation traps, visual QA by frame extraction

## Real-world examples

[`examples/tdc-cortes-2026-08/`](examples/tdc-cortes-2026-08/) — the actual scripts from a production session (probe → transcribe once → cut → transition → burn captions → QA), including HDR→SDR tonemap (hable) for iPhone 4K HLG footage. Paths are machine-specific; treat as reference, not plug-and-play.

## Requirements

- ffmpeg (in this setup: WSL Ubuntu) with libass; Windows fonts via `fontsdir`
- Python + faster-whisper (CUDA for GPU path; CPU int8 fallback works)
- See the [media-transcription](../media-transcription/) skill for the transcription setup

## See Also

- [SKILL.md](SKILL.md) — Full skill (recipes, golden rules, transition research)
