# media-transcription

Transcribe audio/video to text and subtitles — local faster-whisper large-v3 on GPU, or remote for YouTube.

## Purpose

Reliable transcription of talks, mentoring sessions, and interviews with the quality lever that actually matters: the large-v3 model (small models loop/hallucinate on live speech). The skill is machine-agnostic: it detects the interpreter, GPU and ffmpeg at runtime and tells the agent to store machine facts in memory, not in the skill.

## Features

- **Ready script** — `scripts/transcribe_gpu.py`: faster-whisper large-v3, `int8_float16` on a 4 GB GPU (~4.3x realtime) with `int8` fallback, solves the Windows `cublas64_12.dll` preload trap, fails fast on unwritable out-dir/missing inputs, and streams to `.srt.partial` so a crash never loses work
- **Step 0** — extract 16 kHz mono WAV for large videos (~74x smaller), check duration/level, detect the language on a sample before spending GPU time
- **Quality playbook** — `initial_prompt` for proper nouns/jargon, VAD filter, beam 5, prompt-echo cleanup, degeneration scan with a recovery procedure (it happens on large-v3 too)
- **Remote path** — youtubetotranscript.com / `yt-dlp --write-auto-sub` when the video is already on YouTube
- **Ops notes** — GPU contention detection (`nvidia-smi`), the many-small-apps VRAM thief, warm-up readings to ignore, background runs with resume, partitioned recordings with a global timeline

## Quick Start

```bash
python scripts/transcribe_gpu.py --out-dir "/path/to/out" --base "event-name" \
  --prompt "Talk about X; names: Alice, Bob; terms: RAG, Deep Work" \
  --language en video1.mp4 video2.mp4
```

## See Also

- [SKILL.md](SKILL.md) — Full skill (decision table, environment detection, QA passes, background ops)
- [video-editing](../video-editing/) — word-level captions and burning for short-form cuts
