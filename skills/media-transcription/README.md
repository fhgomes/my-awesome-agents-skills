# media-transcription

Transcribe audio/video to text and subtitles — local faster-whisper large-v3 on GPU, or remote for YouTube. Skill content in PT-BR.

## Purpose

Reliable transcription of talks, mentoring sessions, and interviews with the quality lever that actually matters: the large-v3 model (small models loop/hallucinate on live speech).

## Features

- **Ready script** — `scripts/transcribe_gpu.py`: faster-whisper large-v3, `int8_float16` on a 4 GB GPU (~4.3x realtime), solves the Windows `cublas64_12.dll` preload trap
- **Quality playbook** — `initial_prompt` for proper nouns/jargon, VAD filter, beam 5, prompt-echo cleanup, degeneration scan
- **Remote path** — youtubetotranscript.com / `yt-dlp --write-auto-sub` when the video is already on YouTube
- **Ops notes** — GPU contention detection (nvidia-smi), background runs with resume, partitioned recordings with global timeline

## Quick Start

```bash
python scripts/transcribe_gpu.py --out-dir "C:\out" --base "event-name" \
  --prompt "Talk about X; names: Alice, Bob; terms: RAG, Deep Work" \
  video1.mp4 video2.mp4
```

## See Also

- [SKILL.md](SKILL.md) — Full skill (decision table, QA passes, background ops)
- [video-editing](../video-editing/) — word-level captions and burning for short-form cuts
