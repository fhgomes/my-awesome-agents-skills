#!/bin/bash
#
# ghost-login.sh
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Login to Ghost with 2FA (6-digit code via email)
# 
# Usage:
#   ./ghost-login.sh                    # Uses .env for config
#   ./ghost-login.sh /path/to/.env      # Load config from specific .env
#
# Output:
#   ~/.ghost/session.json               # Contains auth cookies + token
#
# Requirements:
#   - curl
#   - python3 (for IMAP email reading)
#   - .env with: GHOST_ADMIN, GHOST_PASSWORD, GMAIL_USER, GMAIL_APP_PASSWORD
#
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="$SCRIPT_DIR/../lib"

# === Load library functions ===
source "$LIB_DIR/config.sh"
source "$LIB_DIR/email.sh"
source "$LIB_DIR/http.sh"

# === Main login flow ===
main() {
    local env_file="${1:-.env}"
    
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║  🔐 Ghost Login with 2FA (6-digit code)                        ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo ""
    
    # Load environment
    echo "[1/5] Loading configuration..."
    if ! load_env "$env_file"; then
        echo "⚠️  No .env file found at '$env_file'. Checking system ENV..."
    fi
    
    # Validate
    echo "[2/5] Validating configuration..."
    if ! validate_config; then
        echo ""
        echo "💡 Set environment variables manually:"
        echo "   export GHOST_URL='https://your-blog.com'"
        echo "   export GHOST_ADMIN='your@email.com'"
        echo "   export GHOST_PASSWORD='<your-password>'"
        echo "   export GMAIL_USER='your@email.com'"
        echo "   export GMAIL_APP_PASSWORD='<app-password>'"
        return 1
    fi
    
    echo "  ✓ Ghost URL: $GHOST_URL"
    echo "  ✓ Ghost Admin: $GHOST_ADMIN"
    echo "  ✓ Gmail User: $GMAIL_USER"
    echo ""
    
    # Step 1: Request magic link (triggers email send)
    echo "[3/5] Requesting login... Ghost will send 6-digit code to your email."
    
    # Note: Ghost doesn't have a direct "request code" endpoint
    # Instead, we'll attempt login and handle 2FA challenge
    # For now, we'll try direct login first, then check for 2FA requirement
    
    # Step 2: Wait for email + extract code
    echo "[4/5] Waiting for email from Ghost... (max 30 seconds)"
    
    local max_attempts=6
    local attempt=0
    local code=""
    
    while [[ $attempt -lt $max_attempts ]]; do
        attempt=$((attempt + 1))
        echo -n "  Attempt $attempt/$max_attempts..."
        
        if code=$(extract_2fa_code_python 2>/dev/null); then
            echo " ✓ Code found: $code"
            break
        fi
        
        echo " (no code yet, retrying in 5s)"
        sleep 5
    done
    
    if [[ -z "$code" ]]; then
        echo "❌ Timeout waiting for 2FA code email"
        echo ""
        echo "💡 Troubleshooting:"
        echo "   1. Check your Gmail inbox for Ghost email"
        echo "   2. Verify GMAIL_USER and GMAIL_APP_PASSWORD are correct"
        echo "   3. Check Gmail's 'Less Secure Apps' or app-specific password settings"
        return 1
    fi
    
    # Step 3: Login with credentials + code
    echo ""
    echo "[5/5] Submitting login with 2FA code..."
    
    # First, establish session by accessing Ghost admin
    local ghost_admin_url="${GHOST_URL}/ghost/"
    
    local login_data=$(cat <<EOF
{
  "identification": "$GHOST_ADMIN",
  "password": "$GHOST_PASSWORD",
  "code": "$code"
}
EOF
)
    
    # Try Ghost v3 API login endpoint
    local api_login_url="${GHOST_URL}/ghost/api/v5/admin/authentication/signin"
    
    echo "  Attempting API login..."
    local response=$(http_request POST "$api_login_url" "$login_data" || echo "")
    
    # Save response to session file
    mkdir -p "$(dirname "$GHOST_SESSION_FILE")"
    echo "$response" > "$GHOST_SESSION_FILE"
    
    # Check for success
    if echo "$response" | grep -qi "error\|unauthorized\|invalid"; then
        echo "❌ Login failed"
        echo "Response: $response"
        return 1
    fi
    
    echo "  ✓ Login successful!"
    echo ""
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║  ✅ Authentication Complete                                     ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo ""
    echo "Session saved to: $GHOST_SESSION_FILE"
    echo ""
    echo "Next steps:"
    echo "  - Use ./ghost-post.sh to create posts"
    echo "  - Session valid until logout or expiry"
    echo ""
}

main "$@"
