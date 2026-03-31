# Audio Handling -- Transcription & TTS

A practical guide to receiving, transcribing, and responding with audio in OpenClaw deployments.

---

## 1. Audio Reception Flow

When an agent receives audio (ogg/voice message via any channel -- Discord, Slack, WhatsApp, Telegram):

1. **React immediately** with a listening emoji (e.g., `ear`) before processing -- gives the user visual feedback that their audio was received
2. **Download the file** -- OpenClaw auto-downloads inbound media to `media/inbound/`
3. **Transcribe locally** with Whisper (never send audio to external APIs for privacy)
4. **Use the transcription** as context for the response
5. **Save the transcription** in an organized directory structure
6. **Delete the original audio file** after successful transcription (privacy + storage)

### Error Handling

- **Inaudible audio:** Inform the user honestly and ask for a shorter, clearer re-recording
- **Uncertain transcription:** Confirm your interpretation with the user before acting on it
- **Transcription failure:** Acknowledge explicitly and ask for resubmission -- never guess content
- **Reply format:** If the response contains code, commands, or structured data, always reply in **text** regardless of input format

---

## 2. Whisper Configuration

Two Whisper installations are commonly available:

| Installation | Command | Speed | Quality |
|-------------|---------|-------|---------|
| **openai-whisper** | `whisper` (CLI) | Slower | More accurate |
| **faster-whisper** | Python library | ~3x faster | Comparable | **Recommended** |

### Recommended Command

Add this to your agent's `TOOLS.md` or skill file:

```bash
whisper /path/to/audio.ogg --model small --language <code> --output_format txt --output_dir /tmp
```

### Model Selection Rules

| Model | Use When | CPU Time (~1 min audio) |
|-------|----------|------------------------|
| `tiny` | Quick tests, low-quality acceptable | ~3 seconds |
| `small` | **Production default** | ~10 seconds |
| `medium` | Never on CPU-only servers | ~60+ seconds (blocks lane) |
| `large` | Never on CPU-only servers | Minutes (blocks lane) |

**Critical:** On CPU-only servers (no GPU), always use `--model small`. Medium and large models are too slow and will block the agent's processing lane for minutes, making the bot unresponsive.

### Language Detection

| Scenario | Flag | Notes |
|----------|------|-------|
| Known language | `--language <code>` | Use ISO 639-1 code (e.g., `en`, `pt`, `es`, `fr`) |
| Unknown language | Omit `--language` | Auto-detection works but can produce errors |
| Multilingual audio | Omit `--language` | Let Whisper detect per-segment |

**Tip:** When the user's primary language is known, always specify `--language` to avoid auto-detection errors -- especially for short audio clips where detection is unreliable.

### Performance Considerations

- **Sequential processing:** Multiple audio messages must be processed one at a time (CPU-bound). Do not run parallel transcriptions.
- **Background mode:** For audio longer than 30 seconds, consider running Whisper via `exec` with `background: true` to avoid blocking.
- **Temp files:** Whisper outputs to `--output_dir`. Clean up temp files after copying the transcription to the organized directory.

---

## 3. Transcription Organization

Save transcriptions in a structured directory organized by date:

```
workspace/transcriptions/
├── 2026-03-15/
│   ├── 0930-config-discord.txt
│   ├── 1200-lunch-reminder.txt
│   └── 1415-afternoon-briefing.txt
├── 2026-03-16/
│   ├── 0845-morning-standup.txt
│   └── 1630-project-update.txt
└── ...
```

### Naming Convention

```
HHMM-<summary>.txt
```

| Component | Rules |
|-----------|-------|
| `HHMM` | 24-hour time of the audio message |
| `<summary>` | 2-4 words describing the content |
| Format | Lowercase, hyphens between words |
| Extension | Always `.txt` |

**Examples:**
- `0930-config-discord.txt`
- `1415-afternoon-briefing.txt`
- `2200-travel-plans.txt`

### Rules

- Create directories with `mkdir -p` as needed
- **Never** save transcriptions as `UUID.txt` in the workspace root
- **Never** save to `/tmp/` -- files are lost on restart (systemd `PrivateTmp`)
- Transcriptions go in `workspace/transcriptions/`, **not** in `media/`
- Transcriptions ARE versioned in git (they live inside `workspace/`)
- Original audio files are NOT versioned (excluded via `.gitignore`)

---

## 4. TTS -- Text-to-Speech Responses

### When to Use Audio vs Text

| Use Text (default) | Use Audio |
|--------------------|-----------|
| Normal conversation | User explicitly requests audio |
| Code snippets or commands | Storytelling or summaries |
| Lists, URLs, structured data | Long-form narrative content |
| Content the user needs to copy | "Read this to me" requests |
| Technical explanations | Casual briefings when hands-free |

**Default is always text.** Audio responses are opt-in, not automatic.

### Available TTS Providers

| Provider | Quality | Cost | Setup |
|----------|---------|------|-------|
| **ElevenLabs** | Best (most natural) | Per-character pricing | API key in `.env` |
| **OpenAI TTS** | Good | Per-character pricing | API key in `.env` |
| **Edge TTS** | Reasonable | Free | No API key needed |

### Configuration

OpenClaw manages TTS via built-in commands:

| Command | Purpose |
|---------|---------|
| `tts.enable` | Enable TTS capability |
| `tts.setProvider` | Set the active TTS provider |
| `tts.convert` | Convert text to speech |

### TTS Workflow

1. Agent generates text response
2. Agent calls `tts` tool with the response text
3. OpenClaw converts and delivers the audio to the active channel
4. Agent replies with `NO_REPLY` to prevent a duplicate text message

**Critical:** always send `NO_REPLY` after TTS. Without it, the user receives both the audio AND a text version of the same content.

### Voice Selection Tips

- Match the voice to the agent's persona (gender, tone, accent)
- Test multiple voices before committing to one
- ElevenLabs supports custom voice cloning for personalized agents
- Edge TTS has a wide selection of free voices across many languages

---

## 5. Complete Audio Skill Example

Here is a template for an audio handling skill (`SKILL.md`):

```markdown
# Audio Transcription Skill

## Description
Handles incoming voice messages: transcription, organization, and response.

## Triggers
- When an audio/voice message is received on any channel

## Workflow
1. React with ear emoji for immediate feedback
2. Locate the downloaded audio file in media/inbound/
3. Run: whisper <file> --model small --language <user-lang> --output_format txt --output_dir /tmp
4. Read the transcription from /tmp/<filename>.txt
5. Save to workspace/transcriptions/YYYY-MM-DD/HHMM-<summary>.txt
6. Delete the original audio file from media/inbound/
7. Clean up /tmp/<filename>.txt
8. Use the transcription text as context for generating a response

## Guardrails
- Never use medium or large Whisper models on CPU-only servers
- Never send audio to external transcription APIs
- Always confirm uncertain transcriptions before acting
- Always delete original audio after successful transcription
- Process multiple audios sequentially (CPU-bound)
```

---

## 6. Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| Bot unresponsive after audio | Whisper with medium/large model blocking lane | Switch to `--model small`, use background exec for long audio |
| Garbled transcription | Wrong language auto-detected | Specify `--language <code>` explicitly |
| Missing transcription file | Saved to `/tmp/` and lost on restart | Always save to `workspace/transcriptions/` |
| Duplicate response (text + audio) | Missing `NO_REPLY` after TTS | Always send `NO_REPLY` after using TTS tool |
| Slow transcription (>30s) | Long audio clip on CPU | Use background exec mode, inform user of delay |
| "File not found" error | Audio not yet downloaded | Check `media/inbound/` -- OpenClaw auto-downloads, may take a moment |
