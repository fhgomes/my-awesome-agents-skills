#!/bin/bash
# Restore most recent OpenClaw config backup
set -euo pipefail

CONFIG="${OPENCLAW_CONFIG:-~/.openclaw/openclaw.json}"
BACKUP_DIR="$(dirname "$CONFIG")/config-backups"

LATEST=$(ls -t "$BACKUP_DIR"/openclaw-*.json 2>/dev/null | head -1)

if [[ -z "$LATEST" ]]; then
    echo "Error: No backups found in $BACKUP_DIR"
    exit 1
fi

echo "Restoring from: $LATEST"
cp "$LATEST" "$CONFIG"
echo "Config restored successfully."
echo "Run 'openclaw doctor --non-interactive' to verify."
