# Companion Tools (optional)

Warden works fully on its own: agentic static triage plus `scripts/scan_tree.py` and
`scripts/deobfuscate.py`, stdlib only. The tools below are **optional second opinions**. Each
one is free, open source under an OSI-approved license, runs locally and is maintained.

Verified on **2026-11-18**: license via the GitHub API, latest release and date, checksum of the
downloaded release, and the documented command run on inert test fixtures (a hostile repo with
agent config, a benign repo, a legacy sample folder with a webshell, a PowerShell dropper, a
Python stealer and a fake `MZ` file). Every test ran inside a no-network sandbox, so a result
marked **tested** also proves that the command works offline. Newer releases are fine: verify
their checksum the same way before using them.

Ground rules (the same as in `SKILL.md`):
- Static modes only. Nothing here executes the sample. Anything that would (starting an MCP
  server, `npm install`, dynamic sandboxes) runs only inside an isolated, disposable sandbox,
  only when the user explicitly asks for it.
- A tool or mode that sends content out (vendor API, LLM, file upload) is **not offered by
  default**. Offer it only when the user names it, and say first exactly what will be sent.
- Label each finding with the tool it came from. A clean companion result **never** overrides
  the skill's own indicators. Several tools below returned "nothing found" on samples that were
  plainly hostile (see each "Tested" line).
- Never install without consent. Never claim to have run a tool that is not installed.

---

## Which one for which sample

| Sample | Default companion | Also useful | What the companion adds |
|---|---|---|---|
| **Binary** (PE, ELF, .NET, shellcode) | **capa** | YARA-X + rule set, FLOSS, Detect It Easy, ClamAV | Capabilities mapped to ATT&CK/MBC without running it; family/packer signatures |
| **Office document** (doc/xls/ppt, OOXML, RTF) | **oletools** (`olevba`, `oleid`) | YARA-X, exiftool | Extracts and classifies VBA/XLM macros, auto-exec triggers, IoCs, remote templates |
| **PDF** | **YARA-X** + rule set | exiftool | Known-exploit and dropper signatures; metadata (producer, dates, type mismatch) |
| **Script / webshell** (ps1, js, py, php, sh) | **YARA-X** + rule set | GuardDog (on the folder), oletools (`olevba` reads plain-text sources too) | Known webshell/loader signatures; GuardDog's capability + threat correlation |
| **Package / dependency** (npm, PyPI, Go, crates, gems, VS Code extension) | **GuardDog** | OSV-Scanner | Malicious-package heuristics on a local archive or folder; known-malicious `MAL-` advisories by name and version |
| **Whole repo / PoC** | the skill's own `scan_tree.py`, then **OSV-Scanner** on its lockfiles | YARA-X recursive, GuardDog if the repo is a package | Lockfile check against malicious-package advisories; signature sweep of committed blobs |
| **Docker image** | **Trivy** on a saved image tarball | YARA-X on the extracted layers | Known vulnerabilities, secrets and misconfig inside layers without running the container |
| **Agent config, MCP, skills** | the skill's own pass (target F) | **Cisco skill-scanner** (skills only, core mode) | A second rule engine for `SKILL.md` and its scripts. For `.mcp.json`, hooks and settings no offline tool beats the skill's own checks |

Firmware or blobs with embedded files: binwalk. File-type truth for any sample: exiftool or
Detect It Easy.

---

## Optional: proving a run stays offline

On Linux, `bwrap` (bubblewrap, packaged by most distributions, no root needed) runs a tool with
no network and a read-only view of the system:

```bash
bwrap --ro-bind / / --dev /dev --proc /proc --bind "$WORK" "$WORK" \
      --setenv TMPDIR "$WORK/tmp" --setenv HOME "$WORK/tmp" --unshare-net --die-with-parent \
      <tool> <args>
```

`$WORK` is a scratch folder outside the sample. PyInstaller-built tools (capa, FLOSS) need the
writable `TMPDIR`. Elsewhere, disconnect the analysis VM instead.

---

## Files and binaries

