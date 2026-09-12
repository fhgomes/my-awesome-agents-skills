# Prevention — So It Does Not Happen Again

The goal is to make a leak **impossible by accident**, not to rely on remembering.

---

## 1. Complete `.gitignore`

```gitignore
# Secrets and environment
.env
.env.*
!.env.example
!.env.template
*.local

# Keys and certificates
*.pem
*.key
*.p12
*.pfx
*.jks
*.keystore
id_rsa
id_ed25519
*.ppk

# Tool credentials
.npmrc
.pypirc
.netrc
.pgpass
credentials.json
service-account*.json
serviceAccount*.json
.aws/
kubeconfig
*.ovpn

# Terraform (state stores secrets in plain text)
*.tfstate
*.tfstate.*
.terraform/
*.tfvars
!example.tfvars

# Local IDE config that may hold a token
.vscode/settings.json
.idea/workspace.xml

# Dumps and databases
*.sql
*.dump
*.sqlite
*.sqlite3
*.db

# Backups
*.bak
*.backup
*.old
*~

# OS
.DS_Store
Thumbs.db
```

Adapt it to the project — if the repo legitimately versions `.sql` migrations, replace
the rule with something more specific (`dumps/*.sql`).

**Remember:** `.gitignore` only affects files that are not yet tracked. For files already
tracked, use `git rm --cached` (see `remediation.md`).

---

## 2. Pre-commit hook

Blocks the commit before the secret enters history. Works without installing anything.

Create `.git/hooks/pre-commit`:

```bash
#!/usr/bin/env bash
# Blocks commits with an apparent secret. Deliberate bypass: git commit --no-verify
set -uo pipefail

STAGED=$(git diff --cached --name-only --diff-filter=ACM)
[ -z "$STAGED" ] && exit 0

FAIL=0

# 1) files that must never be committed
for f in $STAGED; do
  case "$f" in
    .env|.env.*|*.pem|*.key|*.p12|*.pfx|*.jks|id_rsa|id_ed25519|*.tfstate|.npmrc|.pgpass)
      case "$f" in
        .env.example|.env.template|.env.sample) ;;
        *) echo "BLOCKED: $f must not be versioned"; FAIL=1 ;;
      esac
      ;;
  esac
done

# 2) secret patterns in the staged content
PATTERNS='(AKIA|ASIA)[A-Z0-9]{16}|gh[pousr]_[A-Za-z0-9]{36}|glpat-[A-Za-z0-9_-]{20}|xox[baprs]-[A-Za-z0-9-]{10}|sk_live_[A-Za-z0-9]{20}|sk-ant-[A-Za-z0-9_-]{20}|AIza[A-Za-z0-9_-]{35}|-----BEGIN [A-Z ]*PRIVATE KEY-----|(password|senha|secret|api[_-]?key)[[:space:]]*[:=][[:space:]]*["'"'"'][^"'"'"'${]{8,}["'"'"']'

if git diff --cached -U0 | grep -nEi "$PATTERNS" >/dev/null 2>&1; then
  echo "BLOCKED: possible secret in the diff:"
  git diff --cached -U0 | grep -nEi "$PATTERNS" | sed 's/^/  /' | head -10
  FAIL=1
fi

if [ "$FAIL" -ne 0 ]; then
  echo
  echo "Fix it, or use 'git commit --no-verify' if it is a false positive."
  exit 1
fi
exit 0
```

```bash
chmod +x .git/hooks/pre-commit
```

Hooks in `.git/hooks/` **are not versioned** — each person installs their own. To share
it with collaborators, version it under `.githooks/` and point git there:

```bash
mkdir -p .githooks && mv .git/hooks/pre-commit .githooks/
chmod +x .githooks/pre-commit
git config core.hooksPath .githooks
git add .githooks && git commit -m "chore: pre-commit hook against secrets"
```

Each person runs once after cloning:
```bash
git config core.hooksPath .githooks
```

---

## 3. GitHub-side protections

Public repos (free) and private repos (paid plans):
- **Settings → Code security → Secret scanning:** turn it on. GitHub detects and, with
  *push protection*, blocks a push that contains a known secret.
- **Push protection:** enable it. It is the safety net that catches what the local hook missed.
- **Dependabot alerts:** for vulnerable dependencies.

GitHub secret scanning covers partner-provider formats (AWS, Stripe, etc.) — it does not
catch generic passwords or personal data. It does not replace the audit.

---

## 4. Ongoing hygiene

- **Secrets shared between contributors:** password manager (Bitwarden, 1Password) or
  secret manager. Never WhatsApp, Slack, e-mail or screenshots.
- **One secret per environment:** dev, staging and prod with different credentials. A dev
  leak does not take down prod.
- **Periodic rotation** of production keys, even without an incident.
- **Least privilege:** the key the app uses does not need to be admin. A leaked read-only
  key does far less damage.
- **Test data is FAKE data.** Never copy a production dump into a fixture. Use faker to
  generate CPFs, names, e-mails. A real CPF in a fixture is a personal-data leak with
  LGPD implications.

---

## 5. Checklist before making a repo public

- [ ] `scan_secrets.py . --history` with no critical/high finding
- [ ] History scanned, not just the working tree
- [ ] No `.env`, `.pem`, `.key`, `credentials.json` tracked
- [ ] `.gitignore` covers secrets, keys, dumps, backups
- [ ] `.env.example` versioned, with empty keys
- [ ] No internal IP, production hostname or private endpoint in the code
- [ ] Fixtures use fake data, not real customer data
- [ ] README has no screenshot with a token, e-mail or personal data
- [ ] Issues, PRs and commit messages reviewed (they go public too)
- [ ] Repo wiki and releases reviewed
- [ ] Credentials that were ever committed have been **rotated**
- [ ] Secret scanning + push protection enabled on GitHub
- [ ] License chosen (not security, but this is the moment to decide)

Commit messages and issue titles leak with the same reach as the code —
`git log --all --grep='password'` tends to bring surprises.
