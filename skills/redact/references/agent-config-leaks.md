# Secrets in AI Coding-Agent Config Files

Coding agents write config files into the project, and some of those files hold the
literal command lines the developer approved. A password typed inline in a command ends up
in that file in plain text. This is now one of the most common leak paths, and the
standard scanners miss a large share of it, because the secret has no provider format.

Tool: `scripts/scan_agent_configs.py` (stdlib only, never prints a value).

---

## The mechanism (Claude Code, per the official settings docs)

- `.claude/settings.local.json` is the "project local" settings file. When you answer
  **"Yes, and don't ask again"** to a Bash permission prompt, Claude Code saves that approval
  there as a `permissions.allow` rule. The rule can be the exact command string, so
  `Bash(PGPASSWORD=… psql -h db …)` lands in the file with the password in it.
- Claude Code creates the file the first time you give a standing approval, and keeps it out
  of git by adding `**/.claude/settings.local.json` to the **global** git excludes file
  (`core.excludesFile`, else `$XDG_CONFIG_HOME/git/ignore`, else `~/.config/git/ignore`).
  Nothing in the repository ignores it. On another machine, an old clone, CI, a container
  build, `git add -f`, or when you created the file by hand, it is just another file.
- In a git repo the file lives at the **repository root** (since v2.1.211). Older versions
  wrote it in the starting directory, so nested copies exist in subfolders.
- The VS Code extension lets the approval card write to the **shared**
  `.claude/settings.json`, which is meant to be committed. Secrets end up there too.
- Precedence (highest first): managed → `--settings` → `.claude/settings.local.json` →
  `.claude/settings.json` → `~/.claude/settings.json`. List keys such as
  `permissions.allow` **merge** across files, so any of them can hold the leaked rule.
- Rule syntax that matters for review: `Bash(cmd)`, `Bash(cmd *)` / `Bash(cmd:*)` (prefix),
  `WebFetch(domain:…)`, `Read(./path)`. `WebFetch(url:https://user:pass@…)` and
  `Read(/path/with/token)` also leak.

### Other Claude Code files that can hold credentials

| File | What it holds | Commit? |
|---|---|---|
| `.claude/settings.local.json` | approved commands (`permissions.allow`), `env` | **never** |
| `.claude/settings.json` | team permissions, hooks, `env` block | yes, so it must stay secret-free |
| `.mcp.json` | project MCP servers: `command`, `args`, `env`, `url`, `headers` | yes, with `${VAR}` references only |
| `~/.claude.json` | account details, per-project MCP servers (`projects["<path>"].mcpServers`), trust state | never (home dir) |
| `~/.claude/settings.json` | user permissions, `env` | never (home dir) |
| `~/.claude/.credentials.json` | login credentials | never |
| `~/.claude/projects/<project>/<session>.jsonl` | **transcripts**: every tool call and its output, plain text | never |
| `~/.claude/history.jsonl` | typed prompts, including `!` shell commands | never |
| `~/.claude/backups/.claude.json.*` | old copies of `~/.claude.json` | never |
| `CLAUDE.local.md` | personal notes for the project; you must gitignore it yourself | never |

The docs state it plainly: transcripts and history are not encrypted; if a tool reads a
`.env` or a command prints a credential, the value is written to the transcript. Home-dir
files leak when someone copies `~/.claude` into a dotfiles repo, a backup, or an image.

`.mcp.json` supports `${VAR}` and `${VAR:-default}` in `command`, `args`, `env`, `url` and
`headers`. A literal token there is a finding; a reference is the correct pattern.

### Other agents (confirmed in their docs)