### YARA-X (`yr`) with an open rule set
- **Adds:** thousands of curated signatures for known malware families, webshells, loaders and exploit documents.
- **License:** BSD-3-Clause. **Tested:** 1.23.0 (released 2026-11-05).
- **Platforms:** Linux, macOS, Windows (release archives). Homebrew `yara-x`, Scoop `yara-x`.
- **Install:** release archive from `github.com/VirusTotal/yara-x/releases`, checked against the
  asset's SHA-256 digest shown on the release page (Linux x86_64 1.23.0:
  `da0c17f23fc743dcd44ad6d3135c906a4c0d197685b661c4cdc923c2f8967a64`). No root.
- **Rule sets** (the engine ships no rules):
  - **YARA Forge `core`** (`github.com/YARAHQ/yara-forge/releases`, package 20261115, 1.7 MB zip,
    5084 rules, SHA-256 `d8cbfc7940c688bd890f941c323f51940c54b46bb2a78143b55d312bab7581c6`). The
    default. An aggregator of 45+ vetted repositories; the tooling is GPL-3.0 and **each rule keeps
    its source's license** in its `license` meta field. In the tested package: 1621 CC BY-SA 4.0,
    383 Detection Rule License 1.1, 135 Volexity's own license, 57 BSD-2-Clause, others Apache-2.0,
    CC BY 4.0, MIT. Fine for local scanning; check the per-rule license before redistributing rules.
  - **ReversingLabs rules** (`github.com/reversinglabs/reversinglabs-yara-rules`, MIT, last commit
    2025-11-03). The single-license option, focused on PE malware families.
- **Command:**
  ```bash
  yr compile -w -o forge-core.yarc packages/core/yara-rules-core.yar   # once, about 5 s
  yr scan -C -r -s=40 --disable-console-logs forge-core.yarc <file-or-folder>
  yr scan -w -r <rules-folder> <file-or-folder>                         # uncompiled rules folder
  ```
  Windows: the same with `yr.exe`.
- **Read:** one line per match, `RULE_NAME path`, then with `-s` the offset, length, string id
  and matched bytes (`0x6:11:$geval: eval($_POST`). No output means no rule matched.
- **Tested:** yes, both rule sets. Forge core flagged the PHP webshell
  (`SIGNATURE_BASE_WEBSHELL_PHP_Generic_Eval`) and nothing else: not the PowerShell
  `-enc`/`DownloadString` dropper, not the Python stealer, not the hostile agent config. Signature
  coverage of scripts and agent config is thin; silence is not a verdict.
- **Caveats:** no network at scan time. False positives come mostly from generic rules (hack
  tools, packers, "suspicious string" rules) on dual-use software; read the rule before quoting it.
- Classic YARA (`VirusTotal/yara`, BSD-3-Clause, 4.6.0 released 2026-10-27) runs the same rules
  with `yara -r rules.yar <target>`; prefer YARA-X, which the YARA project presents as its successor.

### capa (Mandiant)
- **Adds:** what a binary *can do* (injection, persistence, C2, anti-analysis), mapped to ATT&CK
  and MBC, from static features.
- **License:** Apache-2.0 (rules too). **Tested:** 10.0.0 (released 2026-10-16).
- **Platforms:** Linux, macOS, Windows standalone builds; `pip install flare-capa`.
- **Install:** `capa-v10.0.0-<os>.zip` from `github.com/mandiant/capa/releases` (Linux zip 45 MB,
  SHA-256 `96cb5115f495024a478b0e9f9f77f9027058155589235fbd4c50e7382055fcca`). Rules embedded.
- **Command:** `capa <file>` (tested); `capa -v <file>` for matched addresses and `capa -j <file>`
  for JSON (from `--help`, not run here). Inputs: PE, ELF, .NET, raw shellcode (`-f sc32`/`sc64`).
- **Read:** a table of ATT&CK tactics/techniques, MBC behaviors and capability names with
  namespaces. A capability is not intent: `create TCP socket` is normal, `inject thread` plus
  `decode data using XOR` plus `persist via Run key` is a story.
