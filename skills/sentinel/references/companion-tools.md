# Companion Tools (optional)

Sentinel's own audit (the domains in `SKILL.md` and the checklists in `playbooks.md` and
`coding-agents-hardening.md`) always runs first and stands on its own. The tools below are an
**optional second opinion**: open-source scanners the user can choose to run alongside it.
Offer them; never require them.

Every tool here is free, open source (except where a license caveat says otherwise), runs
locally and was maintained at the time of review. Licenses and latest releases were checked
at the source on **2026-11-18** (GitHub API `license` and `releases/latest`, or the project
site where noted). "Tested" means the pinned release was downloaded, its checksum or signature
verified, `--version`/`--help` run, and, for file-based tools, run against deliberately weak
fixtures (a Dockerfile, a compose file, a GitHub workflow, an sshd_config, agent config files
with fake tokens) on Ubuntu 24.04 x86_64. "Not tested" says why.

## Which one for which audit

| Audit (Sentinel domain) | Default | Also worth offering | What the tool adds over the skill alone |
|---|---|---|---|
| Host hardening (A) | **Lynis** | OpenSCAP (compliance profiles), osquery (ad-hoc SQL over host state) | Hundreds of scripted checks and a hardening index in a few minutes |
| File integrity (H) | **AIDE** | none | A hash baseline that later shows exactly which files changed |
| SSH crypto (A) | **ssh-audit** | none | Algorithm-by-algorithm verdicts and built-in hardening policies |
| TLS / nginx (B) | **testssl.sh** | none | Full protocol, cipher and TLS-vulnerability matrix of the live endpoint |
| Exposure from outside (A, B, F) | none by default | nmap (license caveat), Nuclei (active, noisy) | Proof of what the internet actually reaches |
| Dockerfiles, images (C) | **Trivy** (`config`, `image`) + **hadolint** | Grype + Syft, Dockle, Docker Bench for Security | CVEs in image packages, Dockerfile lint, CIS checks |
| IaC (C, G) | **Checkov** | Trivy `config` | Policy checks for Terraform, Kubernetes, Dockerfile, Helm and more |
| CI: GitHub Actions (G, J) | **zizmor** + **actionlint** | Checkov `github_actions` | Template injection, dangerous triggers, unpinned actions, workflow syntax |
| Application code (D) | **Semgrep CE** | none | Pattern-based SAST with rules the user can read and write |
| Secrets in repos, CI gate (G) | **gitleaks** | Betterleaks | Regex + entropy detection over tree and history; fails the build |
| Coding-agent environments (J) | **gitleaks** `dir` on agent files + **zizmor** | Trivy `fs --scanners secret` | Finds literal tokens in `settings.local.json`, `.mcp.json` and similar |
| AI / MCP (I) | none by default | Cisco MCP Scanner (YARA analyzer only) | Pattern scan of MCP tool definitions |

Docker Compose files: none of the tested tools (Trivy, Checkov, hadolint) analysed the weak
`compose.yaml` fixture; they only reported on the Dockerfile next to it. Compose review stays
with the skill's own Docker Compose playbook. KICS (Apache-2.0) documents Compose support but
ships as a container image or source only; not tested here.

## Installing safely (applies to every release binary below)

Never pipe a download straight into a shell. Prefer the distro package when it is recent enough; otherwise download a
**pinned** release plus its checksum file, verify, and extract into an empty directory:

```bash
VER=0.76.2                     # pin; never "latest"
BASE=https://github.com/aquasecurity/trivy/releases/download/v${VER}
mkdir -p ~/tools/dl/trivy && cd ~/tools/dl/trivy
curl -fsSLO "$BASE/trivy_${VER}_Linux-64bit.tar.gz"
curl -fsSLO "$BASE/trivy_${VER}_checksums.txt"
sha256sum --ignore-missing -c "trivy_${VER}_checksums.txt"   # must print: OK
mkdir -p ../../trivy-${VER} && tar -xzf "trivy_${VER}_Linux-64bit.tar.gz" -C ../../trivy-${VER}
```

