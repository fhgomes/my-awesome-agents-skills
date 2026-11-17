# Hardening Environments That Run Coding Agents

How to set up a developer workstation, a server and CI so that a coding agent (Claude Code,
Cursor, Codex, Gemini CLI) **does not persist secrets in its config files**, and so that
those files **never leave the machine**. Plus the audit checklist for such an environment.

How the work splits between the security skills:
- **Sentinel (this file)**: prevention and hardening. How to configure things so it does not happen.
- **Redact**: detection. Finding the leaked secret in the tree and in git history, and
  remediating it (Redact's agent-config audit). Do not rebuild a scanner here.
- **Warden**: the hostile angle. Agent config in an untrusted repo as an attack vector
  (malicious hooks, MCP servers, pre-approved commands).

---

## 0. The mechanism (confirmed in the docs and in the research)

1. At a Bash permission prompt, "Yes, and don't ask again" saves the approval as an `allow`
   rule in `.claude/settings.local.json`, **at the root of the git repository** (in a
   worktree, at the root of the main checkout). This applies to Bash and WebFetch; file-edit
   approvals last only for the session. (docs: Settings, Permissions)
2. The saved rule is the text of the command. If the command contained `PGPASSWORD=...`, an
   `Authorization: Bearer ...` header, `user:password@` in a URL or `--password x`, the secret
   is now in the file in plain text. (GitGuardian, Apiiro)
3. Why it becomes an exact match and not a prefix: the docs say an `allow` rule **does not
   match after a variable assignment** unless the variable is on the built-in list of safe
   variables, and the prompt only offers "don't ask again" for what it can display. So
   `PGPASSWORD=x psql ...` does not become `Bash(psql *)`; it becomes the whole line.
   (Inferred from the Permissions docs, "Wrappers" section; it matches what both studies found.)
4. Git protection: the first time it writes the file in a repo that does not ignore it,
   Claude Code adds `**/.claude/settings.local.json` to the **global git excludes**
   (`core.excludesFile`, else `$XDG_CONFIG_HOME/git/ignore`, else `~/.config/git/ignore`).
   It does **not** write to the project `.gitignore`. A file created by hand gets not even
   that. (docs: Settings)
   Consequence: another clone, another machine, CI, `COPY . .`, `npm pack`, a zip of the
   directory: none of them honor your machine's global excludes.
5. A local settings file that is **tracked by git** is treated as repository config, and its
   `allow` rules wait for workspace trust (docs: Permissions, "When your local settings file
   needs trust"). That part is Warden's subject; what matters here is that "tracked" is an
   abnormal state and must fail CI.

Figures (confirmed ones only; details under Sources):

| Source | Finding |
|---|---|
| GitGuardian (9 Nov 2026, public GitHub, Jan 2025 to 7 Nov 2026) | `settings.local.json`: 31,088 distinct secrets in 23,276 repositories, 5,343 valid when detected. Shared `settings.json`: 8,271 secrets, 1,283 valid |
| GitGuardian, Docker Hub | 613 distinct secrets in Claude Code settings files inside public images, 99 valid; 543 image repositories, 7,625 tags. 72% under `/app`, `/workspace` or `/usr/src` (the `COPY . .` signature) |
| GitGuardian | Generic detectors (password, high entropy, JWT, bearer) account for 63% of occurrences: a password after `PGPASSWORD=` has no provider format to match |
| Apiiro (via the CSA research note that cites the post) | 104,185 public copies of the file; 1,122 with at least one secret; 1,379 distinct secrets; all still on the default branch; in half the repos the file had been there for at least 217 days; gitleaks caught 564 of the 1,122 files, TruffleHog 643, and **215 got past both** |

---

## 1. Operating rules: a secret never goes into a command line the agent sees

Whatever the agent sees can end up in a saved rule (`settings.local.json`), in an on-disk
transcript (`~/.claude/projects/<project>/<session>.jsonl`) or in the prompt history
(`~/.claude/history.jsonl`, never cleaned up automatically). Hence the rule:
**the agent handles names, never values.**

| Instead of | Use |
|---|---|
| `PGPASSWORD=xyz psql -h db -U app` | `~/.pgpass` (`host:port:db:user:password`, `chmod 600`; libpq ignores the file if its permissions are looser) or `PGPASSFILE` / `PGSERVICE` with `~/.pg_service.conf` |
| `mysql -uroot -pSecret` | `~/.my.cnf` with `[client]` + `password=` (`chmod 600`), or `mysql_config_editor set --login-path=prod` and `mysql --login-path=prod` |
| `curl -H "Authorization: Bearer abc"` | `curl -H @/path/to/headers.txt` (header read from a file), `curl --netrc` with `~/.netrc` (`chmod 600`), or `-H "Authorization: Bearer $TOKEN"` with the variable already in the environment |
| `git clone https://user:token@host/...` | `gh auth login` + `gh auth setup-git`, or `git config credential.helper` (`cache`, `libsecret`, `osxkeychain`, `manager`) |
| `docker login -u x -p secret` | `docker login --password-stdin` fed from a file or secret manager, and `credsStore` in `~/.docker/config.json` (`pass`, `secretservice`, `osxkeychain`) |
| `AWS_SECRET_ACCESS_KEY=... aws s3 ls` | `aws configure sso` / `--profile`, `credential_process` in `~/.aws/config` |
| An API password on the command line | **A wrapper that takes the name, not the value**: `dbq prod "select 1"` reads the credential inside the script (a `600` file, `pass`, Vault, `op read`). The saved rule becomes `Bash(dbq *)`, with no secret in it |

Rules of conduct:
- **Never choose "don't ask again" on a command that carries a literal credential.** Approve
  it once ("Yes") and, if it recurs, write a pattern rule by hand in `/permissions`.
- Prefer a **pattern rule without the secret** (`Bash(psql -h db *)`, `Bash(dbq *)`) to an
  exact-match rule. Every rule without a `*` is suspect: that is where secrets live.
- Load environment variables **outside the agent's view**: exported in the shell (or in the
  systemd unit, `direnv`, a secret manager) before starting the agent. Do not put secrets in
  the `env` block of Claude Code settings: that is just another plain-text file.
- Do not paste secrets into the prompt. They go to the transcript and to `history.jsonl`.
- Do not ask the agent to "show the value" of a variable or of a `.env`. List names only. A
  small wrapper that prints the variable names of a container or file, and prints a value
  only for an exact name requested, masking anything that looks like a secret, covers the
  legitimate need.

---

## 2. Repository and build hygiene

### Project `.gitignore` (do not rely on the global excludes)

```gitignore
# Coding-agent local files: may contain approved commands with secrets in them
.claude/settings.local.json
CLAUDE.local.md
.claude/*.local.*
```

The docs themselves tell you to ignore `CLAUDE.local.md` by hand. `.cursor/cli.json`,
`.gemini/settings.json` and `.claude/settings.json` are usually shared config and **may** be
committed, but they go through a scan before every commit (section 3).

Check **where** the ignore comes from (if the source is the global excludes, other machines
do not have it):

```bash
git check-ignore -v .claude/settings.local.json
# .gitignore:1:...                       -> protected in the repo
# /home/<you>/.config/git/ignore:1:...   -> this machine only
# (no output, exit 1)                    -> NOT ignored

# simulate "another machine" (no global config):
GIT_CONFIG_GLOBAL=/dev/null git check-ignore -v .claude/settings.local.json
```

### `.dockerignore` (`COPY` reads the working tree, not the git index)

```dockerignore
**/.claude/
**/CLAUDE.local.md
**/.cursor/
**/.gemini/
**/.codex/
**/.specstory/
**/.mcp.json
.git/
**/.env
**/.env.*
```

Without a `.dockerignore`, `COPY . .` puts `.claude/`, `.git/` and `.env` into the image even
if git ignores all of them. And **`RUN rm -rf .claude` in a later layer does not fix it**: the
file is still in the `COPY` layer (tested: the final image does not show the file, a `tar` of
the layer does). The same applies to `.npmignore` / the `files` field of `package.json`:
check with `npm pack --dry-run` before publishing.

### Images already published

`docker history` shows **that** there was a `COPY . .`, not **which** files it copied. To
list agent files across all layers (including ones deleted later):

```bash
IMG=registry.example.com/app:1.4.2   # a fixed tag, never latest
D=$(mktemp -d)
docker save "$IMG" -o "$D/img.tar" && tar -xf "$D/img.tar" -C "$D"
find "$D" -type f ! -name img.tar | while read -r f; do
  tar -tf "$f" 2>/dev/null | grep -E '(^|/)(\.claude|\.cursor|\.gemini|\.codex|\.specstory)/|(^|/)(\.mcp\.json|CLAUDE\.local\.md|\.env)$' \
    | sed "s|^|$(basename "$f"): |"
done
rm -rf "$D"
```

Empty output = clean. Any line = a compromised image: treat it as an incident (section 5),
because every tag that reuses that layer carries the file.

---

## 3. Guardrails

### 3.1 pre-commit (local)

`.git/hooks/pre-commit` (or the same content through the `pre-commit` / `lefthook` frameworks):

```sh
#!/bin/sh
# Blocks commits of coding-agent local files (they may hold approved commands with secrets)
PATTERN='(^|/)(\.claude/settings\.local\.json|CLAUDE\.local\.md)$'
hits=$(git diff --cached --name-only --diff-filter=ACMR | grep -E "$PATTERN")
if [ -n "$hits" ]; then
  echo "pre-commit: coding-agent local file staged:" >&2
  echo "$hits" | sed 's/^/  /' >&2
  echo "Remove it with: git rm --cached <file>  and add it to the project .gitignore" >&2
  exit 1
fi
```

`chmod +x .git/hooks/pre-commit`. Tested: it catches the file at the root and in
subdirectories. A local hook can be bypassed (`--no-verify`), which is why the CI gate below
is mandatory.

### 3.2 CI gate (the part that actually holds)

```yaml
# GitHub Actions, first job of the pipeline
- name: Coding-agent local file tracked?
  run: |
    if git ls-files | grep -E '(^|/)(\.claude/settings\.local\.json|CLAUDE\.local\.md)$'; then
      echo "::error::coding-agent local file is versioned. Rotate whatever it holds, then remove it (see the incident steps in the Sentinel skill)"
      exit 1
    fi
    git check-ignore -q .claude/settings.local.json || {
      echo "::error::.claude/settings.local.json is not in the project .gitignore"; exit 1; }
```

Add to the same pipeline a secret scan with rules for **passwords inside command syntax**
(`PGPASSWORD=`, `-p<password>`, `Authorization:`, `user:pass@`) and an image build followed by
the layer listing from section 2. The scan rules and the history scan belong to Redact.

### 3.3 Claude Code's own mechanisms (confirmed in the docs)

**Deny reads of secret files** (`~/.claude/settings.json` or managed settings). Path syntax:
`//absolute`, `~/home`, `/relative-to-the-settings-file`, `./relative-to-cwd`:

```json
{
  "permissions": {
    "deny": [
      "Read(./.env)",
      "Read(./.env.*)",
      "Read(**/.env)",
      "Read(~/.ssh/**)",
      "Read(~/.aws/**)",
      "Read(~/.pgpass)",
      "Read(~/.my.cnf)",
      "Read(~/.netrc)",
      "Read(~/.docker/config.json)",
      "Read(~/.claude.json)",
      "Read(~/.claude/.credentials.json)"
    ]
  }
}
```

Documented limit: a `Read` deny covers the file tools and the Bash commands Claude Code
recognizes (`cat`, `head`, `tail`, `sed`, redirections). It does **not** cover a `grep -r` that
does not name the file, or a Python/Node script that opens it. For OS-level enforcement, use
the sandbox (macOS: Seatbelt; Linux/WSL2: `bubblewrap` + `socat`; native Windows has no
sandbox):

```json
{
  "sandbox": {
    "enabled": true,
    "credentials": {
      "files": [
        { "path": "~/.aws/credentials", "mode": "deny" },
        { "path": "~/.ssh", "mode": "deny" }
      ],
      "envVars": [
        { "name": "GITHUB_TOKEN", "mode": "deny" },
        { "name": "NPM_TOKEN", "mode": "deny" }
      ]
    }
  }
}
```

Note: sandbox paths use the normal convention (`/tmp/x` is absolute, `~/x` is home), unlike
`Read(...)` rules. On Linux, an entry for a path that does not exist yet has no effect.

**A PreToolUse hook that denies literal credentials and environment dumps.** PreToolUse hooks
run **before** the permission prompt, and a block holds even when an `allow` rule matches. A
denied command does not run, produces no prompt and therefore **never becomes a saved rule**.
Requires `jq`.

`~/.claude/hooks/block-inline-secrets.sh` (`chmod +x`):

```bash
#!/bin/bash
# PreToolUse (matcher "Bash"): deny commands with a literal credential or an environment dump.
cmd=$(jq -r '.tool_input.command // empty')

deny() {
  jq -n --arg r "$1" '{hookSpecificOutput:{hookEventName:"PreToolUse",
    permissionDecision:"deny", permissionDecisionReason:$r}}'
  exit 0
}

# 1. VAR=literal on a secret-looking variable (VAR="$OTHER" passes)
if grep -Eq '(^|[[:space:];&|])[A-Za-z_]*(PASS(WORD)?|PWD|TOKEN|SECRET|API_?KEY|ACCESS_KEY)[A-Za-z_]*=["'"'"']?[^$[:space:]"'"'"']' <<<"$cmd"; then
  deny "Literal credential in the command. Use a variable loaded outside the agent, ~/.pgpass, a credential helper or a wrapper."
fi
# 2. password flag with a literal value: --password=x, --password x, --token x; mysql -pSECRET
if grep -Eq -- '--(password|passwd|token|api-key|secret)([=[:space:]])["'"'"']?[^$[:space:]"'"'"'-]|(^|[[:space:]])(mysql|mysqldump|mariadb)[[:space:]].*[[:space:]]-p[^$[:space:]]' <<<"$cmd"; then
  deny "Password/token as a literal argument. Use a credential file (~/.my.cnf, ~/.pgpass) or a variable."
fi
# 3. literal authorization header
if grep -Eiq 'authorization:[[:space:]]*(bearer|basic|token)[[:space:]]+[^$[:space:]"'"'"']' <<<"$cmd"; then
  deny "Authorization header with a literal value. Reference \$VAR or use a credential helper."
fi
# 4. URL with user:password
if grep -Eq '[a-z][a-z0-9+.-]*://[^/@[:space:]:]+:[^/@[:space:]$]+@' <<<"$cmd"; then
  deny "URL with an embedded user:password. Use ~/.netrc, ~/.pgpass or a variable."
fi
# 5. environment dump (env/printenv with no command, /proc/*/environ)
if grep -Eq '(^|[;&|][[:space:]]*)(env|printenv|export -p)[[:space:]]*($|[|;&>])|/proc/[^[:space:]]*/environ' <<<"$cmd"; then
  deny "Environment dump blocked: it prints secrets into the transcript. List the names only."
fi
exit 0
```

Registration (`~/.claude/settings.json`, or managed settings so it cannot be turned off):

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          { "type": "command", "command": "$HOME/.claude/hooks/block-inline-secrets.sh" }
        ]
      }
    ]
  }
}
```

Tested against 24 cases: it denies `PGPASSWORD=lit`, `Bearer lit`, `user:tok@`, `mysql -pLit`,
`--password lit`, `export API_KEY=lit`, `env`, `env | grep`, `printenv`, `/proc/1/environ`;
it lets through `PGPASSWORD="$X"`, `Bearer $TOKEN`, `mysql -p` (prompts), `--password-stdin`,
`env FOO=1 node x.js`, `ssh git@host`, `git commit -m "fix password reset"`. It is a text
heuristic: `docker inspect`, `docker exec ... env` or `docker compose config` also dump
secrets, so add patterns for your environment. A text hook also denies commands that merely
**quote** the pattern (a documentation heredoc): in that case write the file with the edit
tool instead of working around the hook.

**Managed settings** (shared server, CI, team machine). File location: Linux/WSL
`/etc/claude-code/managed-settings.json` (plus drop-ins in `managed-settings.d/`), macOS
`/Library/Application Support/ClaudeCode/managed-settings.json`, Windows
`C:\Program Files\ClaudeCode\managed-settings.json`. Nothing below it can override it:

```json
{
  "allowManagedPermissionRulesOnly": true,
  "allowManagedHooksOnly": true,
  "cleanupPeriodDays": 7,
  "permissions": {
    "disableBypassPermissionsMode": "disable",
    "allow": ["Bash(npm run *)", "Bash(git status)", "Bash(git diff *)"],
    "deny": ["Read(./.env)", "Read(./.env.*)", "Read(~/.ssh/**)", "Read(~/.aws/**)"]
  },
  "hooks": {
    "PreToolUse": [
      { "matcher": "Bash",
        "hooks": [ { "type": "command", "command": "/etc/claude-code/hooks/block-inline-secrets.sh" } ] }
    ]
  }
}
```

- `allowManagedPermissionRulesOnly: true`: only managed rules apply; per the docs it also
  **hides the "always allow" options in the prompt and stops saving new rules**. It is the
  only key that removes the leak mechanism at the root. Cost: every allow rule comes from the admin.
- `allowManagedHooksOnly: true`: user, project, local and plugin hooks do not run, which is
  why the hook goes into the managed file.
- `disableBypassPermissionsMode: "disable"`: no `--dangerously-skip-permissions`.
- On WSL, `/etc/claude-code` is writable by the user (the docs warn about this): it is not a
  boundary there.

---

## 4. Permission hygiene audit

Audit rule: **never print a whole rule or a value**. Print the tool, the first word, the
classification and the length. If something looks suspicious, Redact confirms and remediates it.

```bash
# allow rules: classify without exposing the command
audit_allow() { jq -r '
  .permissions.allow[]? as $r
  | ($r | capture("^(?<tool>[^(]+)(\\((?<pat>.*)\\))?$")) as $m
  | ($m.pat // "") as $p
  | ($p | sub("[ :].*$"; "") | sub("=.*$"; "=<…>")) as $w
  | (if $p == "" or $p == "*" then "BROAD (whole tool)"
     elif ($w | test("^(curl|wget|ssh|scp|sudo|docker|kubectl|bash|sh|zsh|python3?|node|npx|eval|rm|git|aws|gcloud|az|psql|mysql)$")) and ($p | test("\\*"))
       then "RISKY (wildcard on a powerful command)"
     elif ($p | test("\\*") | not) and ($p | test("=|@|--pass|--token|-p[^ ]|[Aa]uthorization|[Bb]earer"))
       then "SUSPECT (exact match that looks like a credential: Redact audit)"
     else "ok" end) as $v
  | "\($v)\t\($m.tool)(\($w)...)  len=\($p | length)"' "$1" | sort | uniq -c; }

for f in ~/.claude/settings.json ~/.claude/settings.local.json \
         ./.claude/settings.json ./.claude/settings.local.json; do
  [ -f "$f" ] && { echo "== $f"; audit_allow "$f"; }
done
```

What to reject:
- Bare `Bash` or `Bash(*)` in allow: the agent runs anything without a prompt. Acceptable only
  inside a disposable sandbox or VM.
- A wildcard on a powerful command: `Bash(curl *)`, `Bash(ssh *)`, `Bash(sudo *)`, `Bash(docker *)`,
  `Bash(git *)` (which includes `git -c core.fsmonitor=<program>`), `Bash(npx *)`, `Bash(python *)`.
  The docs warn that a `*` before the subcommand opens up the entire program.
- A wildcard on a destructive command (`rm`, `git push --force`, `kubectl delete`, `terraform apply`).
- Remember that Bash deny/ask rules are **not a boundary**: `Bash(curl *)` in deny does not
  catch `/usr/bin/curl` or `sh -c 'curl ...'` (per the docs). The real boundary is the sandbox.
- Any rule without a `*` that contains `=`, `@`, `-p`, `--password` or `Authorization`: probably a secret.

**MCP servers with plain-text tokens.** `~/.claude.json` holds local- and user-scope servers;
`.mcp.json` holds project servers (committed). Both accept `${VAR}` and `${VAR:-default}` in
`command`, `args`, `env`, `url` and `headers`. List only the names of fields that hold a literal:

```bash
jq -r '
  [ (.mcpServers // {} | to_entries[] | {scope:"user", name:.key, s:.value}),
    (.projects // {} | to_entries[] | .key as $proj
      | (.value.mcpServers // {}) | to_entries[] | {scope:$proj, name:.key, s:.value}) ][]
  | . as $e
  | ((.s.env // {}) + (.s.headers // {})) | to_entries[]
  | select(.value | test("\\$\\{") | not)
  | select(.key | test("TOKEN|KEY|SECRET|PASS|AUTH|URL|DSN|Authorization"; "i"))
  | "LITERAL\t\($e.scope)\t\($e.name)\t\(.key)"' ~/.claude.json
# same filter on ./.mcp.json (swap the file)
```

Fix: the value becomes `${NAME}` and the token moves to the environment or a secret manager,
or use `headersHelper` (a command that produces the header at connect time). Old copies of
`~/.claude.json` stay in `~/.claude/backups/` (up to five): the token remains there until it
is rotated.

**File permissions.** The docs say transcripts and history are not encrypted and that OS
permissions are the only protection. Recommended baseline (a recommendation, not the default):

```bash
stat -c '%a %U %n' ~/.claude ~/.claude.json ~/.claude/.credentials.json \
  ~/.claude/settings*.json ~/.pgpass ~/.my.cnf ~/.netrc 2>/dev/null
find ~/.claude -maxdepth 2 -perm /077 -printf '%m %p\n' | head     # anything group/other-readable
chmod 700 ~/.claude && chmod 600 ~/.claude.json ~/.claude/.credentials.json
```

**Transcripts and session data.** Everything that passed through a tool is kept in
`~/.claude/projects/<project>/<session>.jsonl` (plus `tool-results/`, `subagents/`) and deleted
after `cleanupPeriodDays` (default 30). These stay until you delete them: `~/.claude/history.jsonl`
(typed prompts) and `.heapsnapshot` files from `/heapdump` (they contain the conversation and the
process's credentials). Controls: lower `cleanupPeriodDays`; `CLAUDE_CODE_SKIP_PROMPT_HISTORY`
to write neither transcript nor history; `claude -p --no-session-persistence` in CI;
`claude purge <dir> --dry-run` to see and then delete one project's state. On a multi-user
server: each account's `~/.claude` at `700`, and never run the agent as root.

Quick environment checklist:
- [ ] `.claude/settings.local.json` and `CLAUDE.local.md` in the **project** `.gitignore`
      (`git check-ignore -v` points to `.gitignore`, not to the global excludes)
- [ ] `.dockerignore` with the agent directories, `.git/` and `.env*`; `npm pack --dry-run` clean
- [ ] pre-commit hook + CI gate from section 3
- [ ] no broad `allow` rule, and no exact-match rule that looks like a credential
- [ ] `Read` deny for `.env`, `~/.ssh`, `~/.aws`, `~/.pgpass`, `~/.netrc`, `~/.claude.json`
- [ ] PreToolUse hook against literal credentials and environment dumps
- [ ] MCP config without literal values in `env` / `headers`
- [ ] `~/.claude` at `700`, `~/.claude.json` and `.credentials.json` at `600`
- [ ] `cleanupPeriodDays` consistent with the risk; no forgotten `.heapsnapshot`
- [ ] on a shared server or CI: managed settings with `allowManagedPermissionRulesOnly`
- [ ] credentials the agent uses come from a helper (`~/.pgpass`, `~/.my.cnf`, `~/.netrc`, `gh`,
      docker `credsStore`, `aws` profiles) or from a wrapper that takes a name

---

## 5. Incident: I found a secret in an agent config file

Order matters. Deleting first and rotating later leaves the credential valid in history,
forks and images while you clean up.

1. **Rotate / revoke** every credential the file **ever held** (not only the current version):
   database passwords, API tokens, AWS keys, PATs. Check the provider's logs for misuse since
   the date of the file's first commit.
2. **Remove the local rule**: `/permissions` or edit the file; replace it with a pattern rule
   without the secret and with the helper or wrapper from section 1.
3. **Stop tracking it**: `git rm --cached .claude/settings.local.json`, an entry in the
   project `.gitignore`, `git check-ignore -v` to confirm, plus the pre-commit hook and CI gate.
4. **History**: rewrite it (filter-repo) and force-push only after rotation. The procedure,
   detection across the whole history and the sweep of the other agent files: **Redact skill**.
5. **Outside the repo**, wherever a copy survives:
   - forks (Apiiro found 211 forks of 74 repos carrying the same secrets) and open PRs;
   - container images: list the layers (section 2), delete the affected tags from the
     registry, rebuild with a `.dockerignore`; CI build caches;
   - published packages (npm/PyPI): `npm pack --dry-run` on the affected versions, deprecate/unpublish;
   - CI artifacts, release zips, backups;
   - machines: `~/.claude/projects/*` (transcripts), `~/.claude/backups/`, `~/.bash_history`.
6. **Record it**: what leaked, since when, what was rotated, where copies may still exist.

---

## 6. Other agents (only what their documentation confirms)

| Agent | Where the persistent approval goes | Implication |
|---|---|---|
| Claude Code | `.claude/settings.local.json` at the repo root (Bash, WebFetch). In VS Code the approval card lets you pick the file, including the shared `.claude/settings.json` | Inside the repo: `.gitignore` + `.dockerignore` + CI |
| Codex CLI | Approving / allow-listing in the TUI writes to `~/.codex/rules/default.rules` (user layer, Starlark `prefix_rule`). Project rules in `<repo>/.codex/rules/` load only when `.codex/` is trusted | Outside the repo by default; the risk is a dotfiles repo or a backup that carries `~/.codex/`. Test rules with `codex execpolicy check --rules ...` |
| Cursor CLI | Permissions in `~/.cursor/cli-config.json` (global) or `<project>/.cursor/cli.json`, rules shaped `Shell(cmd)`. On the official forum the team confirmed that "Always allow" writes to the **global** file when the project `cli.json` has a `permissions` section | Audit both; `.cursor/` in `.dockerignore`; scan before committing `cli.json` |
| Gemini CLI | Policies in `~/.gemini/policies/*.toml` (user), `/etc/gemini-cli/policies` (admin), workspace `.gemini/policies` (the docs say this tier does not work yet); settings in `~/.gemini/settings.json` and `.gemini/settings.json`. There is an "Allow for all future sessions" option, but the docs **do not say** which file it writes to | Treat `.gemini/` as sensitive; not confirmed whether the approval stores the literal command |
| Copilot CLI and others | Not confirmed in this review | Apply the same principle: find the persistent-approval file before trusting it |

GitGuardian and the CSA note recommend treating `.claude/`, `.cursor/`, `.gemini/`, `.codex/`,
`.specstory/`, `.mcp.json` and `CLAUDE.md` as files that can carry secrets, on the same level
as `.env`: scan them in pre-commit, CI, history and the registry.

---

## Sources

- GitGuardian, G. Valadon, "Claude Code settings.local.json Secrets: 17 months of exposure on
  GitHub, & Docker Hub", 9 Nov 2026: https://blog.gitguardian.com/claude-code-settings-local-json-secrets-docker-hub/
- Apiiro, "coding agents leaking secrets ... don't ask again", 5-6 Nov 2026:
  https://apiiro.com/blog/coding-agents-leaking-secrets-github-dont-ask-again
  (the page returned 403 to automated access; figures checked against the CSA note below, which cites the post)
- Cloud Security Alliance, "Approved Once, Leaked Forever: Secrets in Claude Code Settings
  Files", 8 Nov 2026: https://labs.cloudsecurityalliance.org/research/csa-research-note-claude-code-settings-secret-leak-20261108/
- Claude Code docs: Settings (https://code.claude.com/docs/en/settings), Permissions
  (https://code.claude.com/docs/en/permissions), Hooks (https://code.claude.com/docs/en/hooks),
  Managed settings (https://code.claude.com/docs/en/managed-settings), the .claude directory and
  application data (https://code.claude.com/docs/en/claude-directory), MCP
  (https://code.claude.com/docs/en/mcp), Sandboxing (https://code.claude.com/docs/en/sandboxing)
- Codex rules: https://learn.chatgpt.com/docs/agent-configuration/rules
- Cursor CLI permissions: https://cursor.com/docs/cli/reference/permissions ; forum thread:
  https://forum.cursor.com/t/cli-permission-allowlist-written-to-global-config-instead-of-project-level-cursor-cli-json/160343
- Gemini CLI policy engine: https://geminicli.com/docs/reference/policy-engine/
