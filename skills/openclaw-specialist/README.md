# openclaw-specialist

Drop-in OpenClaw operations specialist skill. Install as an OpenClaw skill or load into any agent that manages OpenClaw infrastructure.

## What it does

Guides safe, surgical operations on an OpenClaw instance:

- Config changes (`openclaw.json`) with backup → validate → restart → verify
- Cron job authoring (`payload.kind`, `sessionTarget`, `delivery` semantics)
- Agent bootstrap review (`SOUL.md` / `AGENTS.md` / `TOOLS.md` size budgets)
- Channel troubleshooting (Discord / Slack / WhatsApp)
- Version upgrades (local binary install, `doctor --fix`, restart)
- Structured diagnosis reports (Diagnosis / Fix / Verification / Next steps)

## Install

1. Copy `SKILL.md` into your OpenClaw skills directory (typically `~/.openclaw/skills/openclaw-specialist/`), or reference it directly from an agent's workspace.
2. Replace the placeholders at the top of the skill (`<USER>`, `<PORT>`, `<HOME>`, `<UNIT>`) with your own values, or keep them generic and let the agent fill them from context.
3. Load the skill into an agent — for example, give your "ops" agent a `skills` entry pointing at it, or paste it as reference material in the agent's bootstrap.

## Related guides in this repo

- [`openclaw/guides/ollama-setup.md`](../../openclaw/guides/ollama-setup.md) — add a local or hosted Ollama provider to an OpenClaw instance with a quick-test path and rollback
- [`openclaw/guides/providers-and-models.md`](../../openclaw/guides/providers-and-models.md) — reference for authenticating Anthropic, OpenAI, Gemini, Ollama
- [`openclaw/guides/cron-and-automation.md`](../../openclaw/guides/cron-and-automation.md) — deeper dive on cron payloads and schedules
- [`skills/config-guardian/SKILL.md`](../config-guardian/SKILL.md) — scripted backup/validate/diff/restore helpers referenced by this skill's protocol

## Notes

- Nothing in this skill is tied to a specific instance. Placeholders keep it portable.
- If you run multiple instances, clone the placeholder block per instance in your own agent config.
- The skill assumes a systemd-managed OpenClaw with a dedicated Linux user. For single-user setups, drop the `sudo -u <USER>` prefix from commands.