The same pattern works with `gh release download v${VER} -R owner/repo -p '<asset>' -p '<checksums>'`.
Python tools: a dedicated virtualenv with an exact version (`pip install 'checkov==3.4.5'`).
Container images, if used: an exact tag or, better, a digest.

**Supply-chain note (Trivy, March 2026).** Advisory GHSA-69fq-xp46-6x23: compromised credentials
were used to publish a malicious Trivy v0.69.4 release, force-push 76 of 77 `trivy-action` tags
and all `setup-trivy` tags to credential-stealing code, and later push malicious v0.69.5/v0.69.6
Docker Hub images. Lessons that apply to every tool here: verify checksums, pin GitHub Actions
by full commit SHA (not by tag), pin images by digest.

---

## Host audit

### Lynis (default for A)
- **Adds:** hundreds of scripted checks (auth, SSH, kernel, file permissions, services, logging) with
  warnings, suggestions and a hardening index.
- **License:** GPL-3.0. **Version:** 3.1.7 (released 2026-06-25). Distro packages are often
  older (Ubuntu 24.04 ships 3.0.9).
- **Install:** distro package, CISOfy's signed package repository, or the tarball from
  `https://downloads.cisofy.com/lynis/lynis-3.1.7.tar.gz` with the SHA-256 published on
  `https://cisofy.com/downloads/lynis/`
  (`b5314a07fd85fa3ffc7da57b508f0108ec3280d84e4af823f805d95cbbc2428c`). Runs from the extracted
  directory, no install needed.
- **Command (read-only):**
  ```bash
  sudo lynis audit system --quick --no-colors \
    --report-file /tmp/lynis-report.dat --log-file /tmp/lynis.log
  lynis audit system --pentest --quick     # unprivileged, reduced coverage
  ```
- **Root:** recommended (many checks read root-only files). Lynis does not change the system.
- **Reading results:** `grep -E '^(warning|suggestion)\[\]=' /tmp/lynis-report.dat` and
  `grep hardening_index /tmp/lynis-report.dat`. Each item has a test ID (e.g. `SSH-7408`) whose
  page on cisofy.com explains it. Treat suggestions as leads and rank by real risk.
- **Caveats:** light load, a few minutes. Upstream default does a DNS TXT lookup to check for a
  newer version (Debian/Ubuntu packages set `skip-upgrade-test=yes`); `--upload` is the
  commercial feature and is never needed.
- **Tested:** checksum verified, `show version` and `show options`. Not run as an audit here
  (the test machine is a production server).

### OpenSCAP (optional, compliance)
- **Adds:** evaluation against formal profiles (CIS, STIG, ANSSI) with an HTML report, using
  ComplianceAsCode content.
- **License:** LGPL-2.1 (scanner), BSD-3-Clause (ComplianceAsCode content). **Version:** 1.4.6
  (2026-10-22); content v0.1.82 (2026-09-01). Ubuntu 24.04 ships 1.3.9 and very old content.
- **Install:** distro package `openscap-scanner`; content from the ComplianceAsCode release
  (`scap-security-guide-0.1.82.zip` with its `.sha512`, ~180 MB; the `.tar.bz2` is ~9 MB).
- **Command (read-only, no `--remediate`):**
  ```bash
  oscap info ssg-ubuntu2404-ds.xml                      # list the real profile IDs
  sudo oscap xccdf eval --profile <profile-id-from-info> \
    --results /tmp/oscap.xml --report /tmp/oscap.html ssg-ubuntu2404-ds.xml
  ```
- **Root:** yes. **Reading:** the HTML report lists pass/fail per rule with rationale.
- **Caveats:** content must match the distro release; profiles are compliance-driven, so many
  fails are policy choices rather than risk. Moderate CPU for several minutes.
- **Not tested here:** needs a system install and a root run against the live host.

### osquery (optional, ad-hoc questions)
- **Adds:** SQL over host state, handy for one precise question.
- **License:** Apache-2.0 OR GPL-2.0-only (dual). **Version:** 5.24.1 (2026-10-29).
- **Install:** the project's signed package repository, or the `.deb`/`.rpm`/tarball from the
  GitHub release (no checksum file is attached to the release, so record the SHA-256 you
  downloaded and pin the version).
