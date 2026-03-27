# my-awesome-agent-skills

A collection of agent skills and configurations for AI assistants.

## Structure

```
skills/          # Universal SKILL.md files (provider-agnostic)
  <skill-name>/
    SKILL.md     # Skill definition — works with any OpenClaw-compatible agent

openclaw/        # OpenClaw-specific configuration files
  <skill-name>/
    SOUL.md      # Agent identity and operating principles
    AGENTS.md    # Memory rules and workspace conventions
    TOOLS.md     # Available tools with commands and guardrails
    IDENTITY.md  # Name, emoji, avatar
    MEMORY.md    # Memory index
    references/  # Playbooks, checklists, and reference material
    scripts/     # Helper scripts
```

## Skills

| Skill | Description |
|-------|-------------|
| [sentinel](skills/sentinel/SKILL.md) | Cybersecurity & DevSecOps specialist — hardening, audits, incident response, AI/agent security |

---

Maintained by [@fhgomes](https://github.com/fhgomes)
