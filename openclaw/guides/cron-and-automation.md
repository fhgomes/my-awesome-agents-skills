# Cron Jobs & Automation

How to schedule periodic tasks, run background commands safely, and manage concurrency in OpenClaw.

---

## Payload Types

Every cron job delivers its payload through one of two mechanisms:

### agentTurn (Recommended for Most Tasks)

Creates an **isolated session** for the target agent. The agent starts with a clean context — no conversation history, no prior state.

```jsonc
{
  "id": "daily-briefing",
  "type": "agentTurn",
  "agent": "<agent-id>",
  "payload": "Generate the daily briefing for today."
}
```

**Best for:** periodic autonomous tasks, reports, maintenance, data collection — anything that doesn't need awareness of an ongoing conversation.

### systemEvent

Injects into the **main agent's active session**. The agent has full conversation context from the current session.

```jsonc
{
  "id": "status-check",
  "type": "systemEvent",
  "agent": "<agent-id>",
  "payload": "Check the deployment status we discussed earlier."
}
```

**Best for:** heartbeats, context-aware follow-ups, periodic checks that relate to an active conversation.

**Caution:** systemEvent can disrupt an ongoing conversation. If the agent is mid-task, the injected event competes for attention. Prefer agentTurn unless you specifically need conversation context.

---

## Schedule Types

### `at` — Single Fire

Executes once at a specific time, then auto-deletes.

```jsonc
{
  "schedule": {
    "at": "2026-04-01T09:00:00Z"
  }
}
```

Use ISO-8601 format. The cron entry is automatically removed after firing.

### `every` — Interval

Executes at a fixed interval (in milliseconds).

```jsonc
{
  "schedule": {
    "every": 3600000
  }
}
```

Common intervals:
- 15 minutes: `900000`
- 1 hour: `3600000`
- 6 hours: `21600000`
- 24 hours: `86400000`

### `cron` — Traditional Expression

Standard cron syntax with timezone support.

```jsonc
{
  "schedule": {
    "cron": "0 9 * * *",
    "timezone": "America/New_York"
  }
}
```

| Expression | Meaning |
|-----------|---------|
| `0 9 * * *` | Daily at 9:00 AM |
| `0 9 * * 1-5` | Weekdays at 9:00 AM |
| `0 */6 * * *` | Every 6 hours |
| `0 9 1 * *` | First of every month at 9:00 AM |
| `*/30 * * * *` | Every 30 minutes |

Always specify `timezone` — without it, the server's default timezone is used, which may not be what you expect.

---

## Delivery

How the cron result is communicated:

### announce

Posts the result to a specific channel:

```jsonc
{
  "delivery": {
    "announce": {
      "channel": "discord",
      "target": "<channel-id>"
    }
  }
}
```

### webhook

Sends the result as an HTTP POST:

```jsonc
{
  "delivery": {
    "webhook": {
      "url": "https://hooks.example.com/endpoint",
      "headers": {
        "Authorization": "Bearer ${WEBHOOK_TOKEN}"
      }
    }
  }
}
```

### none

Silent execution — no output delivery. Useful for maintenance tasks that write to files or memory:

```jsonc
{
  "delivery": "none"
}
```

---

## Heartbeat vs Cron Decision Guide

| Factor | Use Heartbeat (systemEvent) | Use Cron (agentTurn) |
|--------|---------------------------|---------------------|
| Needs conversation context | Yes | No |
| Runs independently | No | Yes |
| Frequency | Low (hourly+) | Any |
| Session impact | May disrupt active conversation | None (isolated) |
| Clean context needed | No | Yes |
| Self-check / monitoring | Good fit | Not ideal |
| Report generation | Not ideal | Good fit |
| Memory maintenance | Either works | Preferred |
| Deployment follow-ups | Good fit | Not ideal |

---

## Async Exec (CRITICAL)

Long-running commands **must** run in background mode. Without it, the command blocks the agent's processing lane, making the bot unresponsive to all other messages.

### The Problem

```jsonc
// BAD: Synchronous exec blocks the lane
{
  "payload": "Run the build: npm run build"
}
// Agent runs `npm run build`, which takes 5 minutes
// During those 5 minutes, the agent cannot respond to ANYONE
```

### The Solution

```jsonc
{
  "exec": {
    "background": true,
    "backgroundMs": 5000,
    "notifyOnExit": true,
    "timeoutSec": 1800
  }
}
```

| Setting | Purpose | Recommended |
|---------|---------|-------------|
| `background: true` | Run command in background | Always for commands > 5 seconds |
| `backgroundMs: 5000` | Wait up to 5s for quick results before backgrounding | 3000-10000 |
| `notifyOnExit: true` | Notify agent when command completes | Always true |
| `timeoutSec: 1800` | Kill command after 30 minutes | Adjust per command |

### What to Background

- Docker builds (`docker build`, `docker-compose up`)
- Package installation (`npm install`, `pip install`, `gradle build`)
- Large file operations (backups, compression, transfers)
- Test suites (`npm test`, `pytest`, `gradle test`)
- Any command that might take more than 10 seconds

### Agent SOUL.md Rule

Add this to your agent's bootstrap:

```markdown
## Exec Rules
- ALWAYS use background mode for builds, installs, tests, and Docker operations
- NEVER run synchronous commands that take more than 10 seconds
- Set timeoutSec as a safety net for every background command
```

---

## Concurrency