- **Command (read-only):**
  ```bash
  sudo osqueryi --json "SELECT p.name, l.address, l.port FROM listening_ports l
                        JOIN processes p USING (pid) WHERE l.address NOT IN ('127.0.0.1','::1');"
  sudo osqueryi --json "SELECT * FROM suid_bin;"
  ```
- **Root:** for complete tables. **Caveats:** `osqueryi` makes no network calls unless TLS
  plugins are configured; the daemon (`osqueryd`) is a service, not a one-shot.
- **Tested:** package extracted locally, `--version` and `--help`. Queries not run (they would
  audit the live host).

### AIDE (default for H, integrity)
- **Adds:** a hash baseline; the second run shows added, removed and changed files.
- **License:** GPL-2.0. **Version:** 0.19.5 upstream (2026-10-22); tested the Ubuntu 24.04
  package 0.18.6.
- **Install:** distro package `aide`.
- **Command:**
  ```bash
  sudo aide --config-check -c /etc/aide/aide.conf
  sudo aide --init  -c /etc/aide/aide.conf          # writes aide.db.new; move it to aide.db
  sudo aide --check -c /etc/aide/aide.conf          # read-only comparison
  ```
- **Reading:** a summary (added/removed/changed) and per-file lines. Exit code is a bitmask:
  1 added, 2 removed, 4 changed (the fixture run with one added and one changed file exited 5).
- **Caveats:** `--init` hashes everything configured: heavy disk I/O, run off-peak. The
  baseline is only trustworthy if stored where an intruder cannot rewrite it (read-only media
  or off-host). Not a one-shot audit: its value starts at the second run.
- **Tested:** `--config-check`, `--init`, `--check` against a fixture directory with its own
  config; a file was added and one modified, both reported.

### rkhunter / chkrootkit (excluded)
Signature-based rootkit checks with a high false-positive rate. rkhunter's last release is
1.4.6 (2018, per SourceForge); chkrootkit 0.60 (chkrootkit.org). Lynis and AIDE cover the
useful part; suspected compromise is incident response, not a companion scan.

---

## SSH, TLS and exposure

### ssh-audit (default for SSH crypto)
- **Adds:** per-algorithm verdicts (kex, host keys, ciphers, MACs) and built-in hardening
  policies per distro.
- **License:** MIT. **Version:** 3.9.0 (2026-07-04). Distro packages lag (Ubuntu 24.04: 3.1.0).
- **Install:** `pip install 'ssh-audit==3.9.0'` in a venv, or the release tarball
  `v3.9.0.tar.gz` with `v3.9.0.tar.gz.sig` and the author's key attached to the release
  (`gpg --verify` reported a good signature from key fingerprint
  `CFA2 DF74 CC38 D1F0 A747 6748 42DA 6508 C11B D64E`).
- **Commands:**
  ```bash
  # offline: judge the algorithms of a config file without connecting
  algs=$(awk 'tolower($1) ~ /^(kexalgorithms|ciphers|macs|hostkeyalgorithms)$/ {print $2}' \
         /etc/ssh/sshd_config | paste -sd, -)
  ssh-audit --lookup="$algs"
  # better input on a server: the effective config
  sudo sshd -T | awk '$1 ~ /^(kexalgorithms|ciphers|macs|hostkeyalgorithms)$/ {print $2}' | paste -sd, -

  # active (owned/authorized host only), always skip the DHEat rate test
  ssh-audit --skip-rate-test -j 203.0.113.10 > ssh-audit.json
  ssh-audit --skip-rate-test -P "Hardened Ubuntu Server 24.04 LTS (version 2)" 203.0.113.10
  ssh-audit -L                                    # list built-in policies
  ```
- **Root:** no. **Reading:** `[fail]` = remove now, `[warn]` = weak or not post-quantum,
  `[info]` = context.
