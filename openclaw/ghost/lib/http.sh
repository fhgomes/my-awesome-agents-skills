#!/bin/bash
# http.sh — HTTP helpers for Ghost API
# Wrappers around curl with error handling

set -euo pipefail

# === Make HTTP request with error handling ===
http_request() {
    local method="$1"
    local url="$2"
    local data="${3:-}"
    local headers="${4:-}"
    
    local curl_opts=(
        --silent
        --show-error
        --location
        --max-time 30
        -X "$method"
    )
    
    # Add headers
    if [[ -n "$headers" ]]; then
        curl_opts+=(-H "$headers")
    fi
    
    # Add data for POST/PUT
    if [[ -n "$data" ]] && [[ "$method" =~ ^(POST|PUT|PATCH)$ ]]; then
        curl_opts+=(-d "$data" -H "Content-Type: application/json")
    fi
    
    # Add cookies from session file if exists
    if [[ -f "${GHOST_SESSION_FILE:-}" ]]; then
        curl_opts+=(-b "${GHOST_SESSION_FILE}")
        curl_opts+=(-c "${GHOST_SESSION_FILE}")
    fi
    
    # Make request
    curl "${curl_opts[@]}" "$url"
}

# === Ghost login step 1: POST email + password ===
ghost_login_step1() {
    local ghost_url="${1:-$GHOST_URL}"
    local email="${2:-$GHOST_ADMIN}"
    local password="${3:-$GHOST_PASSWORD}"
    
    local login_url="${ghost_url}/ghost/api/v5/admin/authentication/passwordreset"
    local data=$(cat <<EOF
{
  "passwordReset": [{
    "email": "$email"
  }]
}
EOF
)
    
    echo "[*] Step 1: Sending login request to Ghost..." >&2
    http_request POST "$login_url" "$data" "Content-Type: application/json" || {
        echo "❌ Ghost login failed" >&2
        return 1
    }
    
    echo "[✓] Email sent with 2FA code" >&2
}

# === Ghost login step 2: POST email + password + 2FA code ===
ghost_login_step2() {
    local ghost_url="${1:-$GHOST_URL}"
    local email="${2:-$GHOST_ADMIN}"
    local password="${3:-$GHOST_PASSWORD}"
    local code="${4}"
    
    local login_url="${ghost_url}/ghost/api/v5/admin/authentication/signin"
    local data=$(cat <<EOF
{
  "login": "$email",
  "password": "$password"
}
EOF
)
    
    echo "[*] Step 2: Logging in with credentials..." >&2
    local response=$(http_request POST "$login_url" "$data")
    
    if echo "$response" | grep -q "access_token\|bearer\|authorization"; then
        echo "[✓] Login successful" >&2
        echo "$response" | tee "${GHOST_SESSION_FILE}"
        return 0
    else
        echo "❌ Login failed or 2FA required" >&2
        echo "$response" >&2
        return 1
    fi
}

# === Extract and save bearer token ===
save_session_token() {
    local json_file="${1:-$GHOST_SESSION_FILE}"
    
    if [[ ! -f "$json_file" ]]; then
        echo "❌ Session file not found: $json_file" >&2
        return 1
    fi
    
    # Extract token (adjust key based on actual Ghost API response)
    local token=$(grep -oP '"access_token"\s*:\s*"\K[^"]+' "$json_file" || echo "")
    
    if [[ -z "$token" ]]; then
        echo "❌ No access_token found in session file" >&2
        return 1
    fi
    
    echo "$token"
}

export -f http_request ghost_login_step1 ghost_login_step2 save_session_token
