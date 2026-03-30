#!/bin/bash
# config.sh — Load Ghost + Gmail environment variables
# Used by: ghost-login.sh and other Ghost admin scripts

set -euo pipefail

# === Ghost Configuration ===
GHOST_URL="${GHOST_URL:-https://your-blog.com}"
GHOST_USER="${GHOST_USER:-}"  # From .env (GHOST_USER)
GHOST_ADMIN="${GHOST_ADMIN:-${GHOST_USER:-your@email.com}}"  # Alias for internal use
GHOST_PASSWORD="${GHOST_PASSWORD:-}"  # Load from .env if set
GHOST_SESSION_FILE="${GHOST_SESSION_FILE:-$HOME/.ghost/session.json}"

# === Gmail / SMTP Configuration (read from .env if exists) ===
GMAIL_USER="${GHOST_GMAIL_USER:-${GMAIL_USER:-}}"  # From .env (GHOST_GMAIL_USER)
GMAIL_APP_PASSWORD="${GHOST_GMAIL_PASSWORD:-${GMAIL_APP_PASSWORD:-}}"  # From .env (GHOST_GMAIL_PASSWORD)
GMAIL_IMAP_HOST="${GMAIL_IMAP_HOST:-imap.gmail.com}"
GMAIL_IMAP_PORT="${GMAIL_IMAP_PORT:-993}"

# === Load .env file if present ===
load_env() {
    local env_file="${1:-.env}"
    if [[ -f "$env_file" ]]; then
        set -a
        source "$env_file"
        set +a
        return 0
    fi
    return 1
}

# === Validate required vars ===
validate_config() {
    local required=("GHOST_URL" "GHOST_ADMIN" "GHOST_PASSWORD" "GMAIL_USER" "GMAIL_APP_PASSWORD")
    local missing=()
    
    for var in "${required[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            missing+=("$var")
        fi
    done
    
    if [[ ${#missing[@]} -gt 0 ]]; then
        echo "❌ Missing required environment variables:"
        printf '  - %s\n' "${missing[@]}"
        echo ""
        echo "Load from .env: source ./lib/config.sh && load_env /path/to/.env"
        return 1
    fi
    
    return 0
}

# === Export for subshells ===
export GHOST_URL GHOST_ADMIN GHOST_PASSWORD GHOST_SESSION_FILE
export GMAIL_USER GMAIL_APP_PASSWORD GMAIL_IMAP_HOST GMAIL_IMAP_PORT
