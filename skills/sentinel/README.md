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
- **Coding-agent environments** — keeping credentials out of approved commands and agent config (Claude Code `settings.local.json`, `.mcp.json`), project `.gitignore`/`.dockerignore`, pre-commit and CI gates, `Read` deny rules, a PreToolUse hook, managed settings, permission audit, incident order

## What's inside

- `SKILL.md` — the full skill definition (identity, domains, CVE triage method, ethics)
- `references/playbooks.md` — bundled operational playbooks (VPS hardening, nginx/Docker/Spring Boot audits, incident response, AI/agent security audit, CVE feed triage)
- `references/coding-agents-hardening.md` — hardening workstations, servers and CI that run coding agents (Claude Code, Cursor, Codex, Gemini CLI): tested snippets, audit checklist, incident steps, sources
- `references/companion-tools.md` — optional open-source scanners Sentinel can offer to run alongside its own audit (Lynis, AIDE, ssh-audit, testssl.sh, Trivy, Grype/Syft, hadolint, Checkov, zizmor, actionlint, Semgrep CE, gitleaks, and more): default per domain, license, pinned install, read-only commands, caveats, what was tested

**Optional companions:** Sentinel works fully on its own. When a matching scanner is installed it offers, once, to also run it (or names the best one to install, with consent); findings are labelled by source.

This folder is **self-contained** — copy it into any runtime that loads a SKILL.md (Claude, OpenClaw, custom agents) and it works as-is. No other part of this repository is required.

## See also (optional)

If you use OpenClaw, there is also a full agent packaging of Sentinel — SOUL.md, AGENTS.md, TOOLS.md, IDENTITY.md and its own copy of the playbooks — in [../../openclaw/security/agents/sentinel/](../../openclaw/security/agents/sentinel/). It is an alternative, not a prerequisite.

## Trigger keywords

`security`, `hardening`, `exposed`, `vulnerable`, `firewall`, `fail2ban`, `nginx security`, `prompt injection`, `Ollama exposed`, `MCP security`, `agent security`, `CVE`, `CVE triage`, `Trivy`, `SSL`, `brute force`, `settings.local.json`, `don't ask again`, `.dockerignore`, `PreToolUse hook`, `managed settings`...