- **Caveats:** without `--skip-rate-test` it deliberately opens many connections to test
  DHEat exposure, which trips SSH rate limits (`ufw limit`, fail2ban) and can lock the
  auditor's IP out. Run against your own servers only.
- **Tested:** signature verified, `--help`, `-L`, and `--lookup` on the algorithms of the weak
  sshd_config fixture (7 `[fail]` verdicts). Remote audit not tested (no network scans from the
  test machine).

### testssl.sh (default for TLS / nginx)
- **Adds:** protocols, ciphers, certificate chain, HSTS and known TLS vulnerabilities
  (Heartbleed, ROBOT, etc.) of the live endpoint.
- **License:** GPL-2.0. **Version:** 3.2.5 (2026-11-04). Ubuntu 24.04 ships 3.2~rc3.
- **Install:** `git clone --depth 1 --branch v3.2.5 https://github.com/testssl/testssl.sh`
  (the project publishes no checksum file; pin the tag). The tree bundles its own test OpenSSL
  build in `bin/`.
- **Command (owned/authorized host only):**
  ```bash
  ./testssl.sh --quiet --warnings batch --severity MEDIUM \
    --jsonfile-pretty /tmp/tls.json https://example.com
  ./testssl.sh --quiet --ip 203.0.113.10 https://example.com   # test the origin behind a CDN
  ```
- **Root:** no. **Reading:** severity per finding (`OK`, `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`);
  start with `HIGH`/`CRITICAL` and the protocol section.
- **Caveats:** hundreds of handshakes over several minutes; a CDN or WAF may rate-limit or flag
  it. OCSP/CRL lookups only with `--phone-out` (off by default).
- **Tested:** `--version`, `--help`. Not run against any host.

### nmap (optional; license caveat)
- **Adds:** proof of which ports the internet reaches (the `docker-proxy` bypass in domain C).
- **License:** **Nmap Public Source License (NPSL) 0.95**. It is source-available and free to
  use, but **not OSI-approved** and not on the OSI license list; it prohibits redistributing or
  embedding Nmap in proprietary products without the commercial OEM license. Using it to scan
  your own servers is fine; shipping it inside a product is not. GitHub reports the license as
  `NOASSERTION`. Latest is 7.993 (nmap.org); Ubuntu 24.04 ships an older 7.94 snapshot.
- **Install:** distro package, or source/RPM from nmap.org with the published signatures.
- **Command (from a machine outside the server, owned/authorized target only):**
  ```bash
  nmap -sT -Pn --top-ports 1000 -T3 -oA /tmp/ext-scan 203.0.113.10
  nmap -sT -Pn -sV -p 22,80,443 203.0.113.10
  ```
- **Root:** not for `-sT` (connect scan). **Caveats:** active scanning; providers and IDSs flag
  it; scan from outside, since a scan from the host itself does not show the firewall's effect.
- **Not tested here:** network scanning is out of bounds on the test machine.

### Nuclei (optional, advanced)
- **Adds:** thousands of community templates for exposed panels, misconfigurations and known
  CVEs on web endpoints.
- **License:** MIT. **Version:** 3.11.1 (2026-08-08).
- **Install:** release zip + `nuclei_<ver>_checksums.txt`.
- **Command (owned/authorized host only):**
  ```bash
  nuclei -u https://example.com -duc -ni -rl 10 -severity medium,high,critical \
    -etags dos,fuzz,intrusive -silent -jsonl -o /tmp/nuclei.jsonl
  ```
- **Root:** no. **Caveats:** actively sends exploit-like requests; downloads a large template
  repository on first scan; `-ni` disables Interactsh (otherwise it uses third-party OAST
  callback servers); default rate is 150 requests/s (`-rl` lowers it); never use `-dashboard`
  (uploads results to the vendor cloud). Even `-version` creates `~/.config/nuclei`.
- **Tested:** checksum, `-version`, `-h`. Not run against any host; templates not downloaded.

---

## Containers and images

### Trivy (default for C)
- **Adds:** CVEs in image and filesystem packages, Dockerfile/IaC misconfiguration, secrets,
  in one binary.
