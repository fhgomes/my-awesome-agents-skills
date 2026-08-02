# Sentinel — Security & Hardening Specialist

**SKILL.md** — Drop-in skill for any OpenClaw-compatible agent.

## What it does

Sentinel is a cybersecurity and DevSecOps specialist that delivers ready-to-run commands and configs, not abstract advice.

**Domains:**
- Linux server hardening (SSH, UFW, fail2ban, kernel, updates)
- Nginx security (TLS, rate limiting, headers, WAF rules)
- Docker & container security (isolation, Trivy, secrets)
- Spring Boot production security (actuator, CORS, CSRF, injection)
- Log analysis and incident response
- CVE feed triage and backlog hygiene (keyword-match false-positive filtering)
- DNS/TLS/certificate audits
- **AI/LLM/Agent security** — prompt injection, Ollama exposure, MCP tokens, agent permissions, OWASP Top 10 LLM

## What's inside

- `SKILL.md` — the full skill definition (identity, domains, CVE triage method, ethics)
- `references/playbooks.md` — bundled operational playbooks (VPS hardening, nginx/Docker/Spring Boot audits, incident response, AI/agent security audit, CVE feed triage)

This folder is **self-contained** — copy it into any runtime that loads a SKILL.md (Claude, OpenClaw, custom agents) and it works as-is. No other part of this repository is required.

## See also (optional)

If you use OpenClaw, there is also a full agent packaging of Sentinel — SOUL.md, AGENTS.md, TOOLS.md, IDENTITY.md and its own copy of the playbooks — in [../../openclaw/security/agents/sentinel/](../../openclaw/security/agents/sentinel/). It is an alternative, not a prerequisite.

## Trigger keywords

`security`, `hardening`, `exposed`, `vulnerable`, `firewall`, `fail2ban`, `nginx security`, `prompt injection`, `Ollama exposed`, `MCP security`, `agent security`, `CVE`, `CVE triage`, `Trivy`, `SSL`, `brute force`...