| Agent | Files | Secret-bearing fields |
|---|---|---|
| Cursor | `.cursor/mcp.json`, `~/.cursor/mcp.json` | `mcpServers.*.env`, `headers`, `args`; correct pattern `${env:NAME}` |
| VS Code (Copilot) | `.vscode/mcp.json` (`servers`, `inputs`), workspace `.mcp.json` | `env`, `headers`; correct pattern `inputs` with `"password": true` → `${input:id}` |
| Gemini CLI | `.gemini/settings.json`, `~/.gemini/settings.json` | `mcpServers.*.env`/`headers`; `tools.allowed` holds command strings such as `run_shell_command(…)` |
| Codex | `.codex/config.toml`, `~/.codex/config.toml`; `rules/*.rules` (e.g. `~/.codex/rules/default.rules`) | `mcp_servers.<id>.env`, `http_headers`; approved commands are saved as `prefix_rule(pattern=[…])` |
| Continue | `.continue/mcpServers/*.yaml` / `*.json`, `.continue/config.yaml` | `env`, `args`; correct pattern `${{ secrets.NAME }}` |
| Aider | `.aider.conf.yml` (home, repo root, cwd) | `openai-api-key`, `anthropic-api-key`, `api-key`, `set-env`; history in `.aider.chat.history.md`, `.aider.input.history` |
| SpecStory | `.specstory/` | saved agent chats (named in the Apiiro research as secret-bearing) |
| Devin (CLI/Desktop) | user `~/.config/devin/config.json` + `mcp_config.json` (`%APPDATA%\devin\` on Windows); project `.devin/config.json`, `.devin/config.local.json` (gitignored), `.devin/mcp_config.json`, `.devin/mcp_config.local.json` (gitignored), `.devin/hooks.v1.json` | `mcpServers.*.env`/`headers`, `permissions.allow` entries like `Exec(cmd)` (the approved command can sit there literally), `hooks.*.command`; project config holds only `permissions`, `read_config_from` and `hooks`. Older versions stored `mcpServers` inside `config.json` itself. Local session state lives in the CLI directory (`%APPDATA%\devin\cli\sessions.db`, a SQLite file) — the same "transcripts are plain text at rest" caveat applies |

Correct patterns are only correct when the referenced variable is set outside the repo.

---

## The blind spot: credentials typed into command arguments

Format-based scanners look for `AKIA…`, `ghp_…`, `sk-…`. A database password typed after
`-p` has no format. Shapes `scan_agent_configs.py` catches:

| Shape | Example (value elided) |
|---|---|
| Env prefix / export | `PGPASSWORD=… psql`, `MYSQL_PWD=… mysql`, `export FOO_TOKEN=…`, `DATABASE_URL=…` |
| Glued `-p` | `mysql -u root -p…`, `mysqldump -p…` |
| Long flags | `--password=…`, `--token …`, `--api-key …`, `--secret …`, `--client-secret …` |
| Short password flags | `sshpass -p …`, `docker/podman login -p …`, `redis-cli -a …`, `mongosh -p …`, `sqlcmd -P …`, `ldapsearch -w …`, `smbclient -U user%…` |
| curl / wget | `curl -u user:…`, `-H "Authorization: Bearer …"`, `-H "X-API-Key: …"`, `-H "Cookie: …"` |
| URLs | `postgresql://user:…@host`, `https://x-access-token:…@github.com/…`, `?access_token=…`, `&sig=…` |
| DSN | `password=…` / `Pwd=…` in libpq, JDBC, ADO strings |
| Cloud / k8s | `aws configure set aws_secret_access_key …`, `kubectl create secret … --from-literal=k=…` |
| Others | `openssl … -pass pass:…`, `npm config set //registry/:_authToken …`, `echo '…' \| sudo -S` |
| MCP / settings blocks | literal value in `env` under a secret-looking name, or in an auth header |

Not flagged (correct patterns): `$VAR`, `${VAR}`, `$(cmd)`, `${env:…}`, `${input:…}`,
`${{ secrets.… }}`, `--password-stdin`, `mysql -p` with no value (prompts), permission
wildcards (`Bash(PGPASSWORD=* psql:*)`), `-u 1000:1000`, ports, file paths.

Provider-format tokens are also checked, reusing the `scan_secrets.py` catalog.

---

## Audit

```bash
# one command for a whole tree: nested repos, history, Dockerfiles
python3 scripts/scan_agent_configs.py /path/to/workspace

# a home directory too (reads ~/.claude.json, ~/.claude/settings.json, transcripts)
python3 scripts/scan_agent_configs.py ~ --no-history

python3 scripts/scan_agent_configs.py /path --json          # machine-readable
python3 scripts/scan_agent_configs.py /path --no-transcripts  # skip *.jsonl (large)
```

Exit code 1 when anything is found. Output per finding: file, JSON path or line, rule,
`name` (env var / header name), and `value: ab… (len=N)` — the first two characters only
for values of 8+ characters, nothing for shorter ones. No snippet, no hash.

What the tracking-state section answers, per file:

| Check | Manual equivalent |
|---|---|
| Tracked now? | `git ls-files --error-unmatch -- .claude/settings.local.json` |
| Ever in history (even deleted)? | `git log --all --oneline -- .claude/settings.local.json` (`--diff-filter=A` for the commit that added it) |
| Who ignores it? | `git check-ignore -v --no-index .claude/settings.local.json` — the source column says `.gitignore` (project), `.git/info/exclude` (this clone only) or the global excludes path (this machine only) |
| Committed by/with Claude? | `git log --all --format='%h %ae' -- <file>` + `Co-Authored-By:` trailers |
| Shipped in an image? | a Dockerfile with `COPY . …` / `ADD . …` and no `.dockerignore`, or one that does not exclude `.claude/` |

Every version in history is parsed, so a secret that was later removed from the file is
still reported, with the oldest commit holding it.

**Docker:** `COPY` reads the build context, not the git index; `.gitignore` does not apply.
Without a `.dockerignore` (or `<Dockerfile>.dockerignore`) listing `.claude/`, the file goes
into every image built from that directory. The script assumes the context is the
Dockerfile's directory; check compose `build.context` / CI `docker build <dir>` by hand.

---

## Remediation

Order as always: **rotate → remove → clean history → prevent**.

1. **Rotate every credential the file ever held.** Not only what is in it now: the
   history scan lists old versions. Forks, clones and image layers keep copies. See the
   rotation table in `remediation.md`.
2. **Rewrite the rule so it carries no secret.** Edit the file or use `/permissions` to
   delete the entry. Then approve a form without the value:
   ```text
   BEFORE  Bash(PGPASSWORD=<literal> psql -h db -U app)
   AFTER   Bash(psql -h db -U app *)        # password from ~/.pgpass (chmod 600) or PGPASSWORD exported in the shell
   BEFORE  Bash(curl -H "Authorization: Bearer <literal>" https://api/...)
   AFTER   Bash(curl -H "Authorization: Bearer $API_TOKEN" https://api/...)
   BEFORE  Bash(docker login -u bot -p <literal> registry)
   AFTER   Bash(docker login -u bot --password-stdin registry)   # or a credential helper
   ```
   Other options: credential helpers (`git credential`, docker `credsStore`, `aws` profiles),
   `.my.cnf` / `.pgpass` outside the repo with `600` permissions, a small wrapper script that
   reads from a secret manager and is approved as `Bash(./scripts/db.sh *)`. Prefer narrow
   prefixes over broad ones like `Bash(curl:*)`.
   For MCP: `"env": {"API_KEY": "${API_KEY}"}`, `"Authorization": "Bearer ${API_KEY}"`,
   VS Code `inputs` with `"password": true`, Codex `bearer_token_env_var` / `env_http_headers`.
3. **Stop tracking it, in the project:**
   ```bash
   git rm --cached .claude/settings.local.json
   printf '.claude/settings.local.json\nCLAUDE.local.md\n' >> .gitignore
   printf '.claude/\n.git\n.env\n' >> .dockerignore      # create it if missing
   git add .gitignore .dockerignore && git commit -m "chore: keep agent local files out of git and images"
   ```
   The global excludes protect one machine. The project `.gitignore` protects every clone.
4. **History:** if the scan reports `[history:…]`, follow `history-rewrite.md`
   (`git filter-repo --invert-paths --path .claude/settings.local.json`, or
   `--replace-text` to keep the file). Destructive: confirm with the user first.
5. **Published Docker images:** a rebuilt image does not remove the old ones. Rotate the
   credential, rebuild with the `.dockerignore` in place, then **delete the affected tags**
   from the registry (each tag is a separate copy; one leaked token was found in hundreds of
   tags of the same image). Check that the file is gone: `docker run --rm --entrypoint ls
   <image> -la /app/.claude` (adjust the path).
6. **Home-dir files** (`~/.claude.json`, transcripts): never copy `~/.claude` into a repo or
   image. To clear one project's local state: `claude purge <path>`. Lower
   `cleanupPeriodDays` to keep transcripts for less time.

## Prevention

- `.gitignore` and `.dockerignore` entries above in **every** repo where an agent runs, not
  only on your machine. Add the other agents' personal files the same way.
- Pre-commit hook blocks `.claude/settings.local.json` (see `prevention.md`).
- Never type a credential into a command you approve with "don't ask again". Export it in
  the shell first, or use a credential helper.
- Review `.claude/settings.local.json` before publishing, like a `.env`.
- Run `scan_agent_configs.py` in the pre-publication pass and in CI.

---

## Research behind this (as of November 2026)

**GitGuardian** — blog post by G. Valadon, 9 Nov 2026
(<https://blog.gitguardian.com/claude-code-settings-local-json-secrets-docker-hub/>),
public GitHub, January 2025 to 7 November 2026:
- `.claude/settings.local.json`: 31,088 distinct secrets in 23,276 repositories; 5,343
  valid when detected. `.claude/settings.json`: 8,271 secrets in 6,839 repositories, 1,283 valid.
- Public Docker Hub: 613 distinct secrets in these files, 99 valid, across 543 image
  repositories and 7,625 tags; one valid Cloudflare token in 559 tags of one image.
- In 263 repositories the leaking commit was authored by Claude's noreply address.
- Generic detectors (passwords, high-entropy strings, bearer tokens, `user:pass`) account
  for 63% of occurrences. About half the leaking rules were `curl` commands, about 15%
  `VAR=value` prefixes.

**Apiiro** — research published 5 Nov 2026 (<https://apiiro.com/blog/coding-agents-leaking-secrets-github-dont-ask-again>;
the page refused automated access, figures as reported by The Hacker News,
<https://thehackernews.com/2026/11/claude-codes-dont-ask-again-file.html>):
- 104,185 public copies of `.claude/settings.local.json` in 103,617 repositories; 1,122
  held at least one real secret, 1,379 distinct secrets; in half of the affected repos the
  file had been there at least 217 days.
- 734 more secrets in 509 repositories only in older versions; 2,539 secrets in 1,994
  repositories counting the shared settings file, history and saved agent transcripts.
- gitleaks flagged 564 and TruffleHog 643 of the 1,122 files; neither flagged 215.
- In 539 of 1,105 repositories a commit with Claude as co-author changed the file.
- Of 16 coding agents compared, Claude Code was the only one confirmed to save the full
  approved command in a project file by default.

The two studies count different things (all versions pushed since Jan 2025 vs. current
copies), so their numbers are not comparable.

**Claude Code docs** — settings files and precedence: <https://code.claude.com/docs/en/settings>;
files under `.claude/` and `~/.claude/`, transcripts, `claude purge`:
<https://code.claude.com/docs/en/claude-directory>; MCP scopes and `${VAR}` expansion:
<https://code.claude.com/docs/en/mcp>.
