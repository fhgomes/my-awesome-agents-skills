# config-guardian

Validate and safeguard OpenClaw configuration updates.

## Purpose

Prevent invalid or broken OpenClaw configurations through automated backups, schema validation, and safe rollback.

## Features

- **Automatic backups** — Create timestamped snapshots before every edit
- **Schema validation** — Verify JSON syntax and OpenClaw config structure
- **Safe rollback** — Restore from most recent backup if validation fails
- **Diff review** — See exactly what changed before applying

## Quick Start

```bash
# Backup current config
bash scripts/backup.sh

# Validate before changes
bash scripts/validate.sh

# Make your change to openclaw.json
# ...

# Validate after changes
bash scripts/validate.sh

# Review what changed
bash scripts/diff.sh

# Restore if something broke
bash scripts/restore.sh
```

## Workflow

1. Call `backup.sh` before editing
2. Make your changes (minimal and focused)
3. Call `validate.sh` to check syntax and schema
4. If validation fails, call `restore.sh` immediately
5. Call `diff.sh` to review changes
6. Request explicit approval before restarting gateway

## Requirements

- `openclaw` CLI installed
- `python3` available
- Read/write access to `~/.openclaw/openclaw.json`

## Environment Variables

- `OPENCLAW_CONFIG` — Path to alternate config file (default: `~/.openclaw/openclaw.json`)

```bash
OPENCLAW_CONFIG=/path/to/config.json bash scripts/backup.sh
```

## See Also

- [SKILL.md](SKILL.md) — Full documentation