- **License:** Apache-2.0. **Version:** 0.76.2 (2026-11-05). See the supply-chain note above.
- **Install:** release tarball + `trivy_<ver>_checksums.txt` (or the signed apt/rpm
  repository).
- **Commands (always add the privacy flags):**
  ```bash
  P="--disable-telemetry --skip-version-check"
  trivy config $P --skip-check-update --exit-code 1 /path/to/repo        # no DB needed
  trivy fs $P --scanners misconfig,secret --exit-code 1 /path/to/repo    # no DB needed
  trivy image $P --severity HIGH,CRITICAL --ignore-unfixed registry.example.com/app:1.2.3
  trivy image $P --input app.tar        # a saved image, no daemon access
  ```
- **Root:** no (image scans need access to the Docker socket or a saved tarball).
- **Reading:** findings grouped by target with IDs (`DS-0002`, CVE IDs) and severity; exit code
  0 unless `--exit-code` is set.
- **Caveats:** vulnerability scans download the vulnerability DB (**~140 MB compressed**,
  measured 2026-11-18, larger on disk; refreshed every run unless `--skip-db-update`). Trivy
  sends anonymous usage telemetry by default (`--disable-telemetry`) and checks for updates
  (`--skip-version-check`). Scanning a large image is CPU- and I/O-heavy; on a production box
  scan a saved tarball elsewhere or in CI.
- **Tested:** `config` and `fs --scanners misconfig,secret` on the fixtures: 6 Dockerfile
  failures (root user, secret in `ENV`, port 22, missing tag...) and the fake GitHub, GitLab
  and Slack tokens in the agent config files. Vulnerability DB not downloaded (over the size
  budget), so `image` and `fs --scanners vuln` were not tested.

### Grype + Syft (alternative to Trivy for CVEs)
- **Adds:** SBOM generation (Syft) and CVE matching (Grype) from another vendor; useful as a
  cross-check, or where Trivy is not wanted after its 2026 incident.
- **License:** Apache-2.0 (both). **Versions:** Grype 0.122.0, Syft 1.57.2 (2026-11-16).
- **Install:** release tarballs + `*_checksums.txt`.
- **Commands:**
  ```bash
  export SYFT_CHECK_FOR_APP_UPDATE=false GRYPE_CHECK_FOR_APP_UPDATE=false
  syft scan dir:/path/to/repo -o cyclonedx-json=sbom.json
  syft scan registry.example.com/app:1.2.3 -o cyclonedx-json=sbom.json
  grype sbom:sbom.json --only-fixed --fail-on high -o table
  ```
- **Root:** no. **Reading:** one row per package/CVE with the fixed version; `--fail-on` exits 2.
- **Caveats:** Grype's DB is **~203 MB compressed** (measured 2026-11-18); both check for app
  updates unless disabled as above.
- **Tested:** checksums, versions; Syft produced a CycloneDX SBOM from a fixture
  `requirements.txt`. Grype matching not tested (DB over the size budget).

### hadolint (default Dockerfile linter)
- **Adds:** Dockerfile best-practice rules plus ShellCheck on `RUN` lines.
- **License:** GPL-3.0. **Version:** 2.15.1 (2026-07-31).
- **Install:** single static binary `hadolint-linux-x86_64` + `checksums.sha256`.
- **Command:** `hadolint --failure-threshold warning Dockerfile` (`-f json` for machines).
- **Root:** no. **Reading:** rule ID (`DL3007`, `DL4006`...), severity, line. Exit 1 on findings.
- **Tested:** on the weak Dockerfile: `latest` tag, secret in `ENV`, unpinned apt packages,
  missing `pipefail`.

### Dockle (optional)
- **Adds:** CIS-style checks on a built image (user, setuid files, secrets in env, healthcheck).
- **License:** Apache-2.0. **Version:** 0.4.15 (released 2025-01-06; no release since, so treat
  as lightly maintained). Trivy's `--image-config-scanners misconfig,secret` covers much of it.
- **Command:** `dockle --exit-code 1 --exit-level warn registry.example.com/app:1.2.3` or
  `dockle --input app.tar`.
