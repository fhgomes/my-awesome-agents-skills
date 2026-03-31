# Tools & Skills Reference

A comprehensive guide to OpenClaw's built-in tools, the web research hierarchy, and the skills system.

---

## 1. Native OpenClaw Tools

### Communication & Channels

| Tool | Description |
|------|-------------|
| **message** | Channel operations (Discord/Slack/WhatsApp): send, read, edit, delete, react, thread-create, pin, member-info, channel-list, search, poll, moderation, and more. |
| **tts** | Text-to-speech. Auto-delivers audio to the active channel. **Important:** reply with `NO_REPLY` after using TTS to avoid sending a duplicate text message. |

### Web & Research

| Tool | Description |
|------|-------------|
| **web_fetch** | HTTP fetch with readability extraction. Fast, no API key needed, but **static HTML only**. Fails on SPAs, bot-protected sites (Cloudflare 403), and JS-rendered content. |
| **browser** | Headless Chrome via Playwright. Full JavaScript rendering, page interaction, screenshots, and DOM snapshots. Config: `browser.headless: true`, `browser.noSandbox: true` (for headless servers). |
| **web_search** | AI-powered web search (supports Brave, Perplexity, Gemini, Grok, Kimi). Requires an API key in `.env`. |

### Execution & Automation

| Tool | Description |
|------|-------------|
| **exec** | Execute shell commands. Supports background mode (`backgroundMs`, `notifyOnExit`, `timeoutSec`). **Critical:** long-running commands (Docker builds, compilation, large downloads) MUST use background mode -- otherwise they block the processing lane. |
| **cron** | Manage scheduled jobs. Two payload types: `systemEvent` (injects into main session) and `agentTurn` (creates isolated session). Three schedule types: `at`, `every`, `cron`. |

### Inter-Agent Communication

| Tool | Description |
|------|-------------|
| **sessions_send** | Send a message to another agent's session. |
| **sessions_spawn** | Create a new isolated session for an agent with a specific prompt. |
| **sessions_list** | List active agent sessions and their status. |

### Media & Analysis

| Tool | Description |
|------|-------------|
| **image** | Analyze images with a vision model. Use only when the image is NOT already present in the user's message (OpenClaw auto-includes inline images). |
| **pdf** | PDF analysis -- native rendering or text extraction fallback. |
| **canvas** | Canvas control: render HTML, navigate, evaluate JavaScript. |

### Memory & Search

| Tool | Description |
|------|-------------|
| **memory_search** | Semantic search over workspace memory files via local embeddings (Ollama). Can be replaced by external knowledge bases for cross-agent search. |

### Devices

| Tool | Description |
|------|-------------|
| **nodes** | Control paired devices (Android, iOS, macOS) via the OpenClaw gateway. |

---

## 2. Web Research Hierarchy

**Always follow this order when fetching web content.** Escalate only when the current method fails.

### Step 1: web_fetch (try first)

Fast, free, no API key. Works for static HTML pages, documentation, APIs, and RSS feeds.

**Fails on:**
- Single-page applications (React, Vue, Angular)
- Bot-protected sites (Cloudflare 403, CAPTCHA)
- Pages that require JavaScript to render content
- Sites that block non-browser User-Agents

### Step 2: browser (when web_fetch fails)

Full headless Chrome via Playwright. Renders JavaScript, handles redirects, executes interactions.

```
browser navigate <url>
browser snapshot          # returns page text content
browser screenshot        # returns visual screenshot
browser click <selector>  # interact with page elements
browser type <selector> <text>
```

**Escalation rule:** after **2 consecutive same-type web_fetch failures** on a URL (403, empty body, JS-required), switch to browser immediately. Do not retry web_fetch.

**Critical:** never tell the user "I can't access the web." The browser tool can render anything Chrome can render. If browser also fails, inform the user honestly about the specific error.

### Step 3: web_search (for general queries)

AI-powered search when you need to discover URLs rather than fetch a known page. Requires an API key.

**Alternative without API key:** use browser to navigate to a search engine, then snapshot the results page.

### Anti-Loop Rules

- Never loop `web_fetch` on sites that already returned 403 or empty content
- Never retry the same tool more than 2 times with the same parameters
- If both web_fetch and browser fail on the same URL, report the failure and suggest alternatives
- JS-heavy sites (dashboards, SPAs) should go directly to browser -- skip web_fetch entirely if you know the site requires JavaScript