- **Tested:** yes. On the fake `invoice.pdf.exe` it refused with "not a valid PE file ... Unable to
  read the DOS Header, possibly a truncated file", which is itself an indicator for a file posing
  as an executable.
- **Caveats:** no network observed. Packed samples show few capabilities (unpack first, or say so
  in scope). Slow on large binaries.

### FLOSS (Mandiant)
- **Adds:** strings that `strings` misses: stack strings, tight strings and strings decoded by
  routines inside the binary, recovered by emulation (vivisect), not by native execution.
- **License:** Apache-2.0. **Tested:** 3.2.0 (released 2026-10-16).
- **Platforms:** Linux, macOS, Windows standalone builds; `pip install flare-floss`.
- **Install:** `floss-v3.2.0-<os>.zip` from `github.com/mandiant/flare-floss/releases` (Linux zip
  42 MB, SHA-256 `c449366960b688769b6510662cd6db6a3bf9edada4e8a8878056becd324df52c`).
- **Command:** `floss <file>`; `floss --only static -- <file>` for plain static strings; `-j` for JSON.
- **Read:** sections per string type; the DECODED and STACK sections are the ones to grep for
  URLs, paths, registry keys and commands.
- **Tested:** `--only static` yes. Full mode on the truncated fake PE crashed with a Python
  traceback: fall back to `--only static` and record the failure in scope.
- **Caveats:** no network observed. Writes a vivisect config to `~/.envi`. Emulation is CPU-heavy
  on large binaries.

### oletools (`olevba`, `oleid`, `mraptor`, `rtfobj`, `msodde`)
- **Adds:** macro extraction and classification (auto-exec, suspicious keywords, IoCs, decoded
  strings), XLM macros, remote templates, DDE, embedded OLE objects in RTF.
- **License:** BSD-2-Clause (GitHub reports NOASSERTION; the license file is BSD 2-clause text).
  **Tested:** 0.60.2 (released 2024-07-02; the repository still receives commits, slowly).
- **Platforms:** Linux, macOS, Windows (pure Python).
- **Install:** in a virtual environment, `pip install oletools==0.60.2`.
- **Command:** `olevba <file>` (tested), `olevba -a --decode <file>` analysis only plus decoded
  strings (tested), `olevba -j <file>` JSON (not run), `oleid <file>` (tested).
- **Read:** the summary table (`AutoExec`, `Suspicious`, `IOC`, `Hex/Base64 String`). `AutoExec` +
  `Suspicious` (Shell, CreateObject, URLDownloadToFile) is the classic dropper.
- **Tested:** yes. `olevba` also reads plain-text sources: on the PowerShell dropper it flagged
  `powershell`, `DownloadString`, the URL and the IP; on the fake `.exe` it reported nothing.
  `oleid` produced its indicator table.
- **Caveats:** no network. Never opens the document in Office. Encrypted documents need the
  password (`msoffcrypto-tool` is a dependency).

### exiftool
- **Adds:** real file type versus extension, and metadata (author, producer, creation tool,
  timestamps, embedded thumbnails or documents) for images, PDFs, Office files and executables.
- **License:** GPL-3.0 (as detected by GitHub). **Tested:** 13.64.
- **Platforms:** Linux, macOS, Windows. Homebrew `exiftool`, Scoop `exiftool`, distribution packages.
- **Install:** `Image-ExifTool-<ver>.tar.gz` (Perl, no build) linked from `exiftool.org`, checked
  against `exiftool.org/checksums-<ver>.txt` (13.64 SHA2-256
  `dcb9f6be1f6705ee826a92d1522e3fec1d0b3749cdc061b03c46873d5fe204fc`).
- **Command:** `exiftool -a -G1 -s <file>`.
- **Read:** `FileType` / `MIMEType` against the name (tested: `invoice.pdf.exe` came back as `TXT`),
  then `Producer`, `Creator`, dates and any embedded-object tags.
- **Tested:** yes.
- **Caveats:** no network. Read only with these flags (never pass write options on evidence).

