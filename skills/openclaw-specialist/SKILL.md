---
name: openclaw-specialist
description: Use when maintaining, configuring, diagnosing, or updating an OpenClaw instance — cron jobs, agents, channels, config changes, version upgrades, service restarts, or troubleshooting delivery/exec/channel issues. Also use when reviewing agent instructions or bootstraps for optimization.
---

# OpenClaw Operations Specialist

Expert-level OpenClaw infrastructure management. Config changes, cron fixes, agent tuning, version migrations, diagnostics.

## Environment Conventions

Replace the placeholders below with your own values:

| Placeholder | Typical value |
|-------------|---------------|
| `<USER>` | Linux user running OpenClaw (e.g. `openclaw`, or your own username) |
| `<PORT>` | Gateway port from `gateway.port` (default `55444`) |
| `<HOME>` | User home (e.g. `/home/<USER>`) |
| `<CONFIG>` | `<HOME>/.openclaw/openclaw.json` |
| `<BIN>` | Local binary at `<HOME>/.openclaw/local/bin/openclaw` |
| `<UNIT>` | systemd unit name (e.g. `openclaw.service`) |

Most commands assume a systemd-managed instance with a dedicated user. If you run a single-user installation, drop the `sudo -u <USER>`.

**Cron storage:** `<HOME>/.openclaw/cron/jobs.json` (NOT inside `openclaw.json`).

## Config Change Protocol

```
Read current → Backup → Patch surgically → chown → doctor --fix → Restart → Verify
```

1. **Read** current state:
   `cat <CONFIG> | python3 -c "import sys,json;print(list(json.load(sys.stdin).keys()))"`
2. **Backup** before touching:
   `cp <CONFIG> <CONFIG>.bak-$(date +%Y%m%d-%H%M%S)`
3. **Patch surgically** — never overwrite entire sections. Prefer Python JSON or `jq` over full-file rewrites
4. **chown** to the correct user after every edit:
   `chown <USER>:<USER> <CONFIG>` (required if your CLI runs as root)
5. **Validate:** `sudo -u <USER> <BIN> doctor` (add `--fix` only after reading the report)
6. **Restart:** `systemctl restart <UNIT>`
7. **Verify:** wait ~60s for boot, then check `/ready`:
   `curl -s http://127.0.0.1:<PORT>/ready | python3 -m json.tool`

### Critical Rules

- OpenClaw **rejects unknown JSON keys** — the service crashes on startup. Always validate with `openclaw doctor` before restart.
- NEVER use `openclaw gateway status/restart/run` if the process is under systemd — it returns false negatives and conflicts with the unit.
- NEVER run Docker/Gradle/long builds synchronously inside an agent turn — use `background: true` in cron payloads or detach the process.
- After any version update: run `openclaw doctor --fix` per instance, then restart.
- Services use the **local** binary (`<HOME>/.openclaw/local/bin/openclaw`), not the global `npm -g` install. Update the local prefix when upgrading.

## Cron Jobs — Quick Reference

### Payload Types

| `payload.kind` | Use For | Tool Access | Field |
|----------------|---------|-------------|-------|
| `agentTurn` | Autonomous jobs (the agent thinks and acts) | Full (exec, message, browser) | `message` |
| `systemEvent` | Passive notifications only (no LLM reasoning) | None | `text` |

### Session Target

| Value | Use | Behavior |
|-------|-----|----------|
| `"isolated"` | **All** autonomous cron jobs | Dedicated disposable session; no cross-contamination |
| `"main"` | Avoid for tool-dependent jobs | Shares the main session; causes conflicts |

### Correct Cron Pattern

```json
{
  "payload": {
    "kind": "agentTurn",
    "message": "[SYSTEM: Tools are pre-approved. Execute directly.]\n\nYour instruction here",
    "timeoutSeconds": 180
  },
  "sessionTarget": "isolated",
  "tools": ["exec", "message", "read", "write", "web_fetch", "web_search"],
  "delivery": { "mode": "none" }
}
```

**Three layers required for autonomous cron execution:**
1. `tools: [...]` — grants system-level tool access in the isolated session (v2026.4.1+)
2. `[SYSTEM: pre-approved]` prefix — tells the LLM to act without asking the user for permission
3. `exec-approvals.json` allowlist — permits the specific shell commands the agent will invoke

### Delivery Modes

- `"none"` — the agent sends messages itself via the `message` tool (use when your instruction says to send)
- `"announce"` — the system auto-delivers the agent's response. **Requires a `to` field for Discord/Slack**:
  `"to": "channel:<id>"` or `"to": "user:<id>"`
- Missing `to` with `announce` → "recipient required" error

### Diagnostics

| `lastDeliveryStatus` | Meaning |
|---------------------|---------|
| `"not-requested"` | No delivery configured — wrong `payload.kind` or `sessionTarget` |
| `"not-delivered"` | Delivery failed — check `delivery` config and recipient |
| `"delivered"` | OK |
| `"unknown"` | Target could not be resolved (bad channel/user id) |

```bash
sudo -u <USER> <BIN> cron status          # Scheduler state
sudo -u <USER> <BIN> cron list            # All jobs with last status
sudo -u <USER> <BIN> cron run <name>      # Manual debug run
sudo -u <USER> <BIN> cron runs --limit 10 # Recent history
```

## Agent Config — Quick Reference

### Config Structure

```
openclaw.json
├── agents.list[]         ← agent definitions (id, model, workspace, identity, tools, subagents)
├── bindings[]            ← channel → agent routing
├── channels              ← discord, slack, whatsapp, telegram, webchat configs
├── models.providers{}    ← provider registry (dict, keyed by provider id)
├── tools.exec            ← exec settings (security, backgroundMs, timeoutSec)
├── session               ← compaction, contextTokens, memoryFlush
├── gateway               ← port, bind, auth
└── plugins.entries       ← enabled plugins
```

