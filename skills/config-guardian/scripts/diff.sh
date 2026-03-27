#!/bin/bash
# Diff current config vs most recent backup
set -euo pipefail

CONFIG="${OPENCLAW_CONFIG:-~/.openclaw/openclaw.json}"
BACKUP_DIR="$(dirname "$CONFIG")/config-backups"

LATEST=$(ls -t "$BACKUP_DIR"/openclaw-*.json 2>/dev/null | head -1)

if [[ -z "$LATEST" ]]; then
    echo "No backups to diff against."
    exit 0
fi

echo "Comparing: $CONFIG vs $LATEST"
echo "---"
diff --color=auto -u "$LATEST" "$CONFIG" || true
