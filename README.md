# my-awesome-agent-skills

A collection of agent skills and configurations for AI assistants, built for [OpenClaw](https://openclaw.ai).

## Structure

```
skills/          # Universal SKILL.md files — drop-in skills for any OpenClaw agent
  <name>/
    SKILL.md     # Skill definition (routing, tools, examples)
    scripts/     # Helper scripts (when needed)

security/        # Security-focused agents and hardening guides
  sentinel/      # Sentinel agent SKILL.md (security specialist)
  good-practices/ # Hardening guides and best practices

openclaw/        # OpenClaw-specific agent configurations
  <name>/        # General agents
  security/      # Security agents
    sentinel/    # Sentinel full config (SOUL.md, TOOLS.md, playbooks)
```

## Skills

| Skill | Description |
|-------|-------------|
| [config-guardian](skills/config-guardian/SKILL.md) | Safe OpenClaw config updates — backup, validate, diff, rollback |
| [obsidian-daily](skills/obsidian-daily/SKILL.md) | Manage Obsidian daily notes via obsidian-cli |

## Security

| Resource | Description |
|----------|-------------|
| [sentinel](security/sentinel/SKILL.md) | Security & DevSecOps specialist agent — hardening, audits, incident response, AI/agent security |
| [openclaw-agent-hardening](security/good-practices/openclaw-agent-hardening.md) | Practical hardening guide: inbound message security, prompt injection defense, secrets management, allowlisting |

### Sentinel — Security Agent

Sentinel is a cybersecurity specialist agent focused on:
- Linux server hardening (SSH, UFW, fail2ban, kernel)
- Nginx/Docker/Spring Boot security audits
- Log analysis and incident response
- DNS/TLS/certificate audits
- **AI/LLM/Agent security** — prompt injection, Ollama exposure, MCP token security, OWASP Top 10 LLM

Full OpenClaw configuration (SOUL.md, TOOLS.md, playbooks) in [openclaw/security/sentinel/](openclaw/security/sentinel/).

### Good Practices

[`security/good-practices/openclaw-agent-hardening.md`](security/good-practices/openclaw-agent-hardening.md) covers:

- Inbound message security (untrusted data, indirect injection)
- Config file protection and version control
- Tool and permission hardening (least privilege, Docker socket, MCP scoping)
- Secrets management (.env, billing alerts)
- Agent allowlisting
- Prompt injection defense patterns with real examples

---

Maintained by [@fhgomes](https://github.com/fhgomes)