---

## 3. Exec Tool — Background Mode

Long-running operations **must** run in background to avoid blocking the agent's processing lane. A blocked lane means the bot becomes unresponsive to all messages.

### Configuration

```json
{
  "tools": {
    "exec": {
      "backgroundMs": 5000,
      "notifyOnExit": true,
      "timeoutSec": 1800
    }
  }
}
```

| Setting | Description |
|---------|-------------|
| `backgroundMs` | Automatically backgrounds commands that run longer than this (ms). Recommended: 5000. |
| `notifyOnExit` | Agent receives a notification when the background command completes. |
| `timeoutSec` | Maximum execution time before the command is killed. Default: 1800 (30 min). |

### What Must Run in Background

- Docker builds (`docker build`, `docker compose up`)
- Compilation (`gradle`, `mvn`, `cargo build`, `npm run build`)
- Large file operations (`rsync`, bulk downloads)
- Database migrations
- Any command expected to take more than 5 seconds

### What Can Run Synchronously

- Quick reads (`cat`, `ls`, `grep`, `git status`)
- Short API calls (`curl` to fast endpoints)
- File writes and edits
- Process management (`systemctl status`, `docker ps`)

---

## 4. Browser Tool — Headless Chrome

### Setup

```json
{
  "tools": {
    "browser": {
      "headless": true,
      "noSandbox": true
    }
  }
}
```

`noSandbox: true` is required on servers without a display server (most production deployments).

### Commands

| Command | Description |
|---------|-------------|
| `browser navigate <url>` | Load a URL in the browser |
| `browser snapshot` | Extract readable text content from the current page |
| `browser screenshot` | Take a visual screenshot (returns image) |
| `browser click <selector>` | Click an element (CSS selector or text) |
| `browser type <selector> <text>` | Type text into an input field |

### Best Practices

- Always `navigate` before `snapshot` or `screenshot`
- Use `snapshot` for text extraction (faster, lighter on context)
- Use `screenshot` only when visual layout matters (charts, diagrams, UI bugs)
- For form filling: `navigate` → `type` → `click` (submit) → `snapshot` (result)
- Close long-running browser sessions to free resources

---

## 5. Skills System

Skills are modular capabilities that an agent loads on-demand. When a task activates a skill, the agent reads the skill's `SKILL.md` file for instructions, workflows, and guardrails.

### Skill Directory Structure

```
~/.openclaw/skills/
├── <skill-name>/
│   ├── SKILL.md         # Instructions, triggers, workflow, guardrails
│   ├── scripts/         # Helper scripts (optional)
│   └── templates/       # Templates used by the skill (optional)
```

### Installing Skills

**From ClawHub marketplace:**
```bash
clawhub search <name>
clawhub install <name>
```

**Manual installation:**
1. Create `~/.openclaw/skills/<name>/SKILL.md`
2. Define a clear `<description>` section so the agent knows when to activate
3. Include triggers, required environment variables, workflow steps, and guardrails

### Writing a Good SKILL.md

A skill file should be self-contained. The agent reads it cold (no prior context about the skill), so include everything it needs:

```markdown
# <Skill Name>

## Description
<What this skill does and when to activate it>

## Triggers
- When the user asks about [topic]
- When [condition] is detected

## Prerequisites
- Environment variable: `API_KEY_NAME` (required)
- Script: `scripts/helper.sh` (included)

## Workflow
1. Step one...
2. Step two...
3. Step three...

## Guardrails
- Never [dangerous action]
- Always [safety measure]
- Rate limit: [constraint]
```

### Building Helper Scripts for Integrations

For integrations that need API access beyond what native tools provide:

1. Place scripts in the skill directory or the main agent's workspace
2. Call via the `exec` tool with background mode for long operations
3. Handle authentication via environment variables in `.env` (never hardcode tokens)
4. Respect rate limits of external APIs
5. Return structured output (JSON preferred) so the agent can parse results reliably

**Example pattern:**
```bash
#!/bin/bash
# ~/.openclaw/skills/my-integration/scripts/fetch-data.sh
TOKEN="${MY_API_TOKEN:?Missing MY_API_TOKEN}"
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://api.example.com/data" | python3 -m json.tool
```