### Lane Management

OpenClaw processes agent turns through lanes. Each agent gets a limited number of concurrent lanes.

```jsonc
{
  "concurrency": {
    "maxConcurrent": 8
  }
}
```

This covers **all** concurrent activity: multi-agent conversations, cron jobs, sub-agent spawning, and background exec notifications.

**Rule of thumb:** set `maxConcurrent` to cover your peak load (active agents + concurrent crons) with 2-3 spare lanes for responsiveness.

### Cron Spacing

When multiple crons fire at similar times, they compete for lanes. Space cron schedules by 1-2 minutes:

```jsonc
// Good: staggered schedules
{ "id": "briefing",    "schedule": { "cron": "0 9 * * *" } }    // 9:00
{ "id": "maintenance",  "schedule": { "cron": "2 9 * * *" } }    // 9:02
{ "id": "health-check", "schedule": { "cron": "5 9 * * *" } }    // 9:05

// Bad: all at the same time
{ "id": "briefing",    "schedule": { "cron": "0 9 * * *" } }    // 9:00
{ "id": "maintenance",  "schedule": { "cron": "0 9 * * *" } }    // 9:00
{ "id": "health-check", "schedule": { "cron": "0 9 * * *" } }    // 9:00
```

### Model Assignment for Crons

Always use Haiku for cron agents to reduce both cost and lane contention:

```jsonc
{
  "agents": {
    "list": [
      {
        "id": "cron-agent",
        "model": "anthropic/claude-haiku-4-5",
        "identity": "Autonomous task runner for scheduled jobs"
      }
    ]
  }
}
```

---

## Server-Level Crons

Some tasks run independently of OpenClaw, managed by the system's crontab:

### Config Backup

```bash
# crontab -e (as service user)
0 */6 * * * cd ~/.openclaw && git add -A && git commit -m "auto-backup $(date +\%F-\%H\%M)" && git push 2>/dev/null
```

### Session Cleanup

```bash
# Remove session files older than 14 days
0 3 * * * find ~/.openclaw/sessions/ -name "*.jsonl" -mtime +14 -delete
```

### Preventive Restart

```bash
# Weekly restart to clear accumulated state
0 4 * * 0 systemctl restart openclaw
```

### Log Rotation

```bash
# Rotate OpenClaw logs
0 0 * * * journalctl --vacuum-time=30d
```

---

## Example: Daily Briefing Cron

A complete configuration for a daily morning briefing:

```jsonc
{
  "crons": [
    {
      "id": "daily-briefing",
      "type": "agentTurn",
      "agent": "briefing-agent",
      "schedule": {
        "cron": "0 9 * * 1-5",
        "timezone": "America/New_York"
      },
      "payload": "Generate today's briefing: check service health, summarize yesterday's agent activity from memory/daily/ logs, list any pending tasks from memory/pending.md, and note upcoming deadlines.",
      "delivery": {
        "announce": {
          "channel": "discord",
          "target": "<briefing-channel-id>"
        }
      }
    }
  ]
}
```

### Supporting Agent Config

```jsonc
{
  "agents": {
    "list": [
      {
        "id": "briefing-agent",
        "workspace": "~/.openclaw/agents/briefing",
        "agentDir": "~/.openclaw/agents/briefing",
        "model": "anthropic/claude-haiku-4-5",
        "thinking": "off",
        "identity": "Daily briefing generator — reads logs and status, produces concise summaries"
      }
    ]
  }
}
```

---

## Best Practices

1. **Avoid competing schedules.** If two crons produce similar reports, combine them or stagger by at least 2 minutes.

2. **Use Haiku for all cron agents.** Cron tasks are scoped and autonomous — they rarely need Sonnet's full capability. This reduces cost and lane pressure.

3. **`at`-type crons auto-delete after firing.** Use them for one-time scheduled tasks (deployment follow-ups, deadline reminders). No cleanup needed.

4. **Never create crons with `exec` that can fail silently.** If a cron runs a command that fails and retries automatically, it creates an infinite retry loop with no auto-kill mechanism. Always validate commands work before scheduling them.

5. **Validate commands before scheduling.** Test the exact command in a manual session first. Crons run without interactive supervision — silent failures waste tokens and lanes.

6. **Use `timeoutSec` as a safety net.** Every background exec should have a timeout. Without it, a hung process blocks a lane indefinitely.

7. **Space cron schedules.** Multiple crons firing simultaneously compete for lanes, degrading responsiveness for all agents.

8. **Use `agentTurn` for autonomous tasks.** `systemEvent` can disrupt active conversations. Only use it when you specifically need conversation context.

9. **Set delivery appropriately.** Use `announce` for reports that stakeholders need to see, `none` for maintenance tasks, and `webhook` for integration with external systems.

10. **Monitor cron execution.** Check logs periodically:

```bash
journalctl -u openclaw.service --since "24h ago" | grep -i "cron"
```

---

## Quick Reference

```jsonc
{
  "crons": [
    {
      "id": "<unique-id>",
      "type": "agentTurn",           // or "systemEvent"
      "agent": "<agent-id>",
      "schedule": {
        "cron": "<expression>",      // or "at"/"every"
        "timezone": "<tz>"
      },
      "payload": "<instructions>",
      "delivery": "none"             // or { "announce": {...} } or { "webhook": {...} }
    }
  ],
  "concurrency": {
    "maxConcurrent": 8
  }
}
```
