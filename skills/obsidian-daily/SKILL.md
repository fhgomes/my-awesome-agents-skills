---
name: obsidian-daily
description: Manage Obsidian Daily Notes via obsidian-cli. Create and open daily notes, append entries (journals, logs, tasks, links), read past notes by date, and search vault content. Handles relative dates like "yesterday", "last Friday", "3 days ago". Use when you need to write a note, add to daily notes, or interact with Obsidian vault.
metadata: {"openclaw":{"emoji":"📝","requires":{"bins":["obsidian-cli"]}}}
---

# Obsidian Daily Notes

Interact with Obsidian Daily Notes: create notes, append entries, read by date, and search content.

## Setup

Check if a default vault is configured:

```bash
obsidian-cli print-default --path-only 2>/dev/null && echo "OK" || echo "NOT_SET"
```

If `NOT_SET`, ask the user for:
1. **Vault name** (required)
2. **Daily notes folder** (default: vault root, common: `Daily Notes`, `Journal`, `daily`)
3. **Date format** (default: `YYYY-MM-DD`)

Configure:
```bash
obsidian-cli set-default "VAULT_NAME"
```

## Date Handling

```bash
# Today
date +%Y-%m-%d
# Yesterday
date -d yesterday +%Y-%m-%d
# Last Friday
date -d "last friday" +%Y-%m-%d
# 3 days ago
date -d "3 days ago" +%Y-%m-%d
# Next Monday
date -d "next monday" +%Y-%m-%d
```

## Commands

### Open/Create Today's Note
```bash
obsidian-cli daily
```

### Append Entry
```bash
obsidian-cli daily && obsidian-cli create "$(date +%Y-%m-%d).md" --content "$(printf '\n%s' "ENTRY_TEXT")" --append
```

With custom folder:
```bash
obsidian-cli daily && obsidian-cli create "Daily Notes/$(date +%Y-%m-%d).md" --content "$(printf '\n%s' "ENTRY_TEXT")" --append
```

### Read Note
```bash
# Today
obsidian-cli print "$(date +%Y-%m-%d).md"
# Specific date
obsidian-cli print "2026-03-07.md"
# Yesterday
obsidian-cli print "$(date -d yesterday +%Y-%m-%d).md"
```

### Search Content
```bash
obsidian-cli search-content "TERM"
```

### Specific Vault
Add `--vault "NAME"` to any command:
```bash
obsidian-cli print "2026-03-07.md" --vault "Work"
```

## Use Cases

**Journal entry:**
```bash
obsidian-cli create "$(date +%Y-%m-%d).md" --content "$(printf '\n%s' "- Went to the doctor")" --append
```

**Task:**
```bash
obsidian-cli create "$(date +%Y-%m-%d).md" --content "$(printf '\n%s' "- [ ] Buy groceries")" --append
```

**Timestamped log:**
```bash
obsidian-cli create "$(date +%Y-%m-%d).md" --content "$(printf '\n%s' "- $(date +%H:%M) Deploy completed")" --append
```