- **Tested:** checksum, `--version`, `--help`. Not run (needs a built image).

### Docker Bench for Security (optional)
- **Adds:** the CIS Docker Benchmark against the live daemon, host and running containers.
- **License:** Apache-2.0. **Version:** 1.6.1 (released 2023-12-20, based on CIS Docker
  Benchmark 1.6.0): dated, read results against the current benchmark.
- **Install:** the tag tarball; the release attaches `docker-bench-security.sha256` covering
  each script (`sha256sum -c` from the extracted directory).
- **Command (read-only checks):**
  ```bash
  sudo sh docker-bench-security.sh -b -l /tmp/docker-bench.log
  sudo sh docker-bench-security.sh -b -c container_images,container_runtime
  ```
- **Root:** yes (or docker group, which is root-equivalent). **Caveats:** inspects every running
  container; prefer the script over the container form, which needs host PID/network and the
  Docker socket.
- **Tested:** checksums of all 15 scripts, `-h`. Not run (would inspect a live daemon).

---

## IaC and CI

### Checkov (default for IaC)
- **Adds:** a large policy library for Terraform, Kubernetes, Helm, CloudFormation, Dockerfile,
  GitHub Actions and more.
- **License:** Apache-2.0. **Version:** 3.4.5 (2026-11-12).
- **Install:** `pip install 'checkov==3.4.5'` in a venv.
- **Command:** `checkov -d /path/to/repo --skip-download --compact --quiet`
  (`--framework terraform,kubernetes,dockerfile,github_actions` to narrow).
- **Root:** no. **Reading:** `CKV_*` check IDs with the failing resource; exit 1 on failures.
- **Caveats:** `--skip-download` stops calls to the vendor platform (guidelines, severities);
  never pass an API key unless the user wants results in that platform.
- **Tested:** on the fixtures: 6 Dockerfile failures, and 2 on the weak workflow (shell
  injection, `write-all`); the workflow was only picked up when scanning from the repo root.
  It did not report the `pull_request_target` checkout or unpinned actions; zizmor did.

### zizmor (default for GitHub Actions)
- **Adds:** security-specific audits: template injection, dangerous triggers, excessive
  permissions, unpinned actions, credential persistence.
- **License:** MIT. **Version:** 1.32.0 (2026-11-02).
- **Install:** `pip install 'zizmor==1.32.0'` (or release binary).
- **Command:** `zizmor --offline .` or `zizmor --offline --format sarif .github/workflows/`
- **Root:** no. **Reading:** each finding has an audit name, severity, confidence and the
  offending lines; exit code 10+ when findings exist (14 for high on the fixture).
- **Caveats:** with a GitHub token in the environment it runs online audits (API calls);
  `--offline` prevents that.
- **Tested:** on the weak workflow: dangerous trigger, template injection, `write-all`,
  unpinned actions, persisted checkout credentials.

### actionlint (companion to zizmor)
- **Adds:** workflow syntax and expression checks (and ShellCheck on `run:` if installed).
- **License:** MIT. **Version:** 1.7.12 (2026-03-30).
- **Command:** `actionlint -no-color .github/workflows/*.yml`. Exit 1 on findings.
- **Tested:** caught the untrusted `github.event.issue.title` in `run:`, an undefined property,
  and (first fixture draft) a YAML parse error.

### Semgrep CE (default for application code, domain D)
- **Adds:** SAST with readable rules (SQL injection, unsafe deserialization, weak crypto).
- **License:** LGPL-2.1 (engine). **Version:** 1.185.0 (2026-11-10). Registry rules have their
  own license terms; check before redistributing them.
- **Install:** `pip install 'semgrep==1.185.0'` in its own venv (~350 MB installed).
- **Commands:**
  ```bash
  semgrep scan --metrics=off --disable-version-check --config rules/ --error /path/to/src
  semgrep scan --metrics=off --config p/java --config p/secrets /path/to/src  # downloads rules
  ```
- **Root:** no. **Reading:** rule ID, message, file:line; `--error` exits 1 on findings.
- **Caveats:** metrics are sent by default whenever rules come from the registry;
  `--metrics=off` disables them. `--config auto` requires metrics, so use explicit packs.
  Memory-hungry on big repos.
