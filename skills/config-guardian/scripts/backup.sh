#!/bin/bash
# Backup OpenClaw config with timestamp
set -euo pipefail

CONFIG="${OPENCLAW_CONFIG:-~/.openclaw/openclaw.json}"
BACKUP_DIR="$(dirname "$CONFIG")/config-backups"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_FILE="$BACKUP_DIR/openclaw-$TIMESTAMP.json"

if [[ ! -f "$CONFIG" ]]; then
    echo "Error: Config not found at $CONFIG"
    exit 1
fi

mkdir -p "$BACKUP_DIR"
cp "$CONFIG" "$BACKUP_FILE"

# Keep only last 20 backups
ls -t "$BACKUP_DIR"/openclaw-*.json 2>/dev/null | tail -n +21 | xargs -r rm

echo "Backup created: $BACKUP_FILE"
echo "Total backups: $(ls "$BACKUP_DIR"/openclaw-*.json 2>/dev/null | wc -l)"
