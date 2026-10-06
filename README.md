# my-awesome-agent-skills

A collection of agent skills and configurations for AI assistants, built for [OpenClaw](https://openclaw.ai).

> **Design principle — every item is self-contained.** You can take just one
> `skills/<name>/` folder and install it (Claude, OpenClaw, or any runtime that loads
> a SKILL.md), or just one agent/area under `openclaw/<area>/`, without needing
> anything from the other trees. Cross-links between items are optional "see also"
> pointers, never prerequisites. Content is deliberately duplicated between variants
> when needed — isolation beats DRY here.

> **Contributing / editing with an AI agent:** this repository is public. Read
> [CLAUDE.md](CLAUDE.md) (Claude Code) or [AGENTS.md](AGENTS.md) (any agent) first —
> English only, no personal or machine-specific data, and a `redact` + `warden`
> security pass before every commit.

## Structure

```
skills/          # Universal, self-contained skills — each folder works standalone
  <name>/
    SKILL.md     # Skill definition (routing, tools, examples)
    references/  # Reference material bundled with the skill (when needed)
    scripts/     # Helper scripts (when needed)

guides/          # Vendor-neutral engineering guides — each area self-contained
  testing/       # Guides + enforcement/ (per-AI-tool configs, git hooks, CI gate)
  performance/   # Guides + enforcement/ (per-AI-tool configs, grep hook, Lighthouse CI, k6)

claude/          # Claude-format variants (SKILL.md + references/ loaded on demand)
  skills/
    <name>/
      SKILL.md
      references/

openclaw/        # OpenClaw-specific agents, guides, and areas — each self-contained
  ghost/         # Ghost blog admin + content pipeline
  guides/        # Best practice guides for OpenClaw deployments
  security/      # Security agents and hardening guides
    agents/sentinel/   # Sentinel full agent config (SOUL.md, TOOLS.md, playbooks)
    good-practices/    # Hardening guides and best practices
```

## Skills

| Skill | Description |
|-------|-------------|
| [andela-profile](skills/andela-profile/SKILL.md) | Fill in or rewrite an Andela talent profile from the user's CV through the logged-in browser — field map and limits, markdown rules per field, automatic skill extraction, site-specific automation traps (Enter submits from the skills box, checkbox ignores programmatic input), reload-and-verify |
| [config-guardian](skills/config-guardian/SKILL.md) | Safe OpenClaw config updates — backup, validate, diff, rollback |
| [consistent-visual-generation](skills/consistent-visual-generation/SKILL.md) | Consistent AI character/persona generation — Character Bible, canonical references, 6-round interview, file/version conventions, canon promotion, and calibration of subtle identity cues |
| [harness-engineer](skills/harness-engineer/SKILL.md) | Identify a repo deeply and harvest its patterns, conventions, and business rules into an AI harness — router AGENTS.md + vendor files + routed guides so any coding agent works with more context and quality. Also available in [Claude skill format](claude/skills/harness-engineer/) (SKILL.md + on-demand references) |
| [media-transcription](skills/media-transcription/SKILL.md) | Audio/video transcription — faster-whisper large-v3 on GPU (local) or YouTube transcript (remote), with environment detection, fail-fast, and a quality/QA playbook |
| [obsidian-daily](skills/obsidian-daily/SKILL.md) | Manage Obsidian daily notes via obsidian-cli |
| [openclaw-specialist](skills/openclaw-specialist/SKILL.md) | End-to-end OpenClaw ops — config protocol, cron authoring, channels, upgrades, diagnostics |
| [perf-engineer](skills/perf-engineer/SKILL.md) | Performance engineer persona — measures before claiming, reviews diffs for N+1 / unpaged reads / missing indexes / unmeasured claims, answers as Diagnosis / Evidence / Fix / Verification / Budget; bundled checklists and Day 1 / Week 1 plans |
| [slides-html](skills/slides-html/SKILL.md) | HTML slide decks as one self-contained file on a fixed 1920×1080 stage (never reflows), generated from reusable design-system files (palette with accent rules, type scale in stage px, components, 30 slide recipes in the bundled `nightsky-java` system) — style round with real previews, PPTX/PDF import, Playwright PDF/PNG export, metrics-first browser verification |
| [test-engineer](skills/test-engineer/SKILL.md) | Test engineering specialist — picks the layer (integration-first, mocks for pure logic), demands red-then-green with pasted output, refuses weakened assertions / `@Disabled` / `.only`, 403-never-404 ownership probes, fake-coverage greps, review checklist |
| [video-editing](skills/video-editing/SKILL.md) | CLI video editing with ffmpeg — frame-accurate cuts, 9:16/1:1/4:5 formats, CapCut-style word-level captions, xfade catalog, zoom+flash+whoosh transitions, color grading, runtime GPU/NVENC detection, with a [parameterized example pipeline](skills/video-editing/examples/interview-clip-pipeline/) |

## Security

| Resource | Description |
|----------|-------------|
| [sentinel](skills/sentinel/SKILL.md) | Security & DevSecOps specialist agent — hardening, audits, incident response, AI/agent security, CVE triage |
| [warden](skills/warden/SKILL.md) | Malware & threat analysis — static triage of files, folders, PoCs, URLs and dependencies; layered deobfuscation; incident response. Never executes the sample |
| [redact](skills/redact/SKILL.md) | Pre-publication privacy audit — secrets, PII/PCI/PHI and internal infra in the working tree **and git history**, with remediation (env vars, `.env.example`, history rewrite, rotation) |
| [openclaw-agent-hardening](openclaw/security/good-practices/openclaw-agent-hardening.md) | Practical hardening guide: inbound message security, prompt injection defense, secrets management, allowlisting |

### The three security skills — which one to use

They are complementary, each answering a different question:

| Skill | Question it answers |
|-------|---------------------|
| [sentinel](skills/sentinel/) | *"How do I protect my server?"* — infrastructure hardening |
| [warden](skills/warden/) | *"Is this file malicious?"* — malware and threat analysis |
| [redact](skills/redact/) | *"If I publish this, what leaks?"* — secret and PII exposure |

### Sentinel — Security Agent

Sentinel is a cybersecurity specialist agent focused on:
- Linux server hardening (SSH, UFW, fail2ban, kernel)
- Nginx/Docker/Spring Boot security audits
- Log analysis and incident response
- DNS/TLS/certificate audits
- **AI/LLM/Agent security** — prompt injection, Ollama exposure, MCP token security, OWASP Top 10 LLM
- CVE feed triage and vulnerability backlog hygiene

Two self-contained variants:
- [skills/sentinel/](skills/sentinel/) — drop-in skill (SKILL.md + bundled playbooks) for any runtime
- [openclaw/security/agents/sentinel/](openclaw/security/agents/sentinel/) — full OpenClaw agent config (SOUL.md, TOOLS.md, playbooks)

## Engineering Guides

Vendor-neutral guides for teams that ship with AI coding tools. Each area separates **recommendations** (the guides) from **enforcement** (instruction blocks, hooks and CI gates for Claude Code, Codex, Gemini CLI, GitHub Copilot, Cursor, Cline and aider — so any model, DeepSeek included, is held to the same rules). Every AI-tool config block is either verified against the vendor's docs on a stated date or marked unverified.

| Area | Description |
|------|-------------|
| [Testing](guides/testing/README.md) | From zero to a trusted suite: layers, Day 1 / Week 1 for greenfield and legacy, Spring (Testcontainers, MockMvc), React (vitest, Testing Library), Flutter, Playwright E2E with a production guard, the AI prompt template and a 12-smell catalogue |
| [Testing Enforcement](guides/testing/enforcement/README.md) | Making the rules mandatory: instruction blocks, post-edit and stop hooks per AI tool, git `pre-commit` + `commit-msg` scripts, a GitHub Actions required check with a feat/fix-needs-a-test guard |
| [Performance](guides/performance/README.md) | Measure first, budgets in CI, the eight ways an AI silently writes slow code, backend (Spring Boot + PostgreSQL), frontend (React + Vite) and mobile (Flutter) practice, Day 1 / Week 1 for greenfield and legacy |
| [Performance Enforcement](guides/performance/enforcement/README.md) | Instruction blocks, verified hook configs per AI tool, a grep checklist hook, Lighthouse CI + k6 thresholds and a GitHub Actions workflow |

## Best Practice Guides

Comprehensive operational guides for OpenClaw deployments — generic, shareable, no infrastructure-specific details.

| Guide | Description |
|-------|-------------|
| [Token Economy](openclaw/guides/token-economy.md) | Bootstrap diet, model selection, context pruning, compaction, cost optimization |
| [Multi-Agent Setup](openclaw/guides/multi-agent-setup.md) | Agent architecture, workspace structure, bindings, permissions, event bus |
| [Memory Architecture](openclaw/guides/memory-architecture.md) | 2-layer memory system, security rules, maintenance, cross-agent awareness |
| [Security & Guardrails](openclaw/guides/security-guardrails.md) | Passphrase guard, secrets, prompt injection defense, server hardening |
| [Providers & Models](openclaw/guides/providers-and-models.md) | Anthropic/OpenAI/Gemini/Ollama auth, model selection, fallbacks, thinking |
| [Cron & Automation](openclaw/guides/cron-and-automation.md) | Payload types, schedules, delivery, heartbeats, async exec |
| [Tools & Skills](openclaw/guides/tools-and-skills.md) | Native tools, web search hierarchy, skills system |
| [Audio & Transcription](openclaw/guides/audio-and-transcription.md) | Whisper setup, TTS providers, transcription organization |
| [External Integrations](openclaw/guides/external-integrations.md) | Google, Atlassian, Slack, Discord setup and usage |
| [Media Organization](openclaw/guides/media-organization.md) | Directory structure, naming conventions, backup rules |
| [Git Backup Strategy](openclaw/guides/git-backup-strategy.md) | What to version, .gitignore, automation, disaster recovery |
| [Ollama Setup](openclaw/guides/ollama-setup.md) | Step-by-step local (Docker) and cloud Ollama provider setup with quick-test agent and rollback |

Full index: [openclaw/guides/README.md](openclaw/guides/README.md)

### Good Practices

[`openclaw/security/good-practices/openclaw-agent-hardening.md`](openclaw/security/good-practices/openclaw-agent-hardening.md) covers:

- Inbound message security (untrusted data, indirect injection)
- Config file protection and version control
- Tool and permission hardening (least privilege, Docker socket, MCP scoping)
- Secrets management (.env, billing alerts)
- Agent allowlisting
- Prompt injection defense patterns with real examples

---

Maintained by [@fhgomes](https://github.com/fhgomes)
