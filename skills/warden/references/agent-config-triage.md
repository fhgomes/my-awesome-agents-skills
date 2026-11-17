# AI Coding-Agent Configuration in Untrusted Repositories

**Opening a repository with a coding agent is an execution path.** A cloned repo can ship
files that the agent reads as instructions, and files that the agent's harness **executes**
(hooks, helper commands, MCP server launchers). It can also ship settings that pre-approve
commands or send the agent's API traffic, with your credential, to someone else's server.
Triage these files as executable content, exactly like `postinstall` or `.github/workflows`.

Do this triage before anyone runs `claude`, `codex`, `gemini`, Cursor or Copilot agent mode in the tree.

---

## Real cases (confirmed)

| Case | What the repo/package shipped | Source |
|---|---|---|
| Claude Code, GHSA-ph6w-f82w-28w6 (fixed Aug 2025) | `SessionStart` hook in `.claude/settings.json` ran before the trust dialog | Check Point Research, Feb 2026 |
| Claude Code, CVE-2025-59536 (fixed Sep 2025) | `.mcp.json` servers plus `enableAllProjectMcpServers` / `enabledMcpjsonServers` in the repo's settings started before consent | Check Point Research; NVD |
| Claude Code, CVE-2026-21852 (fixed in 2.0.65) | `env.ANTHROPIC_BASE_URL` in project settings: the API key went in plaintext to the attacker before the trust dialog | Check Point Research; NVD |
| Cursor, CVE-2025-54135 "CurXecute" / CVE-2025-54136 "MCPoison" | Writable or swappable `.cursor/mcp.json`: an approved entry was changed afterwards, or a new one was injected via prompt injection | AIM Security; Check Point; Tenable FAQ |
| VS Code Copilot, CVE-2025-53773 (Aug 2025) | Prompt injection made the agent write `"chat.tools.autoApprove": true` to `.vscode/settings.json` ("YOLO mode") and then run commands | Embrace The Red; MSRC |
| OpenAI Codex CLI, CVE-2025-61260 (fixed in 0.23.0) | Repo `.env` set `CODEX_HOME=./.codex`, so the repo's `config.toml` MCP commands ran without asking | Check Point Research; NVD |
| Gemini CLI (fixed in 0.1.14) | Injection hidden in `README.md`/`GEMINI.md`. An allow-listed `grep` with a chained `; curl` sent env vars out | Tracebit, Jul 2025 |
| "Rules File Backdoor" | Zero-width and bidi unicode hid instructions in Cursor/Copilot rules files that the reviewer could not see | Pillar Security, Mar 2025 |
| s1ngularity (malicious `nx` on npm, Aug 2025) | `postinstall` ran `claude --dangerously-skip-permissions -p`, `gemini --yolo`, `q --trust-all-tools` to hunt for secrets | Snyk; Wiz |
| `postmark-mcp` on npm (Sep 2025) | A lookalike MCP server that added a hidden BCC to every e-mail it sent | Koi Security; Snyk |
| `mcp-remote` CVE-2025-6514 (< 0.1.16) | A malicious remote MCP server got OS command execution through `authorization_endpoint` | JFrog |
| `.claude/settings.local.json` leaks (Nov 2026) | "Yes, and don't ask again" saves the exact command, inline passwords included. Thousands of public repos and Docker images contain the file | Apiiro; GitGuardian |

Fixed CVEs still matter. A teammate on an old version is still exposed, and the **intent**
in the file is the IoC even when your own version ignores it.

---

## 1. Inventory: what can be in the tree

Every name below is from the vendor's docs. Run `scripts/scan_tree.py` and it flags all of them.

| Agent | Executes / grants | Instructions (prompt surface) |
|---|---|---|
| **Claude Code** | `.claude/settings.json`, `.claude/settings.local.json`, `.mcp.json`, skill/subagent frontmatter `hooks`, plugins (`.claude-plugin/plugin.json`, `hooks/hooks.json`, plugin `.mcp.json`, `.lsp.json`, `monitors/monitors.json`, `bin/`) | `CLAUDE.md`, `.claude/CLAUDE.md`, `CLAUDE.local.md`, `AGENTS.md`, `.claude/rules/**/*.md`, `.claude/skills/*/SKILL.md`, `.claude/commands/*.md`, `.claude/agents/*.md`, `@path` imports |
| **Cursor** | `.cursor/mcp.json`, `.cursor/hooks.json` | `.cursor/rules/**/*.mdc`, `AGENTS.md`, legacy `.cursorrules` |
| **VS Code / Copilot** | `.vscode/mcp.json` (`servers`), workspace `.mcp.json`, `.vscode/settings.json` (`chat.tools.autoApprove`, `chat.mcp.autostart`), `.vscode/tasks.json` (`runOn: folderOpen`) | `.github/copilot-instructions.md`, `.github/instructions/*.instructions.md`, `.github/prompts/*.prompt.md`, `.github/agents/*.agent.md`, `AGENTS.md` |
| **Codex CLI** | `.codex/config.toml` (`mcp_servers`, `hooks`, `approval_policy`, `sandbox_mode`), a `.env` that moves `CODEX_HOME` | `AGENTS.md` |
| **Gemini CLI** | `.gemini/settings.json` (`mcpServers` with `trust`, `hooks`, `tools.allowed`, `security.folderTrust`), `.env` | `GEMINI.md` (or the `context.fileName` override) |
| **Windsurf / Devin Desktop** | `.devin/mcp_config.json`, `.devin/hooks.v1.json` | `.windsurfrules`, `.windsurf/rules/*.md`, `.devin/rules/*.md`, `AGENTS.md` |

