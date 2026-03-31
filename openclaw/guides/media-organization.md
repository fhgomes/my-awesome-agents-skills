# Media Organization

A practical guide to organizing media files, transcriptions, and generated content in OpenClaw deployments.

---

## 1. Default Directory Structure

```
~/.openclaw/media/
├── inbound/               # Received media (auto-managed by OpenClaw)
│   ├── discord/           # From Discord channels
│   ├── slack/             # From Slack channels
│   └── whatsapp/          # From WhatsApp
├── generated/
│   ├── images/            # AI-generated images
│   ├── audio/             # Generated audio (TTS output)
│   └── video/             # Generated video content
└── archive/               # Old media (>30 days, optional cleanup)
```

### Inbound Media

OpenClaw automatically downloads received media (images, audio, video, documents) to `media/inbound/`. This includes:

- Voice messages (`.ogg`, `.opus`)
- Photos and images (`.jpg`, `.png`, `.gif`, `.webp`)
- Videos (`.mp4`, `.webm`)
- Documents (`.pdf`, `.docx`, etc.)

The agent accesses these files via their local filesystem path. After processing (e.g., transcribing audio), **delete the original file** to save storage and protect privacy.

### Generated Media

When the agent generates media (TTS audio, image generation, etc.), save to the appropriate subdirectory under `generated/`:

```
media/generated/images/briefing-chart-2026-03-15.png
media/generated/audio/morning-briefing-2026-03-15.mp3
```

---

## 2. File Naming Rules

### General Principles

| Rule | Example | Anti-Pattern |
|------|---------|-------------|
| Use descriptive names | `briefing-2026-03-06.mp3` | `output.mp3` |
| Include date or context | `sprint-review-chart-03-15.png` | `chart.png` |
| Lowercase with hyphens | `daily-standup-notes.txt` | `Daily_Standup Notes.txt` |
| Include file extension | `report.pdf` | `report` |

### Never Save to /tmp/

On servers running OpenClaw via systemd, `/tmp/` is typically a private mount (`PrivateTmp=true`). Files saved there:

- Are invisible to other services
- Are **deleted on service restart**
- Cannot be accessed by the user directly

Always save important files to the appropriate directory under `~/.openclaw/`.

### Naming Patterns by Type

| Type | Pattern | Example |
|------|---------|---------|
| Audio transcriptions | `HHMM-<summary>.txt` | `0930-config-discord.txt` |
| Generated images | `<context>-<date>.png` | `sprint-chart-2026-03-15.png` |
| TTS output | `<context>-<date>.mp3` | `morning-briefing-2026-03-15.mp3` |
| Screenshots | `<site>-<date>.png` | `jira-board-2026-03-15.png` |
| Reports | `<type>-<date>.pdf` | `weekly-report-2026-03-15.pdf` |

---

## 3. Audio Transcription Storage

Transcriptions have their own directory structure, separate from media:

```
~/.openclaw/workspace/transcriptions/
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
workspace/transcriptions/YYYY-MM-DD/HHMM-<summary>.txt
```

| Component | Rules |
|-----------|-------|
| Directory | Date in ISO format (`YYYY-MM-DD`) |
| Time | 24-hour format (`HHMM`) |
| Summary | 2-4 words, lowercase, hyphens |
| Extension | Always `.txt` |

### Rules

- Create directories with `mkdir -p` as needed
- Never save as `UUID.txt` or random filenames in the workspace root
- Transcriptions go in `workspace/transcriptions/`, **not** in `media/`
- One file per audio message (don't concatenate multiple transcriptions)

---

## 4. Backup Rules

### What IS Versioned (in git)

- **Transcriptions** (`workspace/transcriptions/`) -- text files, small, valuable
- **Workspace scripts** (`workspace/*.py`, `workspace/*.sh`) -- automation code
- **Memory files** (`memory/*.md`) -- agent knowledge
- **Skills** (`skills/`) -- skill definitions

### What is NOT Versioned (excluded via .gitignore)

- **Media files** (`media/`) -- too large for git, ephemeral
- **Browser data** (`browser/`) -- session cookies, cache
- **Session files** (`agents/*/sessions/`) -- conversation history, can be MBs
- **SQLite databases** (`*.sqlite`) -- regenerable indexes

### Media Backup Options

Since media files are excluded from git, consider separate backup strategies:

| Method | Best For | Setup |
|--------|----------|-------|
| **rsync** | Simple server-to-server backup | `rsync -avz media/ backup-server:/media/` |
| **S3 sync** | Cloud backup with lifecycle policies | `aws s3 sync media/ s3://bucket/media/` |
| **Cleanup cron** | Free storage by archiving old media | Move files >30 days to `archive/` or delete |
| **No backup** | Ephemeral media (voice messages, temp images) | Delete after processing |

### Recommended Cleanup Cron

```bash
# Root crontab -- archive media older than 30 days
0 3 * * 0 find ~/.openclaw/media/inbound/ -type f -mtime +30 -delete
0 3 * * 0 find ~/.openclaw/media/generated/ -type f -mtime +30 -exec mv {} ~/.openclaw/media/archive/ \;
```

---

## 5. Storage Monitoring

Media directories can grow silently. Monitor regularly:

```bash
# Check media directory size
du -sh ~/.openclaw/media/

# Check by subdirectory
du -sh ~/.openclaw/media/*/

# Find large files (>10MB)
find ~/.openclaw/media/ -type f -size +10M -ls

# Find old files (>30 days)
find ~/.openclaw/media/ -type f -mtime +30 | wc -l

# Check transcription directory size
du -sh ~/.openclaw/workspace/transcriptions/
```

### Storage Alerts

Add a check to your agent's heartbeat or a periodic cron:

```
Check if media/ directory exceeds 1GB.
If so, notify the owner and suggest running cleanup.
```

---

## 6. Privacy Considerations

### Audio Files

- **Always delete** original audio files after successful transcription
- Audio contains biometric data (voice) -- treat with care
- Never send audio to external transcription services without user consent
- Transcriptions (text) are less sensitive than audio but still contain private content

### Images and Screenshots

- Browser screenshots may contain sensitive information (passwords, tokens visible on screen)
- Delete screenshots after the agent has processed them
- Never include screenshots in automated reports without review

### General

- Media files in `inbound/` may contain anything the user sends -- treat as potentially sensitive
- The `archive/` directory should have restricted permissions (`chmod 700`)
- Consider encrypting archived media if the server stores sensitive user data
