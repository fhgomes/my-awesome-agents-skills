# Redact — Privacy & Secret Exposure Auditor

**SKILL.md** — Drop-in skill for any OpenClaw-compatible agent.

## What it does

Redact answers one question: **"if this repository goes public right now, what leaks?"**

It audits code and git history for secrets and sensitive data before publication —
and it does not stop at pointing: it delivers the finding, the impact, the remediation
command, the correct pattern to replace it with, and the rotation instruction.

**A secret removed but not rotated is still valid.** That is the whole point.

**What it finds:**
- **Secrets** — cloud keys (AWS/GCP/Azure), platform tokens (GitHub, GitLab, Slack, Stripe, OpenAI, Anthropic, SendGrid), private keys, connection strings with embedded passwords, hardcoded credentials
- **Personal data** — PII (Brazilian CPF/CNPJ/RG/CNH validated by check digits, phone, email, address), PCI (card numbers validated by Luhn, CVV), PHI (health data)
- **Internal infra** — private IPs, internal hostnames, paths revealing OS usernames
- **Dangerous files** — `.env`, `*.pem`, `id_rsa`, `credentials.json`, `*.tfstate`, DB dumps

**The differentiator is `--history`.** A secret deleted from HEAD still lives in git
history and leaks exactly the same. The scanner walks the blobs added in each commit
and names the exact commit where the secret entered.

## Two axes that decide the remediation

Every finding is classified on two independent axes — confusing them leads to the wrong fix:

**Where is it?** working tree (just edit) → committed in HEAD (editing is not enough) →
in history (deleting the file does not remove it) → already published (assume leaked).

**What is it?** live secret (rotate) / dead secret (just clean) / personal data (there is
no "rotate" — it belongs to a real person) / internal infra.

Order that never changes: **rotate → remove from code → clean history → prevent.**

## What's inside

- `SKILL.md` — full skill definition (two axes, audit flow, verdict format, legal limits)
- `references/detection-patterns.md` — pattern catalog: secrets, PII/PCI/PHI, infra, each with its false positive
- `references/remediation.md` — secret extraction per stack (Spring Boot, Node, Python, Docker, CI) + `.env.example`
- `references/history-rewrite.md` — git history cleanup (filter-repo, BFG, filter-branch) and its real limits
- `references/prevention.md` — `.gitignore`, tested pre-commit hook, GitHub push protection, pre-publication checklist
- `scripts/scan_secrets.py` — self-contained scanner: working tree + git history, Luhn and CPF check-digit validation, entropy, masked output

**Stdlib-only Python** — no gitleaks, trufflehog or detect-secrets required.

This folder is **self-contained** — copy it into any runtime that loads a SKILL.md
(Claude, OpenClaw, custom agents) and it works as-is.

## Usage

```bash
# working tree only
python3 scripts/scan_secrets.py /path/to/repo

# including git history — ALWAYS run this before making a repo public
python3 scripts/scan_secrets.py /path/to/repo --history

# blockers only
python3 scripts/scan_secrets.py /path/to/repo --history --severity high

# machine-readable
python3 scripts/scan_secrets.py /path/to/repo --history --json
```

## False positives are the priority

An audit nobody trusts gets ignored. The scanner therefore:
- validates CPF by check digits and cards by Luhn
- recognizes `process.env.X`, `${DB_PASSWORD}`, `os.environ[...]` as the **correct pattern**, not a leak
- filters placeholders (`your-api-key`, `changeme`, `xxx`) and low-entropy values
- downgrades severity inside `tests/`, `fixtures/` and docs, without hiding the finding
- **never prints the full secret** — always masked (`AKIA****...MPLE`), including inside snippets

On a correctly written repo: zero findings.

## See also (optional)

- [sentinel](../sentinel/) — infrastructure hardening
- [warden](../warden/) — malicious content analysis. Redact asks *"what leaks if I publish?"*; Warden asks *"is this file malicious?"*

## Trigger keywords

`secret`, `API key`, `leaked token`, `hardcoded password`, `private key`, `.env committed`,
`connection string`, `PII`, `PCI`, `PHI`, `LGPD`, `GDPR`, `git history`, `rewrite history`,
`BFG`, `filter-repo`, `make repo public`, `open source this`, `is it safe to publish?`

Also triggers on the equivalent phrases in other languages.
