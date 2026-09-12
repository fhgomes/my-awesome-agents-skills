# Git History Cleanup

**Destructive operation.** It rewrites the SHAs of every affected commit and all their
descendants, requires `push --force`, and breaks the clone of anyone who already has the repo.

**Never run it without explicit confirmation from the user.**

---

## Before you start, understand the limit

Rewriting history **does not undo a leak that was already public.**

If the repo was public, even for minutes:
- bots sweep GitHub in real time and cloud keys are exploited within minutes
- forks, mirrors and third-party local clones keep the old commits
- GitHub caches can serve the commit by SHA even after the force-push
- indexing services and the Wayback Machine may have copied it

So: **rotate the credential first, always.** Rewriting history is hygiene,
not remediation. The remediation is the rotation.

If the repo **was always private** and only you and your collaborators have clones, the
rewrite is enough — and still rotate if the key belongs to production.

---

## Step 0 — Backup

```bash
git clone --mirror /path/to/repo /path/to/backup-repo.git
# or simply
cp -r repo repo-backup
```

Confirm the backup opens before touching the original.

---

## Option A — `git filter-repo` (recommended)

Not shipped with git; check with `which git-filter-repo`. Install:
```bash
pip install git-filter-repo
```

### Remove a file from the whole history
```bash
cd repo
git filter-repo --invert-paths --path .env
git filter-repo --invert-paths --path config/secrets.yml --path deploy.pem
```

### Remove an entire directory
```bash
git filter-repo --invert-paths --path config/private/
```

### Replace the secret's text, keeping the files
Useful when the file must keep existing, but without the value.

```bash
cat > /tmp/replacements.txt <<'EOF'
RealPassword123==>***REMOVED***
AKIA_EXAMPLE_NOT_REAL==>***REMOVED***
sk_live_EXAMPLE_NOT_REAL==>***REMOVED***
EOF

git filter-repo --replace-text /tmp/replacements.txt
```

Afterwards **delete** `/tmp/replacements.txt` — it contains the secrets in plain text.

> `filter-repo` requires a fresh clone by default. On a repo with a dirty working tree it
> refuses; use `--force` only if you know you will not lose uncommitted work.

---

## Option B — BFG Repo-Cleaner

Requires Java. Download the `.jar` from the official site.

```bash
java -jar bfg.jar --delete-files .env repo.git
java -jar bfg.jar --replace-text replacements.txt repo.git

cd repo.git
git reflog expire --expire=now --all
git gc --prune=now --aggressive
```

BFG does not touch the latest commit (HEAD) — clean the file in the working tree and
commit **before** running it.

---

## Option C — `git filter-branch` (only if you cannot install anything)

Built into git, always available. It is slow and git itself discourages it, but it works.

```bash
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch .env" \
  --prune-empty --tag-name-filter cat -- --all

# clean up the refs filter-branch leaves behind
rm -rf .git/refs/original/
git reflog expire --expire=now --all
git gc --prune=now --aggressive
```

For several entries:
```bash
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch .env config/secrets.yml deploy.pem" \
  --prune-empty --tag-name-filter cat -- --all
```

---

## Final step — publish the rewrite

```bash
# confirm it is gone BEFORE pushing
git --no-pager log --all --oneline -- .env        # no output = removed
git --no-pager log -S'RealPassword123' --all --oneline

# push
git push origin --force --all
git push origin --force --tags
```

If GitHub still shows the old commit by URL/SHA, open a support ticket asking for
garbage collection — only they can clear the server-side cache.

---

## Critical step on a shared repo

After the force-push, **whoever did not rewrite must re-clone**:

```bash
# WRONG — recreates the old commits and undoes your cleanup
git pull

# RIGHT
cd ..
rm -rf project
git clone git@github.com:user/project.git
```

Agree beforehand: anyone with uncommitted work should save a patch first.
```bash
git diff > /tmp/my-work.patch     # before deleting the clone
git apply /tmp/my-work.patch      # after re-cloning
```

A force-push while a collaborator runs `git pull` in the middle is the recipe for the old
commits coming back and the secret reappearing.

---

## Closing checklist

- [ ] Credential **rotated** at the provider (done before anything else)
- [ ] Checked whether the old key was used by a third party (provider logs)
- [ ] Repo backup created and tested
- [ ] History rewritten and verified (`git log -S` returns nothing)
- [ ] Force-push done on all branches and tags
- [ ] Collaborators notified and re-cloned
- [ ] `.gitignore` fixed
- [ ] `.env.example` versioned
- [ ] Pre-commit hook installed (see `prevention.md`)
- [ ] Scanner run again: `scan_secrets.py . --history` → clean
