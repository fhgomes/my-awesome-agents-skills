# Companion tools (optional)

The skill works on its own: the agentic review plus `scripts/scan_secrets.py` and
`scripts/scan_agent_configs.py`. The tools below are a **second opinion** the person may
choose. All are free, open source (OSI license), run locally, and were checked on
**2026-11-18**: license and latest release read from the GitHub API
(`gh api repos/<owner>/<repo>/license`, `.../releases/latest`), the release archive
verified against its published checksum, and every command marked *tested* below run on
throwaway fixtures with fake secrets. Re-check versions before pinning; this page ages.

Every report a tool writes goes through `scripts/summarize_external.py`, never into the
conversation (see [Reading the results](#reading-the-results)).

## Which one for which question

| Question | Use | Why |
|---|---|---|
| "Second opinion on the repo, whole history" | **Betterleaks** (or gitleaks, if already installed) | ~470 provider formats, all refs, offline by default |
| "Is there a secret inside this Docker image?" | **Trivy** `image` | Scans every layer and the image config (`ENV`), from a `docker save` tarball |
| "Is this leaked key still live?" | **TruffleHog** with verification, **only on explicit request** | Verification sends the credential to the provider |
| Pre-commit baseline for a team | detect-secrets (not an audit companion) | Baseline workflow; no history scan |
| Remove the secret from history | git-filter-repo | Remediation, see `history-rewrite.md` |

**Default recommendation:** Betterleaks first; Trivy when an image is shipped; TruffleHog
only when the person asks whether a credential is live, and with verification off unless
they explicitly want it on. If gitleaks is already installed, use it rather than
installing Betterleaks; the results are equivalent for this purpose.

### What the companions add, and what they do not

Measured on a set of private repositories (whole history, gitleaks 8.30.1 with
`--redact=100`, compared with `scan_secrets.py`): 255 gitleaks findings, 136 of them (53%)
from the single rule `generic-api-key`. gitleaks caught provider formats the skill has no
rule for (LinkedIn client secret, `curl -u` credentials, JWT); the skill caught what
gitleaks does not look for: hardcoded passwords, connection strings, dangerous file
names, CPF and card numbers, internal IPs, agent config. **They are complementary, and
the generic rule is noisy.** None of the companions checks Brazilian IDs (CPF/CNPJ by
check digit), Luhn-valid card numbers or agent config tracking state; the skill's own pass
is never skipped.

---

## Betterleaks — first companion

- **Adds:** ~470 provider-specific rules (466 in the default config of 1.10.1) (the gitleaks lineage, actively developed), all
  refs of the history, archives and decoded content.
- **License / status:** MIT. Maintained by the gitleaks author and others. Version tested
  **1.10.1** (released 2026-11-12). The gitleaks README says gitleaks is feature-complete
  and receives security patches only; new work goes to Betterleaks.
- **Install** (pick one, pin the version):
  - Release binary: `betterleaks_<ver>_<os>_<arch>.tar.gz` plus `checksums.txt` from
    `github.com/betterleaks/betterleaks/releases`; verify with
    `grep linux_x64.tar.gz checksums.txt | sha256sum -c -` (a Sigstore bundle is also published).
  - Homebrew: `brew install --cask betterleaks/tap/betterleaks@1` (command `betterleaks-v1`).
  - Fedora: `dnf install betterleaks`. Go: `go install github.com/betterleaks/betterleaks@v1.10.1`.
  - Container: use an exact version tag, not the floating `:v1`.
- **Commands** (tested):
  ```bash
  # whole history, all refs (a commit only on a side branch was found)
  betterleaks git /path/to/repo --redact=100 --no-banner -l error -f json -r /tmp/bl-history.json
  # working tree, including untracked files
  betterleaks dir /path/to/repo --redact=100 --no-banner -l error -f json -r /tmp/bl-tree.json
  python3 scripts/summarize_external.py /tmp/bl-history.json --repo /path/to/repo
  ```
  Exit code 1 means findings.
- **Network:** none by default (no outbound connection observed with `strace`).
  `--validation` sends candidates to provider APIs: do not pass it. The `github`, `gitlab`,
  `huggingface` and `s3` subcommands fetch remote content; not needed here.
- **Caveats:**
  - `--redact=100` blanks `Secret` and the secret inside `Match`, but when one match spans
    two secrets the *other* one stays in `Match` in clear (observed with `curl-auth-header`
    on a line that also had `curl -u`). Treat the report as sensitive anyway.
  - A target's `.betterleaks.toml`/`.gitleaks.toml` is **not** loaded unless
    `--unsafe-auto-load-config`; local git config and hooks are not trusted unless
    `--trust-local-git-config`. Keep both off.
  - `generic-api-key` is the noisy rule; the summary lists it apart.

## gitleaks — if it is already installed

- **Adds:** the same as Betterleaks (same rule lineage). Use it instead of Betterleaks,
  not in addition.
- **License / status:** MIT. Version tested **8.30.1** (latest release, 2026-03-21);
  feature-complete, security fixes only.
- **Is it open source, and does it work with any git host?** Yes, MIT. `gitleaks git`
  reads the **local** repository with `git log -p`, so the host (GitHub, GitLab,
  Bitbucket, Gitea, a bare server, no remote at all) does not matter: the fixtures had no
  remote. It also scans plain directories (`gitleaks dir`) and standard input
  (`gitleaks stdin`); both tested. `--platform` only shapes the links it prints.
- **Install:** `brew install gitleaks`; or the release `gitleaks_<ver>_<os>_<arch>.tar.gz`
  with `gitleaks_<ver>_checksums.txt` (`sha256sum -c`); container with an exact tag.
- **Commands** (tested):
  ```bash
  printf '[extend]\nuseDefault = true\n' > /tmp/gitleaks-default.toml
  gitleaks git /path/to/repo -c /tmp/gitleaks-default.toml --redact=100 --no-banner -l error -f json -r /tmp/gl-history.json
  gitleaks dir /path/to/repo -c /tmp/gitleaks-default.toml --redact=100 --no-banner -l error -f json -r /tmp/gl-tree.json
  python3 scripts/summarize_external.py /tmp/gl-history.json --repo /path/to/repo
  ```
- **Network:** none (no outbound connection observed).
- **Caveats:**
  - gitleaks **auto-loads `.gitleaks.toml` from the scanned directory**. A planted file
    with `[allowlist] paths = [".*"]` silenced every finding (exit 0, 0 findings) in the
    test; Betterleaks ignored the same file. Always pass `-c` with a default-only config
    as above.
  - It runs `git` inside the repository with that repository's local config. Fine for
    the person's own repo; for an untrusted one prefer Betterleaks.
  - Same `Match` caveat as Betterleaks.

## Trivy — when a Docker image is involved

- **Adds:** secrets inside image layers and the image config (`ENV`, labels, build
  history), which is how a `.claude/settings.local.json` or `.env` copied by `COPY .`
  reaches a registry. Also scans a directory.
- **License / status:** Apache-2.0. Version tested **0.76.2** (released 2026-11-05).
- **Install:** release `trivy_<ver>_Linux-64bit.tar.gz` with `trivy_<ver>_checksums.txt`
  (`sha256sum -c`; Sigstore bundles also published); `brew install trivy`; the vendor's
  apt/rpm repository; container `aquasec/trivy:<exact version>`. The archive is ~53 MB.
- **Commands** (tested on a hand-built `docker save`-format tarball and a fixture directory):
  ```bash
  T="--scanners secret --skip-version-check --disable-telemetry --cache-dir /tmp/trivy-cache --format json -q"
  docker save my-image:1.2.3 -o /tmp/my-image.tar        # reads the image, changes nothing
  trivy image $T --image-config-scanners secret --input /tmp/my-image.tar -o /tmp/trivy-image.json
  trivy fs $T -o /tmp/trivy-fs.json /path/to/repo         # working tree only, no history
  python3 scripts/summarize_external.py /tmp/trivy-image.json
  ```
  `trivy image my-image:1.2.3` (reading straight from the local daemon) is *not tested here*;
  the tarball route avoids needing daemon access from the scanner.
- **Network:** with exactly these flags, none observed. Without them:
  - `--scanners` defaults to `vuln,secret`, and `vuln` **downloads the vulnerability
    database** on first use. `--scanners secret` avoids it (the cache stayed under 40 KB).
  - Trivy **sends anonymous usage data to its vendor by default**; `--disable-telemetry`
    turns it off. `--skip-version-check` stops the update notice lookup.
  - Without `--input`, an image not present locally is pulled from a registry.
- **Caveats:** Trivy masks the matched secret with `*`, but the `Code` block keeps the
  surrounding source lines in clear, including other secrets on neighbouring lines
  (observed). `trivy fs` does not read git history. Its rules are fewer than
  Betterleaks' and it knows nothing about inline passwords in agent config (only a
  `ghp_` token was found in a `settings.local.json` that held 15 inline credentials).

## TruffleHog — only on explicit request

- **Adds:** ~800 detectors (its README says "800 secret types") and, its real differentiator, **live verification**: it calls
  the provider to ask whether the credential works. That answers "do I have to rotate
  right now?", at the cost of sending the credential out.
- **License / status:** **AGPL-3.0**. Version tested **3.99.9** (released 2026-11-12).
- **Install:** `brew install trufflehog`; or the release `trufflehog_<ver>_<os>_<arch>.tar.gz`
  with `trufflehog_<ver>_checksums.txt` (`sha256sum -c`; the checksum file is cosign-signed).
  The project also offers an install script piped to `sh`: do not use it.
- **Commands** (tested, verification off):
  ```bash
  trufflehog git file:///path/to/repo --no-verification --no-update --json > /tmp/th.json 2>/dev/null
  python3 scripts/summarize_external.py /tmp/th.json --repo /path/to/repo
  ```
  `trufflehog filesystem /path/to/repo` also decompresses loose objects under `.git/`, so
  it reports history findings as `.git/objects/<object>` paths. Exit code is 0 even with
  findings unless `--fail` (exit 183).
- **Network:**
  - **Verification is ON by default.** Every candidate is sent to the provider's API.
    `--no-verification` turns it off. With verification, `--results=verified` shows only
    live ones.
  - Without `--no-update` it makes an outbound HTTPS request at startup (observed with
    `strace`). With `--no-update --no-verification` no outbound connection was observed.
  - Verification against providers was **not tested here** on purpose.
- **Caveats:** **there is no option to hide the values.** The JSON always carries `Raw`
  and `RawV2` (and often `Redacted`, which for some detectors is the key ID itself); the
  default text output prints them too (tested). Never let its output reach the conversation; write
  to a file and summarize.

## Kingfisher — supported, not recommended by default

- **Adds over Betterleaks:** little for this skill. In 2.19.1, 470 of its 475 rule IDs
  are `betterleaks.*`; its differentiators are validation and `blast-radius` (mapping a
  live credential's permissions), both network features.
- **License / status:** Apache-2.0 (MongoDB). Version tested **2.19.1** (2026-11-17).
- **Install:** `brew install kingfisher`; or the release `kingfisher-<os>-<arch>.tgz`. The
  release has **no checksums file**: verify against the SHA-256 digest GitHub shows for the
  asset (`gh api repos/mongodb/kingfisher/releases/latest --jq '.assets[]|.name+" "+.digest'`),
  which matched the in-toto attestation (`multiple.intoto.jsonl`) in the test.
- **Command** (tested):
  ```bash
  kingfisher scan /path/to/repo --no-validate --no-update-check --redact --format json --output /tmp/kf.json -q
  python3 scripts/summarize_external.py /tmp/kf.json --repo /path/to/repo
  ```
  Full history is the default (`--git-history full`). Exit code 200 means findings.
- **Network:** **validation is ON by default** (`--no-validate` / `-n` turns it off) and
  it checks for updates by default (`--no-update-check`). With both flags no outbound
  connection was observed.
- **Caveats:** `--redact` replaces values with a hash (report verified clean); without it
  the JSON carries raw values.

## detect-secrets — not an audit companion

- **Why not:** scans only the current files (no git history), and its baseline file is
  meant to be committed. Good for a team pre-commit hook, weak for a pre-publication audit.
- **License / status:** Apache-2.0 (Yelp). Version tested **1.5.0**, the latest release
  (2024-05-06); the repository still receives commits.
- **Install:** in a venv, pinned: `pip install detect-secrets==1.5.0` (wheel SHA-256 on PyPI).
- **Command** (tested): `detect-secrets scan --all-files -n > /tmp/ds.json`.
- **Network:** **verification is ON by default** for several plugins (AWS, Slack, Stripe,
  Mailchimp, Telegram, IBM, ...). A run without `-n` on the fixtures opened 24 HTTPS
  connections. `-n` / `--no-verify` turns it off (none observed).
- **Caveats:** the baseline stores an unsalted SHA-1 (`hashed_secret`) per finding; a short
  password can be recovered from it by brute force.

## git-filter-repo — remediation

- **Role:** rewrites history to remove a file or a string; the procedure is in
  `references/history-rewrite.md`. Destructive: only with explicit confirmation.
- **License / status:** MIT (with an option for git's GPL terms; the GitHub API reports
  `NOASSERTION` because of the dual wording). Latest release **v2.47.0** (2024-12-04);
  repository active.
- **Install:** `pip install git-filter-repo==2.47.0`, `brew install git-filter-repo`, or the
  distribution package. **Not tested here** (it rewrites history; covered by the existing
  reference).

---

## Not offered by default

- **ggshield** (GitGuardian, MIT client): the scan runs on GitGuardian's API, so it needs
  an account and an API key and **sends the scanned content to the vendor**. Acceptable
  only if the person already uses GitGuardian and chooses it.
- **Microsoft Presidio** (MIT, PII detection): heavy (it depends on large NLP models) and
  aimed at free text; for code, the skill's own check-digit CPF/CNPJ and Luhn card rules
  are more precise. No light, local, maintained PII scanner for repositories was found
  that adds to the built-in rules.

## Not recommended

- **Nosey Parker** (Praetorian, Apache-2.0): repository **archived**; last release v0.24.0
  (2025-05-08). Its successor in spirit is Kingfisher.

---

## Reading the results

1. Write the report to a file outside the repository (`/tmp/...`), never to stdout in the
   conversation.
2. Summarize it:
   ```bash
   python3 scripts/summarize_external.py /tmp/report.json --repo /path/to/repo
   python3 scripts/summarize_external.py /tmp/a.json /tmp/b.json --repo /path/to/repo --json
   ```
   Output: per tool and rule, `file:line`, commit, date, verification status, and
   `file in HEAD` / `history only` (not in HEAD's tree: deleted, renamed, or only on
   another branch) / `not tracked` / `image layer <id>` / `image config`. Generic
   keyword/entropy rules are grouped as LOW-SIGNAL. No value, match text, code context,
   author or commit message is printed.
3. Label each finding in the verdict with the tool that produced it, and merge
   duplicates with the skill's own findings (same file, line, kind).
4. Confirm a LOW-SIGNAL finding by opening the line yourself before counting it.
5. Delete the raw reports when done; they may contain values.

`summarize_external.py` was tested on JSON reports from Betterleaks 1.10.1, gitleaks
8.30.1, TruffleHog 3.99.9, Kingfisher 2.19.1 (json and jsonl, with and without
`--redact`), Trivy 0.76.2 (fs and image) and detect-secrets 1.5.0, generated from fixtures.
Several of those reports contained raw fixture values; none of the summaries (text or
`--json`) contained any value or any 5-character piece of one.