### Per-Agent Model Overrides

Go **inside** the `agents.list[]` entry, not as a top-level key:

```json
{ "id": "my-agent", "model": "<provider-id>/<model-id>", "...": "..." }
```

### Agent Bootstrap Files (workspace)

| File | Purpose | Size Budget |
|------|---------|-------------|
| `SOUL.md` | Identity, mission, core rules | <5 KB |
| `AGENTS.md` | Safety rules, session protocol | <3 KB |
| `TOOLS.md` | Tool quick reference | <3 KB |
| `MEMORY.md` | Accumulated knowledge index | <2 KB |
| `USER.md` | User context | <1 KB |

**Total bootstrap <15 KB.** Put heavy reference in `memory/*.md` files loaded on demand. Bootstrap tokens are paid on *every* turn — keep them lean.

### DM Targets

The `message` tool's DM targets **must** use the `user:<id>` prefix. Bare IDs are resolved as channels and will fail silently.

## Version Update Checklist

1. `sudo -u <USER> npm install -g --prefix <HOME>/.openclaw/local openclaw@<VERSION>`
2. `chown -R <USER>:<USER> <HOME>/.openclaw/local`
3. `sudo -u <USER> <BIN> doctor --fix`
4. `sudo -u <USER> <BIN> cron list` — scan for jobs flagged by doctor as broken
5. `systemctl restart <UNIT>`
6. Wait ~60 s for non-root boot, then:
   `curl -s http://127.0.0.1:<PORT>/ready | python3 -m json.tool`
7. If you also updated Claude Code locally (`claude update`), re-copy the binary to the path your CLI expects (if any).

## Channel Troubleshooting

| Symptom | Diagnosis | Fix |
|---------|-----------|-----|
| WhatsApp 440 loop | Another WA Web session is active | Close all other WA Web sessions → `openclaw channels login --channel web` |
| Discord stale-socket | Gateway socket dropped; health monitor restarts it | Normal if <1/hour. If frequent: check internet/firewall/Discord status |
| Slack pong timeout | WebSocket drop | Health monitor auto-recovers. If persistent: Slack service-side issue |
| "Unauthorized" on `/ready` | Boot still in progress (~60 s for non-root users) | Wait — this is NOT an auth problem |
| Agent "asking permission" in cron | Payload is `systemEvent` instead of `agentTurn` | Fix `payload.kind` |
| Delivery says "Discord recipient is required" | Using `announce` mode without a `to` field | Add `"to": "channel:<id>"` or switch to `"mode": "none"` |

## Common Diagnostic Commands

```bash
# Service status
systemctl status <UNIT>

# Logs (last hour, error bucket)
journalctl -u <UNIT> --since "1h ago" | grep -iE "error|stuck|loop|overflow|disconnect"

# Channel health (JSON)
curl -s http://127.0.0.1:<PORT>/ready | python3 -m json.tool

# Cron scheduler state
sudo -u <USER> <BIN> cron status

# List top-level config keys (sanity check)
cat <CONFIG> | python3 -c "import sys,json; print(list(json.load(sys.stdin).keys()))"

# List registered providers
cat <CONFIG> | python3 -c "import sys,json; print(list(json.load(sys.stdin)['models']['providers'].keys()))"
```

## Key Breaking Changes (recent versions)

Read the `CHANGELOG.md` inside the openclaw npm package for full detail.

| Version | Change | Action |
|---------|--------|--------|
| v2026.3.31 | Background tasks overhauled; `systemEvent` crons that used to work must move to `agentTurn` | Fix cron `payload.kind` |
| v2026.4.2 | xAI / Firecrawl config paths moved | `openclaw doctor --fix` |
| v2026.4.5 | Legacy config aliases removed; streaming config went from string to object | `openclaw doctor --fix` |
| v2026.4.7 | Memory-Wiki, compaction checkpoints, agent timeout inheritance | Review per-agent timeouts |
| v2026.4.9 | Idle watchdog disabled for crons; session reload guard | Improves cron reliability — no action required |

## Agent Review Workflow

When reviewing an agent after a version update:

1. Read `CHANGELOG.md` in the `openclaw` npm package for breaking changes
2. For each agent: read `SOUL.md` + `AGENTS.md` + `TOOLS.md`
3. Ask: are there new features that simplify current workarounds?
4. Ask: are there removed/renamed config keys affecting this agent?
5. Ask: can the model selection be improved given new provider options?
6. Ask: does the bootstrap exceed the 15 KB budget? Diet if needed
7. Document the review outcome in whatever knowledge base you use (README, wiki, vault)

## Response Format (recommended)

When this skill is driving a task, structure the reply as:

```
## Diagnosis
<what is wrong, per instance/service — short bullets>

## Fix
<exact commands in bash blocks; mention sudo -u <USER> when touching home files>

## Verification
<curl /ready, systemctl is-active, openclaw doctor, log tail>

## Next steps
<ordered by real risk — critical → high → medium → low>

## References
<version notes, CHANGELOG entries, or internal runbooks cited>
```

## Principles

1. **Never** edit `openclaw.json` without validating first — unknown keys cause startup crashes.
2. **Never** restart without a pre/post check — `systemctl status`, `/ready`, a sample cron run.
3. **Always** chown to the correct user after editing anything inside `<HOME>`.
4. **Prefer surgical patches** over full-file rewrites. Python/jq over editors when possible.
5. **Wait ~60 s** after a restart for non-root users before interpreting `/ready`.
6. **Prioritize by real risk**, not theoretical best practice — production first, style second.
