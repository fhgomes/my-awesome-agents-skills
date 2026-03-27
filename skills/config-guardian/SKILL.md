---
name: config-guardian
description: Validate and safeguard OpenClaw config updates (openclaw.json or openclaw config set/apply). Use this skill whenever changing gateway config, models, channels, agents, tools, sessions, or routing. Enforces backup, schema validation, and safe rollback before restarts. Use when changing OpenClaw configuration.
---

# Config Guardian

## Overview
Use this workflow whenever editing `~/.openclaw/openclaw.json` or running `openclaw config set/apply`. Prevents invalid config, creates backups, validates against schema, and enables rollback.

## Workflow (use every time)

1. **Preflight**
   - Confirm the requested change and scope
   - Check for sensitive keys (tokens, credentials)

2. **Backup**
   ```bash
   bash {baseDir}/scripts/backup.sh
   ```

3. **Validate (before change)**
   ```bash
   bash {baseDir}/scripts/validate.sh
   ```
   If validation fails, stop and report.

4. **Apply change**
   - Prefer `openclaw config set <path> <value>` for small changes
   - For complex edits, edit the file directly and keep diffs minimal

5. **Validate (after change)**
   ```bash
   bash {baseDir}/scripts/validate.sh
   ```
   If it fails, restore from backup:
   ```bash
   bash {baseDir}/scripts/restore.sh
   ```

6. **Diff review**
   ```bash
   bash {baseDir}/scripts/diff.sh
   ```

7. **Restart (only with explicit approval)**
   - If change requires restart, ASK for approval first
   - Use `openclaw gateway restart`

## Guardrails
- **Never** restart or apply config without explicit user approval
- **Never** remove keys or reorder blocks unless requested
- **Always** keep a backup before edits
- If unsure about schema: run `openclaw doctor --non-interactive` and stop on errors

## Multi-environment Support
For environments with multiple OpenClaw instances, pass `OPENCLAW_CONFIG` environment variable:
```bash
OPENCLAW_CONFIG=/path/to/alternate/openclaw.json bash {baseDir}/scripts/backup.sh
```