### Detect It Easy (`diec`)
- **Adds:** compiler, linker, packer, protector and installer identification for PE/ELF/Mach-O/APK.
- **License:** MIT. **Version checked:** 4.0.0 (released 2026-11-05).
- **Platforms:** Windows portable zip (`die_win64_*.zip`), Linux packages and AppImage, macOS.
- **Command:** `diec <file>`.
- **Read:** one line per detected component (`Packer: UPX`, `Compiler: ...`). A packer on a small
  "utility" is a reason to dig, not a verdict.
- **Not tested here:** the Linux AppImage contains only the GUI, and the `diec` console binary in
  the `.deb` needs system Qt5 libraries that would require a system-wide install.

### ClamAV (`clamscan`)
- **Adds:** a broad signature database for known malware, including archives and documents.
- **License:** GPL-2.0. **Version checked:** 1.5.4 (released 2026-08-07).
- **Platforms:** Linux, macOS, Windows (`.msi`/`.zip` on the release page, each with a `.sig`).
- **Command:** `freshclam` (downloads signatures), then `clamscan -r -i <file-or-folder>`.
- **Read:** `path: Signature.Name FOUND`; `-i` prints only infected files.
- **Not tested here:** the signature databases are well over 100 MB. `freshclam` downloads them
  from ClamAV's mirror; no sample content leaves the machine. Not useful on new or custom-built
  malware; PUA detection is off unless enabled.

### binwalk
- **Adds:** finds and optionally extracts files embedded in firmware, images and blobs.
- **License:** MIT. **Version checked:** 3.1.0 (released 2024-10-31; commits continue in 2026).
- **Platforms:** Linux, macOS (Homebrew `binwalk` 3.1.0); Windows not verified.
- **Command:** `binwalk <file>` (signature listing only). Extraction (`-e`) writes files and calls
  external extractors: do it in a disposable folder.
- **Not tested here:** no prebuilt release binary; it needs a package manager or a Rust build.

---

## Code and dependencies

### GuardDog (Datadog)
- **Adds:** malicious-package heuristics for npm, PyPI, Go, crates, RubyGems, GitHub Actions and
  VS Code extensions, correlating a capability (network, file read, process spawn) with a threat
  indicator (webhook, credential path, encoded exec) in the same file.
- **License:** Apache-2.0. **Tested:** 3.2.0 (released 2026-08-12). Python 3.10+.
- **Platforms:** Linux, macOS. Windows: Docker only, per the project
  (`ghcr.io/datadog/guarddog:v3.2.0@sha256:5b0804d480e83405120fc90c62b60ad844310418c836e567055b1ba8843e033d`).
- **Install:** in a virtual environment, `pip install guarddog==3.2.0` (about 120 MB installed).
- **Command (local, static):**
  ```bash
  guarddog npm  scan <package-folder-or-archive>
  guarddog pypi scan <package-folder-or-archive>
  guarddog pypi scan <folder> --output-format json
  ```
  Windows (not tested): `docker run --rm --network none -v "${PWD}:/scan:ro" <image@digest> npm scan /scan`.
- **Read:** risks grouped by stage (Post-compromise, Exfiltration...) with rule, file:line and the
  source lines, then `Assessment: <level> (<score>/10)`.
- **Tested:** yes. On the Python stealer it scored **High risk 8.6/10** (credential path read,
  Discord webhook, exfiltration). On the hostile npm fixture, whose `postinstall` spawns a coding
  agent with permissions disabled, it reported **"No risks detected (0.0/10)"**: a clean GuardDog
  never clears a package that the skill flagged.
- **Network:** at start it tries to refresh public top-package lists (for typosquatting) from
  GitHub and package-index sites, falling back to the bundled lists when offline. Scanning by
  package *name* downloads it from the registry; metadata rules run WHOIS on maintainer e-mail
  domains; `verify <lockfile>` downloads every listed package (not tested here). No sample
  content is uploaded. It applies its own kernel sandbox (Landlock/Seatbelt) to extraction and
  analysis; `--no-sandbox` disables it.
- **Caveats:** it prints matched source lines **unmasked**: mask any token before quoting.