- **Tested:** with a local rule on a Java fixture that concatenates SQL: one blocking finding.

### gitleaks (default secret scanner and CI gate)
- **Adds:** secret detection over the tree and the full git history.
- **License:** MIT. **Version:** 8.30.1 (2026-03-21). Ubuntu 24.04 ships 8.16.0.
- **Commands:**
  ```bash
  gitleaks dir /path/to/dir --redact --no-banner
  gitleaks git /path/to/repo --redact --no-banner --report-format sarif --report-path leaks.sarif
  ```
- **CI gate:** download the pinned binary + checksum in the job and run `gitleaks git --redact`;
  the official `gitleaks-action` needs a license key for organization accounts.
- **Root:** no. **Reading:** rule ID, file, line, commit; exit 1 when leaks are found. Always
  `--redact` so values do not land in logs.
- **Tested:** `dir` mode on the agent fixtures: 4 of 4 fake secrets (GitHub PAT, GitLab PAT,
  Slack bot token, a literal `PGPASSWORD` caught by the generic rule).

### Betterleaks (alternative)
- **Adds:** a newer, actively released scanner with the same command shape and optional live
  validation.
- **License:** MIT. **Version:** 1.10.1 (2026-11-12); `checksums.txt` is sigstore-signed.
- **Command:** `betterleaks dir /path/to/dir --redact --no-banner` (or `git`).
- **Caveats:** `--validation` sends found secrets to the provider APIs to check if they are
  live: never enable it without explicit consent.
- **Tested:** same fixtures: 3 of 4 (missed the generic `PGPASSWORD` literal that gitleaks
  caught).

---

## Coding-agent environments (domain J) and MCP (domain I)

No dedicated, fully local scanner for coding-agent configuration was found that beats the
checklist in `coding-agents-hardening.md`. What genuinely helps:

```bash
# literal credentials in agent files (project and user level)
gitleaks dir .claude --redact --no-banner
gitleaks dir .mcp.json --redact --no-banner
gitleaks dir ~/.claude --redact --no-banner        # includes transcripts: can be large
trivy fs --disable-telemetry --skip-version-check --scanners secret .
# CI where agents run
zizmor --offline .
```

All tested on fixtures (see gitleaks, Trivy and zizmor above).

**Cisco MCP Scanner (optional for domain I).** Apache-2.0, version 4.8.7 (2026-10-20). Its
YARA analyzer runs locally; its LLM and Cisco AI Defense analyzers send tool definitions to
external services, and `--scan-known-configs` connects to the configured MCP servers, which for
stdio servers means **launching them** (running their code). Use `--analyzers yara` only, on
configs the user would run anyway. Not tested here (heavy Python dependency set).

**Excluded:** Snyk Agent Scan (formerly mcp-scan, Apache-2.0): requires a Snyk account token
and sends component data (tool descriptions, skill content) to the vendor API, so it is not a
local tool. Agentic Radar (Apache-2.0): analyses agent framework source code, not coding-agent
environments.

---

## Runtime defence (not companions)

fail2ban (GPL-2.0, 1.1.1) and CrowdSec (MIT, v1.8.2) are services to install and tune, not
scanners to run once; the skill covers them in domains A and H. If they are already installed,
reading their state is part of the audit: `sudo fail2ban-client status sshd`,
`sudo cscli decisions list`, `sudo cscli alerts list`.

## Sources

- Each project's GitHub repository (`/license`, `/releases/latest`), checked 2026-11-18.
- Trivy advisory GHSA-69fq-xp46-6x23 and `docs/guide/advanced/telemetry.md`.
- cisofy.com/downloads/lynis (checksum), nmap.org/download and nmap.org/npsl (license),
  opensource.org/licenses (NPSL absent), SourceForge (rkhunter), chkrootkit.org.
- Vulnerability DB sizes: Grype `databases/v6/latest.json` + HEAD of the archive; Trivy DB OCI
  manifest on ghcr.io.
