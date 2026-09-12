# Warden — Malware & Threat Analysis Specialist

**SKILL.md** — Drop-in skill for any OpenClaw-compatible agent.

## What it does

Warden hunts **malicious content** — malware, trojans, backdoors, webshells, ransomware,
cryptominers, infostealers and obfuscated code — inside files, folders, repositories
(PoCs), URLs, executables, scripts and dependencies.

It is not an antivirus that prints "clean/infected". It is the analyst that opens the
file, reads the bytes, decodes the base64, follows the C2, and tells you **what it does,
what it already did, and what to do now**.

**Core rule: it analyzes, it never executes.** All analysis is static by default.

**Targets:**
- Single file — identification, hashing, signature, Defender scan, strings, deobfuscation
- Folder / repo / PoC — auto-executing files first (`postinstall`, `setup.py`, CI workflows), committed binaries, hidden payloads
- URL / site — headers and redirect chain without rendering, phishing and typosquatting checks
- Running process — suspicious paths, network connections, persistence
- Dependencies — npm/pip supply-chain, typosquatting, install hooks

**Verdict is calibrated, never binary:** MALICIOUS / SUSPICIOUS / UNKNOWN / PUA / CLEAN,
always with confidence level and the scope actually analyzed. "CLEAN" means "nothing found
with what I ran" — never "guaranteed safe".

## What's inside

- `SKILL.md` — full skill definition (identity, 6-step triage flow, targets, ethics)
- `references/static-analysis.md` — playbook per artifact type: PE/EXE, scripts, Office, PDF, archives, npm/pip, Docker
- `references/url-triage.md` — URL, domain and phishing analysis
- `references/incident-response.md` — compromised host: containment, scope, credential rotation, eradication
- `references/ioc-patterns.md` — catalog of suspicious patterns, each with its false positive
- `scripts/scan_tree.py` — static folder/repo scan, 26 rules, risk-ranked findings
- `scripts/deobfuscate.py` — layered deobfuscation (base64, UTF-16LE, hex, charcode, gzip, XOR) without executing code

Both scripts are **stdlib-only Python** — no dependencies to install.

This folder is **self-contained** — copy it into any runtime that loads a SKILL.md
(Claude, OpenClaw, custom agents) and it works as-is.

## Usage

```bash
# scan a folder, repo or downloaded PoC
python3 scripts/scan_tree.py /path/to/suspicious --min-score 4

# decode a payload without running it
python3 scripts/deobfuscate.py --string 'BASE64HERE'
python3 scripts/deobfuscate.py suspicious.ps1
python3 scripts/deobfuscate.py file.js --extract   # list encoded blobs only
```

## See also (optional)

- [sentinel](../sentinel/) — infrastructure hardening (nginx, SSH, Docker, firewall). Warden asks *"is this file malicious?"*; Sentinel asks *"how do I protect my server?"*
- [redact](../redact/) — secret and PII exposure before publishing a repo

## Trigger keywords

`malware`, `virus`, `trojan`, `backdoor`, `webshell`, `ransomware`, `cryptominer`,
`stealer`, `RAT`, `keylogger`, `payload`, `dropper`, `obfuscated`, `reverse shell`, `C2`,
`phishing`, `typosquatting`, `postinstall script`, `IoC`, `YARA`, `sandbox`,
`is this file safe?`, `is this link malicious?`, `is my PC infected?`

Also triggers on the equivalent phrases in other languages.