### OSV-Scanner (Google)
- **Adds:** checks lockfiles and manifests against OSV.dev, which includes the OpenSSF
  known-malicious package feed (`MAL-` advisories, e.g. `MAL-2026-2144` for the compromised
  `litellm` releases) besides ordinary vulnerabilities.
- **License:** Apache-2.0. **Tested:** 2.7.1 (released 2026-11-09).
- **Platforms:** Linux, macOS, Windows single binaries. Homebrew and Scoop `osv-scanner`.
- **Install:** binary from `github.com/google/osv-scanner/releases`, checked against
  `osv-scanner_SHA256SUMS` (Linux amd64 2.7.1:
  `fb7dab19a8bd9bbe5c3189f09d4b7ee1820c9553a23bac202648a56efd2f6ee8`).
- **Command:** `osv-scanner scan source -r <folder>`.
  Offline: `osv-scanner scan source -r --offline-vulnerabilities --download-offline-databases <folder>`.
- **Read:** a table of package, version, ecosystem and advisory id. Any `MAL-` id means the exact
  version is a known-malicious package: treat it as an incident if it was installed.
- **Tested:** `--offline` yes, on the fixtures: it walked them and reported "No package sources
  found" (they have no lockfile). The online query and the offline databases were not exercised.
- **Network:** online mode sends **package names, versions and ecosystems** (no source code) to
  `api.osv.dev`. The offline databases are per-ecosystem downloads (size not measured here).
- **Caveats:** only as good as the lockfile. A malicious package not yet reported is not found.

### Trivy (Aqua Security)
- **Adds:** for a Docker image: known vulnerabilities, secrets and misconfigurations in every
  layer, read from a saved tarball so the container never runs.
- **License:** Apache-2.0. **Tested:** 0.76.2 (released 2026-11-05).
- **Platforms:** Linux, macOS, Windows. Homebrew (built from source) and Scoop `trivy`.
- **Install:** release archive from `github.com/aquasecurity/trivy/releases`, checked against
  `trivy_<ver>_checksums.txt` (Linux 64-bit 0.76.2:
  `bc0fc726e017b8927a62b2d3531d7a84ee01769daf5c99ed866dced54089fdbf`); each asset also has a
  `.sigstore.json` bundle for signature verification.
- **Supply-chain note:** in March 2026 the project's release credentials were abused to publish a
  malicious v0.69.4 and to repoint `trivy-action`/`setup-trivy` tags (advisory
  GHSA-69fq-xp46-6x23). Pin an exact version, verify checksum or signature, never `latest`.
- **Command:**
  ```bash
  docker save <image>@<digest> -o image.tar        # no container is started
  trivy image --input image.tar
  trivy fs --scanners secret,misconfig --skip-db-update --skip-check-update --offline-scan <folder>
  ```
- **Read:** per-target tables with severity; for malware hunting, the secrets and unexpected
  packages matter more than CVE counts.
- **Tested:** the `fs` secret/misconfig command yes, offline: it found nothing on the fixtures
  (it did not flag the fake credentials the skill masks). `trivy image` not tested: no image, and
  the vulnerability database download was skipped.
- **Network:** vulnerability scanning downloads its database from an OCI registry on first run
  (not measured here); nothing from the sample is uploaded.

---

## AI-agent config, MCP servers and skills

Warden's own target-F pass (`scan_tree.py` plus `references/agent-config-triage.md`) is the
primary tool here. The scanners below differ sharply in **what leaves the machine**:

