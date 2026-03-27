#!/bin/bash
# Validate OpenClaw config via openclaw doctor
set -euo pipefail

CONFIG="${OPENCLAW_CONFIG:-~/.openclaw/openclaw.json}"

if [[ ! -f "$CONFIG" ]]; then
    echo "Error: Config not found at $CONFIG"
    exit 1
fi

# Check JSON syntax first
if ! python3 -c "import json; json.load(open('$CONFIG'))" 2>/dev/null; then
    echo "FAIL: Invalid JSON syntax in $CONFIG"
    exit 1
fi

echo "JSON syntax: OK"

# Run openclaw doctor for schema validation
if openclaw doctor --non-interactive 2>&1; then
    echo "Schema validation: OK"
else
    echo "WARN: openclaw doctor reported issues (see above)"
    exit 1
fi