---

## 6. Cron Tool — Scheduled Jobs

### Payload Types

| Type | Session | Use When |
|------|---------|----------|
| `agentTurn` | Isolated (new session) | Autonomous tasks: briefings, reports, monitoring |
| `systemEvent` | Main (shared context) | Heartbeats, periodic check-ins needing conversation context |

### Schedule Types

| Type | Example | Description |
|------|---------|-------------|
| `at` | `"at": "2026-04-01T09:00:00Z"` | Single fire at absolute time (ISO-8601) |
| `every` | `"everyMs": 1800000` | Recurring interval in milliseconds |
| `cron` | `"expr": "0 9 * * 1-5", "tz": "America/New_York"` | Standard cron expression with timezone |

### Delivery Modes

| Mode | Description |
|------|-------------|
| `announce` | Posts result to a configured channel (`channel` + `to` fields) |
| `webhook` | Sends HTTP POST to an external URL |
| `none` | Silent execution (agent runs but doesn't post) |

### Example: Daily Briefing

```json
{
  "name": "morning-briefing",
  "enabled": true,
  "schedule": { "kind": "cron", "expr": "0 9 * * 1-5", "tz": "America/New_York" },
  "payload": { "kind": "agentTurn", "message": "Send morning briefing with today's agenda" },
  "sessionTarget": "isolated",
  "delivery": { "mode": "announce", "channel": "discord", "to": "<channel-id>" }
}
```

### Best Practices

- Use a **lighter model** (e.g., Haiku) for cron agents to reduce costs
- Group similar periodic checks in a `HEARTBEAT.md` file instead of creating many separate crons
- Avoid competing cron times (e.g., don't schedule 5 jobs at exactly 09:00)
- For delivery to a specific channel, use `delivery.channel/to` -- don't have the cron job call the `message` tool internally
- One-shot reminders use `at` schedule type, not `cron`

---

## 7. Message Tool — Channel Operations

The `message` tool supports a wide range of actions across Discord and Slack:

### Available Actions

| Category | Actions |
|----------|---------|
| **Messages** | `send`, `read`, `edit`, `delete` |
| **Reactions** | `react`, `reactions` |
| **Pins** | `pin`, `unpin`, `pins` |
| **Threads** | `thread-create`, `thread-list`, `thread-reply` |
| **Roles** | `role-add`, `role-remove`, `role-info` |
| **Info** | `member-info`, `channel-info`, `channel-list` |
| **Custom** | `emoji-list`, `emoji-upload`, `sticker-upload` |
| **Events** | `event-list`, `event-create` |
| **Moderation** | `timeout`, `kick`, `ban` |
| **Other** | `search`, `permissions`, `voice-status`, `poll` |

### Not Available via Message Tool

Role creation/editing/deletion, channel creation/deletion, and guild settings are **not** supported. For these operations, use a dedicated helper script that calls the Discord REST API v10 or Slack Web API directly.

### DM Targeting

When sending DMs, target format must use the `user:<id>` prefix:
```
message send user:123456789 "Hello!"
```
A bare ID without the `user:` prefix causes a channel lookup, which will fail for DMs.

### Rate Limits

- **Discord:** ~5 messages per 5 seconds per channel. Limit parallel sends to 3 at a time.
- **Slack:** ~1 request per second per API method per workspace. Limit parallel sends to 3.
- Exceeding rate limits causes the message tool to hang in retry backoff for minutes.

---

## Quick Reference Card

| Need | Tool | Notes |
|------|------|-------|
| Fetch a static web page | `web_fetch` | Fast, free |
| Fetch a JS-rendered page | `browser` | Headless Chrome |
| Search the web | `web_search` | Needs API key |
| Run a shell command | `exec` | Background for long ops |
| Send a channel message | `message` | Discord/Slack |
| Spawn a sub-agent | `sessions_spawn` | Isolated session |
| Schedule a recurring job | `cron` | agentTurn or systemEvent |
| Analyze an image | `image` | Only if not inline |
| Read a PDF | `pdf` | Native or text fallback |
| Text-to-speech | `tts` | Reply NO_REPLY after |
| Control a device | `nodes` | Android/iOS/macOS |
