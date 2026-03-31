# OpenClaw Best Practices & Guides

Community-maintained operational guides for OpenClaw AI agent gateway deployments. Each guide is self-contained and covers a specific topic in depth.

---

## Guides

| Guide | Description |
|-------|-------------|
| [Token Economy](token-economy.md) | Bootstrap diet, model selection, context pruning, compaction, cost optimization |
| [Multi-Agent Setup](multi-agent-setup.md) | Agent architecture, workspace structure, bindings, permissions, event bus |
| [Memory Architecture](memory-architecture.md) | 2-layer memory system, security rules, maintenance, cross-agent awareness |
| [Security & Guardrails](security-guardrails.md) | Passphrase guard, secrets management, prompt injection defense, server hardening |
| [Providers & Models](providers-and-models.md) | Anthropic/OpenAI/Gemini/Ollama auth, model selection, fallbacks, thinking modes |
| [Cron & Automation](cron-and-automation.md) | Payload types, schedules, delivery, heartbeats, async exec |
| [Tools & Skills](tools-and-skills.md) | Native tools, web search hierarchy, skills system |
| [Audio & Transcription](audio-and-transcription.md) | Whisper setup, TTS providers, transcription organization |
| [External Integrations](external-integrations.md) | Google, Atlassian, Slack, Discord setup and usage |
| [Media Organization](media-organization.md) | Directory structure, naming conventions, backup rules |
| [Git Backup Strategy](git-backup-strategy.md) | What to version, .gitignore rules, automation, disaster recovery |

## Also in This Repository

| Resource | Description |
|----------|-------------|
| [Agent Hardening](../security/good-practices/openclaw-agent-hardening.md) | Inbound message security, config protection, prompt injection defense patterns |
| [Sentinel Agent](../security/agents/sentinel/) | Complete security specialist agent configuration |
| [Config Guardian Skill](../../skills/config-guardian/) | Safe OpenClaw config updates with backup/validate/rollback |

---

## How to Use

- **New deployments** -- follow guides sequentially for a production-ready setup
- **Existing deployments** -- reference individual guides as needed for specific topics
- **AI assistants** -- load guides on-demand for operational knowledge (do not load all at once)

## Conventions

All guides follow these conventions:

| Convention | Example |
|------------|---------|
| Secrets use `${VAR}` syntax | `"token": "${DISCORD_TOKEN}"` |
| Model references use `provider/model` | `anthropic/claude-sonnet-4-6` |
| File paths use `~/.openclaw/` as base | Substitute with your actual config directory |
| Cost comparisons are relative | "3x cheaper" -- check provider pricing for actuals |
| Placeholders use angle brackets | `<your-user>`, `<guild-id>`, `<channel-id>` |

## Contributing

PRs welcome! Please keep guides:

- **In English** -- consistent language across all documentation
- **Generic** -- no specific IPs, ports, user IDs, or credentials
- **Self-contained** -- each guide should work standalone without requiring other guides
- **Practical** -- include config examples, commands, and tables over prose
- **Concise** -- if a section exceeds 50 lines, consider splitting into sub-sections

---

*These guides reflect best practices for OpenClaw v2026.x deployments. Check the [OpenClaw documentation](https://docs.openclaw.dev) for the latest feature reference.*