| Tool (version checked) | License | Offline mode | What leaves the machine, by mode | Offered |
|---|---|---|---|---|
| **Cisco skill-scanner** 2.3.2 | Apache-2.0 | **Yes**: default `scan` runs static (YAML + YARA-X), bytecode, pipeline and correlation analyzers locally | Default: nothing (verified with no network). `--use-llm`: `SKILL.md` and scripts to the configured LLM provider (a local model is possible). `--use-aidefense`: text content to Cisco AI Defense. `--use-virustotal`: file hashes; `--vt-upload-files`: the files. `--use-osv`: dependency names to OSV.dev. `scan-repo <url>`: clones from the network | Yes, core mode only |
| **Snyk agent-scan** (formerly mcp-scan) 0.6.11 | Apache-2.0 | **No** offline analysis | `scan`: component data needed for analysis (agent details, MCP server configs, tool names and descriptions, skill content; secrets redacted per the README) to the Snyk API; needs a Snyk account token. Both `scan` and `inspect` also **contact the MCP servers** in the config: remote URLs are fetched, and stdio servers are **started** (after per-server consent, or with `--dangerously-run-mcp-servers`), which executes the repo's commands | No: only by name, in a disposable sandbox, after saying what is sent |
| **Cisco mcp-scanner** 4.8.7 | Apache-2.0 | Only `static` on a pre-generated tools JSON | Default analyzers are API + YARA + LLM: tool descriptions to Cisco AI Defense and to the LLM provider. `config`, `stdio` and `known-configs` **start** the configured servers; `remote` connects to the URL. `--analyzers yara static --tools <tools.json>` stays local | No (static mode only if the user has a tools JSON) |

### Cisco skill-scanner
- **Adds:** a second rule engine (YAML + YARA-X) and Python dataflow analysis for agent skill
  folders (`SKILL.md` plus scripts).
- **Install:** in a virtual environment, `pip install cisco-ai-skill-scanner==2.3.2` (Python
  3.11-3.14; about 520 MB installed: litellm, onnxruntime, magika). Linux, macOS, Windows.
- **Command:**
  ```bash
  skill-scanner scan <skill-folder>                    # core analyzers, offline
  skill-scanner scan-all -r <repo-folder>              # every skill found under the folder
  skill-scanner scan <skill-folder> --format json
  skill-scanner scan <skill-folder> --use-behavioral   # adds dataflow analysis, still local (not tested)
  ```
- **Read:** status, max severity and findings with rule id and file. JSON gives `severity`,
  `rule_id`, `title`, `file_path`.
- **Tested:** core mode yes, offline. On the hostile skill (a skill shell line that posts `~/.aws/credentials` with `curl`)
  it raised **CRITICAL `YARA_command_injection_generic`** plus an INFO for the missing license;
  `scan-all -r` found the same skill inside the repo. About 20 s per run, mostly start-up.
- **Caveats:** the project's own benchmark says rules alone catch only a small fraction of its
  malicious set and recommends the LLM judge; treat the core mode as a low-recall second opinion.
  Writes a cache under the home directory.

### Snyk agent-scan and Cisco mcp-scanner
**Not tested here:** both analyze through a vendor API or LLM, and their live modes start or
contact the MCP servers under scrutiny, which is the execution warden exists to avoid. agent-scan
was installed (`pip install snyk-agent-scan==0.6.11`) only to confirm its commands (`scan`,
`inspect`) and its Snyk endpoints. If the user asks for one by name: run it inside a disposable
container or VM, never with `--dangerously-run-mcp-servers` on an untrusted repo, and state
beforehand which data goes to which service.

---

## Excluded, and why

| Candidate | Reason |
|---|---|
| Semgrep Community Edition | The engine is LGPL-2.1, but the registry rules are under the Semgrep Rules License (not OSI), `--config auto` downloads them and needs metrics on. It is a SAST tool for bugs; GuardDog covers malicious-package patterns |
| Syft / Grype | SBOM and known-vulnerability matching, not malware hunting; OSV-Scanner already covers `MAL-` advisories |
| pdfid / pdf-parser | Useful, but dedicated to the public domain with no license file, which is not an OSI-approved license. Use them only if the user asks by name |
| mcp-shield | No commits since 2025-04; its deeper check sends tool descriptions to an LLM API |
| signature-base, Elastic protections-artifacts, Yara-Rules | As standalone sets: Detection Rule License 1.1 and Elastic License 2.0 are not OSI; Yara-Rules has had no commits since 2024-04. signature-base rules already reach you through YARA Forge |
| VirusTotal and other reputation services | Services, not open-source tools. Hash lookups and uploads follow the "Do not leak the sample" rule in `SKILL.md` |
