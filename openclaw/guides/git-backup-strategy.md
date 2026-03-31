# Git Backup -- Brain Versioning

A practical guide to backing up your OpenClaw configuration, agent memories, and workspace data using git.

---

## 1. Why Version Your OpenClaw Config

Your OpenClaw configuration directory (`~/.openclaw/`) contains everything that makes your agent deployment unique:

- Agent personalities and behavioral rules (bootstrap files)
- Accumulated knowledge and memories
- Custom skills and automation scripts
- Cron job definitions
- Channel configurations and bindings

Losing this directory means rebuilding your agent from scratch -- including all the knowledge it has accumulated over time. Git backup protects against accidental deletion, misconfiguration, and server failure.

---

## 2. What to Version

### Include (stage and commit)

| Path | Contents | Why |
|------|----------|-----|
| `openclaw.json` | Master configuration | Core of the deployment |
| `workspaces/` | Per-agent bootstrap files (SOUL.md, MEMORY.md, AGENTS.md, TOOLS.md) | Agent personalities and rules |
| `workspace/` | Main agent workspace (scripts, memory files, helpers) | Automation and knowledge |
| `skills/` | Custom skill definitions | Modular capabilities |
| `cron/jobs.json` | Cron job definitions | Scheduled automation |
| `memory/*.md` | Markdown memory files | Long-term agent knowledge |
| `agents/*/agent/models.json` | Model metadata per agent | Model configuration |
| `devices/` | Device pairing data | Gateway device config |
| `credentials/discord-*` | Discord credential metadata | Channel identity |
| `canvas/` | Canvas data | Canvas state |
| `identity/device.json` | Device identity | Ties install to account |

### Exclude (.gitignore)

```gitignore
# === Secrets (NEVER commit) ===
.env
*.gpg
agents/*/agent/auth-profiles.json

# === Ephemeral data (regenerable or transient) ===
agents/*/sessions/
subagents/runs.json
cron/runs/

# === Binary indexes (regenerable from .md source) ===
memory/*.sqlite

# === Large/binary files ===
media/
browser/

# === Build artifacts ===
__pycache__/
*.pyc

# === Manual backups (git history replaces these) ===
*.bak
*.bak.*

# === Logs ===
logs/
backups/
```

---

## 3. Initial Setup

### Initialize the Repository

```bash
cd ~/.openclaw

# Remove any auto-created .git directories in subdirectories
find . -mindepth 2 -name ".git" -type d -exec rm -rf {} + 2>/dev/null

# Initialize
git init
git add .gitignore
git add openclaw.json workspaces/ workspace/ skills/ cron/jobs.json memory/*.md
git commit -m "initial backup"

# Add remote (private repo!)
git remote add origin git@github.com:<your-user>/<your-backup-repo>.git
git push -u origin main
```

### Safe Directory (when CLI runs as a different user)

If your management tools run as a different user than the file owner (e.g., root managing `~<your-user>/.openclaw/`):

```bash
git config --global safe.directory /home/<your-user>/.openclaw
```

---

## 4. Automated Backup Script

Create a backup script that runs on a schedule:

```bash
#!/bin/bash
# /usr/local/bin/openclaw-backup.sh
set -euo pipefail

LOG="/var/log/openclaw-backup.log"
TIMESTAMP=$(date '+%Y-%m-%d-%H%M')

backup_repo() {
  local DIR="$1"
  local LABEL="$2"

  if [ ! -d "$DIR/.git" ]; then
    echo "[$TIMESTAMP] SKIP $LABEL -- not a git repo" >> "$LOG"
    return
  fi

  cd "$DIR"

  # Check for changes
  if [ -z "$(git status --porcelain)" ]; then
    echo "[$TIMESTAMP] $LABEL -- no changes" >> "$LOG"
    return
  fi

  # Stage, commit, push
  git add -A
  git commit -m "auto-sync $TIMESTAMP" --quiet
  git push --quiet 2>> "$LOG"

  echo "[$TIMESTAMP] $LABEL -- backed up" >> "$LOG"
}

# Backup each instance
backup_repo "/home/<your-user>/.openclaw" "main"
# backup_repo "/home/<other-user>/.openclaw" "secondary"  # add more instances
```

### Schedule via Cron

```bash
# Root crontab -- every 4 hours
0 */4 * * * /usr/local/bin/openclaw-backup.sh
```

Check the log:
```bash
tail -20 /var/log/openclaw-backup.log
```

---

## 5. Security Rules

### Pre-Commit Audit

Before every push, verify no secrets are being committed:

```bash
cd ~/.openclaw
git ls-files | grep -iE '\.env|\.gpg|auth-profiles|google_token|whatsapp/'
# Output MUST be empty. If not, clean up immediately.
```