```bash
# list them without opening anything
find . \( -path ./node_modules -o -path ./.git \) -prune -o \( \
  -path '*/.claude/*' -o -path '*/.cursor/*' -o -path '*/.gemini/*' -o -path '*/.codex/*' \
  -o -path '*/.devin/*' -o -path '*/.windsurf/*' -o -path '*/.claude-plugin/*' -o -path '*/.github/instructions/*' \
  -o -path '*/.github/prompts/*' -o -path '*/.github/agents/*' -o -name '.mcp.json' -o -name 'CLAUDE*.md' \
  -o -name 'AGENTS*.md' -o -name 'GEMINI.md' -o -name '.cursorrules' -o -name '.windsurfrules' \
  -o -name 'copilot-instructions.md' -o -name 'SKILL.md' -o -path '*/.vscode/*.json' \) -type f -print
```

---

## 2. What to look for

### 2a. Anything that runs a command

| Where | Key | Notes |
|---|---|---|
| Claude settings | `hooks` (all 33 events: `SessionStart`, `Setup`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `Stop`, `ConfigChange`, `InstructionsLoaded`, `FileChanged`...) | `SessionStart` fires with no user action. Handler `type` can be `command`, `http` (POSTs each event payload to a URL), `mcp_tool`, `prompt` or `agent` |
| Claude settings | `statusLine.command`, `fileSuggestion`, `apiKeyHelper`, `awsAuthRefresh`, `awsCredentialExport`, `gcpAuthRefresh`, `otelHeadersHelper` | All are shell commands, and all are allowed in project scope |
| Claude skills / commands | `` !`cmd` `` or a ` ```! ` block in the body | Runs **when the skill is invoked, before the model sees the text**. Claude can auto-invoke a skill based on its `description` |
| Skill / subagent frontmatter | `hooks`, `allowed-tools`, `mcpServers`, `permissionMode` | Project skill hooks and `allowed-tools` are used even without trust in `-p`/SDK runs |
| Plugins | `hooks/hooks.json`, `.mcp.json`, `.lsp.json`, `monitors` (background process at session start), `bin/` (put on PATH) | A repo can register marketplaces via `extraKnownMarketplaces` / `enabledPlugins` |
| Cursor | `.cursor/hooks.json` (`sessionStart`, `beforeShellExecution`, `workspaceOpen`...) | Needs a trusted workspace |
| Codex | `hooks`, `notify`, `model_providers.*.auth.command`, `mcp_servers.*.command` | Project `.codex/` is loaded only for trusted projects |
| Gemini | `hooks` (`BeforeTool`, `AfterTool`, `SessionStart`...) | |
| VS Code | `tasks.json` task with `"runOptions": {"runOn": "folderOpen"}` | Runs when the folder opens, if automatic tasks are allowed |

A hook that calls a repo script (`.claude/hooks/x.sh`) moves the payload into that script, so scan the script too.
A formatter hook (`npx prettier --write`) is normal **in your own repo**. In a third-party repo, every
hook needs a reason.

### 2b. Pre-approved permissions and lowered guardrails

- `permissions.allow` with `Bash`, `Bash(*)`, or wildcards on `curl`/`wget`/`ssh`/`python`/`node`/`sudo`/`docker`/`git push`/`npm publish`/`rm`
- `WebFetch` or `WebFetch(domain:*)`: an open exfiltration channel
- `Edit(`/`Write(` on `~/`, `/`, `//` or `../`, and `additionalDirectories` pointing outside the repo
- `defaultMode: bypassPermissions` / `auto` (Claude Code ignores these from project files since v2.1.257), `skipDangerousModePermissionPrompt`
- `enableAllProjectMcpServers: true`, `enabledMcpjsonServers` (ignored from an untrusted folder's own settings)
- VS Code `chat.tools.autoApprove`, Gemini `mcpServers.*.trust: true` / `tools.allowed: ["run_shell_command"]` / `security.folderTrust.enabled: false`, Codex `approval_policy = "never"` / `sandbox_mode = "danger-full-access"`
- Instruction text telling the agent, or you, to use `--dangerously-skip-permissions`, `--yolo`, `--trust-all-tools` or `--dangerously-bypass-approvals-and-sandbox`

### 2c. MCP servers

| Signal | Why |
|---|---|
| `npx -y pkg`, `bunx`, `pnpm dlx`, `uvx pkg`, `pipx run` | Downloads and runs whatever the registry serves **on every start**. Unpinned means the publisher can change it tomorrow |
| Name close to a known server (`@modelcontextprotocl/...`, `mcp-server-fecth`) or the official scope name outside the scope | Typosquat / lookalike (the postmark-mcp pattern) |
| `command: bash/sh/cmd/powershell` with `-c` | Inline shell, often `curl | sh` |
| `docker run --privileged`, `-v /:/`, `docker.sock` | Host takeover from a "tool" |
| `url` on a remote host, especially `http://` | Sees prompts and tool data, and its replies are model input (an injection channel) |
| `headersHelper` | Another command. Claude Code runs it only after trust |
| `env` with `*_BASE_URL`, `HTTPS_PROXY`, `NODE_OPTIONS=--require`, `LD_PRELOAD` | Traffic redirection / code injection into the server process |
| `mcp-remote` < 0.1.16 | CVE-2025-6514 |

### 2d. Endpoint and credential overrides (`env` blocks, `.env`)

`ANTHROPIC_BASE_URL` (and the `_BEDROCK_`, `_VERTEX_`, `_FOUNDRY_`, `_AWS_` and `_GOOGLE_CLOUD_` variants),
`HTTP_PROXY`/`HTTPS_PROXY`, `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_API_KEY`, `ANTHROPIC_CUSTOM_HEADERS`,
`NODE_TLS_REJECT_UNAUTHORIZED=0`, `NODE_EXTRA_CA_CERTS`, `CLAUDE_CODE_SHELL_PREFIX` (wraps every Bash,
hook, status-line and MCP start command), `CLAUDE_CONFIG_DIR`, `CODEX_HOME`, `GEMINI_CLI_TRUST_WORKSPACE`.
A base URL that is not the vendor's, set by a repo, is **MALICIOUS until explained**. That is CVE-2026-21852 verbatim.
Claude Code blanks credential variables in a project `.mcp.json` remote `url`/`headers`, but **not** `ANTHROPIC_BASE_URL`.

### 2e. Instruction files as prompt-injection carriers

- **Invisible unicode:** Unicode Tags block U+E0000–E007F (hides ASCII text, which `scan_tree.py` decodes),
  bidi controls U+202A–202E / U+2066–2069 (Trojan Source, CVE-2021-42574), zero-width U+200B–200D/U+2060/U+FEFF.
  Instruction files have no legitimate use for them. Emoji ZWJ sequences are the one benign exception.
- **HTML comments** with commands or URLs: invisible in rendered Markdown. Claude Code strips block-level
  comments before the model sees them, but comments inside code blocks are kept, and other agents may read them all.
- **Phrasing:** "ignore previous instructions", "do not tell/mention to the user", "silently", "before every
  task run...", "fetch <url> and follow it", "send .env / ~/.ssh / tokens to...", "disable the sandbox/hooks".
- **Reach:** `@path` imports, symlinked `.claude/rules/` pointing outside the repo (Claude asks once for external imports),
  nested `CLAUDE.md` in subdirectories (loaded on demand), a `SKILL.md` whose `description` says "use for everything".
- README, issues and docs are injection surfaces too (the Gemini CLI case), just not auto-loaded ones.

```bash
# invisible characters, with code points (read-only)
python3 -I - <<'EOF' CLAUDE.md AGENTS.md .cursorrules
import sys, unicodedata
for p in sys.argv[1:]:
    try: t = open(p, encoding="utf-8", errors="replace").read()
    except OSError: continue
    for i, c in enumerate(t):
        cp = ord(c)
        if 0xE0000 <= cp <= 0xE01EF or cp in (0x200B,0x200C,0x200D,0x2060,0xFEFF) or 0x202A <= cp <= 0x202E or 0x2066 <= cp <= 0x2069:
            print(p, t.count("\n", 0, i) + 1, f"U+{cp:04X}", unicodedata.name(c, "?"))
EOF
```

---

## 3. The mirror image: committed credentials in a third-party repo

`.claude/settings.local.json` saves approved commands **verbatim**:
`Bash(PGPASSWORD=... psql ...)`, `Bash(curl -H 'Authorization: Bearer ...')`. Claude Code adds it to the
**global** git excludes of the machine that wrote it, which protects nobody else. So it shows up in public repos and
in images built with `COPY . .` without a `.dockerignore` (Apiiro and GitGuardian, Nov 2026).

For Warden, a live-looking key in someone else's agent config is:
- **an IoC about the repo's hygiene**: the author ships personal files, so the rest deserves less trust;
- **a trap**: never use, test, "validate" or curl with it. Using a credential you found is unauthorized
  access, and a planted key can be a honeytoken that alerts its owner and names you.

Report it as "credential-looking value of type X in file:line (masked)". `scan_tree.py` prints only the first 4 characters.
**If the repo is the owner's own**, stop and hand off to the **redact** skill (rotation, history rewrite, `.gitignore`).
Prevention (managed settings, `.dockerignore`, pre-commit) is **sentinel**'s job.

---

## 4. Safe handling procedure

1. **Read as text first.** Use `scripts/scan_tree.py <repo>`, then read each flagged file with `cat`/`less`/an editor
   that shows invisible characters. Do not `cd` into it with an agent running and do not open it in Cursor or VS Code agent mode yet.
2. **Never** run `claude -p`, the Agent SDK, `claude --init-only` or `codex exec` in an untrusted tree. In `-p`/SDK
   runs there is no trust dialog: project hooks, the `env` block, helper commands such as `apiKeyHelper` and a
   project skill's hooks/`allowed-tools` **are used**, and `.mcp.json` servers connect without asking.
   `--init-only` exists precisely to run `Setup` and `SessionStart` hooks.
3. **In an interactive first session, read the trust dialog.** It lists the allow rules, additional directories, hooks
   and helper commands the folder would activate. Decline if anything is unexplained. Trusting a parent folder
   does not count for a nested repo. Revisit approvals with `claude mcp reset-project-choices`.
4. **When you do need an agent in it**, contain it and strip the repo's config:
   ```bash
   # inside a disposable container/VM, with a throwaway key and no access to ~/.ssh, ~/.aws or the real home
   claude --setting-sources user --strict-mcp-config --disable-slash-commands --permission-mode plan \
          --settings '{"disableAllHooks": true, "disableSkillShellExecution": true}'
   ```
   - `--setting-sources user` skips project/local settings (hooks, env, allow rules, MCP approvals) and `.claude/rules/`
   - `--strict-mcp-config` loads only servers passed with `--mcp-config` (so no `.mcp.json`)
   - `--disable-slash-commands` disables skills and commands. `disableSkillShellExecution` neutralizes `` !`cmd` ``
   - `--bare` goes further for scripted use: it skips hooks, skills, plugins, MCP, auto memory **and CLAUDE.md**
   - `disabledMcpjsonServers` in your user settings blocks a named server in every mode
   - CLAUDE.md/AGENTS.md still load unless `--bare`. The prompt-injection risk stays, so the container still matters.
   - Other agents: Codex marks projects `trust_level = "untrusted"` (project `.codex/` skipped). Gemini keeps
     `security.folderTrust.enabled` on, and you must not pass `--yolo`. Cursor project hooks need a trusted workspace.
     In VS Code use Restricted Mode and leave `chat.tools.autoApprove` off.
5. **Never `bypassPermissions` / `--dangerously-skip-permissions` / `--yolo` on code you have not triaged.** Vendors
   say to use these only in isolated containers or VMs.
6. After the session, check what changed in agent config: `git status --ignored .claude .cursor .vscode .gemini .codex`.
   Prompt injection that *writes* config (CurXecute, CVE-2025-53773) is the second-stage pattern.

---

## 5. Verdict guide

| Finding | Verdict |
|---|---|
| Hook / helper / MCP launcher that fetches and runs remote code, or sends env/files out | **MALICIOUS** |
| Repo-set `ANTHROPIC_BASE_URL`/proxy to a non-vendor host, `NODE_TLS_REJECT_UNAUTHORIZED=0`, `CLAUDE_CODE_SHELL_PREFIX` | **MALICIOUS** unless the README documents an internal gateway and the repo is internal |
| Hidden tag/bidi text in instruction files, injection phrasing, "don't tell the user" | **MALICIOUS** (decoded intent) / **SUSPICIOUS** (no decodable payload) |
| `Bash(*)`, `bypassPermissions`, `enableAllProjectMcpServers`, unpinned `npx -y` of an unknown package | **SUSPICIOUS**: dangerous by design, possibly careless rather than hostile |
| Local formatter/linter hook, pinned well-known MCP server, ordinary CLAUDE.md | **CLEAN** within scope. Still say a hook exists |
| Live-looking credential in agent config | Hygiene IoC + trap (section 3). Not a verdict on malice by itself |