### Cleaning Already-Tracked Secrets

`.gitignore` only prevents **new** untracked files from being staged. Files that were committed before the ignore rules were added continue to be tracked.

**To remove already-tracked secrets:**

```bash
cd ~/.openclaw

# Remove from git index without deleting from disk
git rm --cached -r --ignore-unmatch agents/*/agent/auth-profiles.json
git rm --cached -r --ignore-unmatch agents/*/sessions/
git rm --cached --ignore-unmatch .env
git rm --cached -r --ignore-unmatch credentials/whatsapp/
git rm --cached --ignore-unmatch workspace/google_token.json
git rm --cached -r --ignore-unmatch cron/runs/ subagents/runs.json

# Commit the cleanup
git add .gitignore
git commit -m "cleanup: untrack sensitive and ephemeral files"
git push
```

### History Scrubbing (if secrets were committed)

If sensitive tokens were committed to history:

1. Rotate the compromised tokens immediately (before cleaning history)
2. Use `git filter-branch` or `BFG Repo Cleaner` to remove from history
3. Force push (this rewrites history)
4. Verify: `git log --all -p -- .env` should return nothing

### Rules Summary

- **Never** commit `.env` or `auth-profiles.json`
- **Always** verify with `git ls-files` before pushing
- Use a **private** repository (never public)
- Token in git history = compromised token. Rotate it.
- `identity/device-auth.json` is intentionally tracked -- it ties the install to the Anthropic account and is needed for restore

---

## 6. Disaster Recovery

When restoring OpenClaw on a new server:

### Step-by-Step Recovery

1. **Install OpenClaw** on the new server

2. **Clone the backup repository:**
   ```bash
   git clone git@github.com:<your-user>/<your-backup-repo>.git ~/.openclaw
   ```

3. **Recreate `.env` manually** with all required tokens:
   ```bash
   cat > ~/.openclaw/.env << 'EOF'
   DISCORD_TOKEN_DEFAULT=your-new-or-existing-token
   SLACK_BOT_TOKEN=xoxb-your-token
   OPENCLAW_GATEWAY_AUTH_TOKEN=your-gateway-token
   # Add all other required variables
   EOF
   chmod 600 ~/.openclaw/.env
   ```

4. **Recreate `auth-profiles.json`** via OpenClaw CLI:
   ```bash
   openclaw models auth login          # for API key auth
   openclaw models auth setup-token    # for token-based auth
   ```

5. **Set correct file ownership** (if service runs as a non-root user):
   ```bash
   chown -R <your-user>:<your-user> ~/.openclaw/
   ```

6. **Start the service:**
   ```bash
   systemctl start openclaw
   ```

7. **Verify health:**
   ```bash
   curl -s http://127.0.0.1:<port>/ready | python3 -m json.tool
   ```

### What Regenerates Automatically

- Memory search indexes (`*.sqlite`) -- rebuilt from `.md` files
- Session files -- agents start fresh (clean slate)
- Cron run history -- starts fresh
- Browser data -- rebuilt on first use

### What Needs Manual Recreation

- `.env` file (all API tokens and secrets)
- `auth-profiles.json` (LLM provider authentication)
- Device pairings (if `device-auth.json` was excluded)
- OAuth tokens (Google, etc.) -- re-run the auth flow

---

## 7. Best Practices

### Commit Hygiene

- Automated commits use timestamped messages: `auto-sync YYYY-MM-DD-HHMM`
- Manual changes should use descriptive messages: `update main agent personality`, `add jira integration skill`
- Review `git diff` before manual commits to catch unintended changes

### Branch Strategy

For most deployments, a single `main` branch is sufficient. The auto-backup script commits directly to main.

For A/B testing deployments, consider separate branches:
```
main        -- production config
experiment  -- A/B test variant
```

### Auto-Created .git Directories

OpenClaw may auto-create empty `.git` directories inside workspace subdirectories. These interfere with the parent git repo. Remove them before initializing:

```bash
find ~/.openclaw -mindepth 2 -name ".git" -type d -exec rm -rf {} + 2>/dev/null
```

### Monitoring Backup Health

Add a check to ensure backups are running:

```bash
# Check last backup timestamp
cd ~/.openclaw && git log --oneline -1
# Should show a recent auto-sync commit

# Check backup log
tail -5 /var/log/openclaw-backup.log
```

If backups stop silently (SSH key expired, remote repo deleted), you won't know until you need them. Include a backup health check in your monitoring setup.

### Multiple Instances

If running multiple OpenClaw instances, back up each to a **separate** private repository:

```bash
backup_repo "/home/user-a/.openclaw" "instance-a"
backup_repo "/home/user-b/.openclaw" "instance-b"
```

Never mix instance configs in a single repo -- they have different secrets and may diverge significantly.
