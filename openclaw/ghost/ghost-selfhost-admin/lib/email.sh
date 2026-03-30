#!/bin/bash
# email.sh — Read 2FA code from Gmail IMAP
# Extracts 6-digit code from Ghost login email

set -euo pipefail

# === Read most recent email and extract 6-digit code ===
# Usage: extract_2fa_code
# Returns: 6-digit code or error

extract_2fa_code() {
    local user="${1:-$GMAIL_USER}"
    local password="${2:-$GMAIL_APP_PASSWORD}"
    local imap_host="${3:-${GMAIL_IMAP_HOST:-imap.gmail.com}}"
    local imap_port="${4:-${GMAIL_IMAP_PORT:-993}}"
    local timeout=30
    
    echo "[*] Connecting to IMAP (${imap_host}:${imap_port}) as ${user}..." >&2
    
    # Use openssl s_client to connect to IMAP over TLS
    # Read the latest email and search for 6-digit code
    local response=$(
        timeout "$timeout" openssl s_client -quiet -connect "${imap_host}:${imap_port}" 2>/dev/null <<EOF
a LOGIN "${user}" "${password}"
b FETCH 1 BODY[TEXT]
c LOGOUT
EOF
    )
    
    # Extract 6-digit code (look for pattern like "123456" or "Code: 123456")
    local code=$(echo "$response" | grep -oP '\b\d{6}\b' | head -1)
    
    if [[ -z "$code" ]]; then
        echo "❌ No 6-digit code found in email" >&2
        return 1
    fi
    
    echo "$code"
    return 0
}

# === Alternative: Python-based IMAP reader (more reliable) ===
# Requires: Python 3 + imaplib (stdlib)

extract_2fa_code_python() {
    local user="${1:-$GMAIL_USER}"
    local password="${2:-$GMAIL_APP_PASSWORD}"
    local imap_host="${3:-${GMAIL_IMAP_HOST:-imap.gmail.com}}"
    local imap_port="${4:-${GMAIL_IMAP_PORT:-993}}"
    
    python3 << PYTHON_EOF
import imaplib
import re
import sys
from email import message_from_bytes

user = "$user"
password = "$password"
host = "$imap_host"
port = $imap_port

try:
    # Connect to IMAP
    print(f"[*] Connecting to {host}:{port}...", file=sys.stderr)
    imap = imaplib.IMAP4_SSL(host, port)
    imap.login(user, password)
    imap.select('INBOX')
    
    # Get latest email
    status, messages = imap.search(None, 'ALL')
    if not messages or not messages[0]:
        print("❌ No emails found", file=sys.stderr)
        sys.exit(1)
    
    latest_id = messages[0].split()[-1]  # Last email
    status, msg_data = imap.fetch(latest_id, '(RFC822)')
    
    # Parse email body
    msg = message_from_bytes(msg_data[0][1])
    body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
    
    # Extract 6-digit code
    code_match = re.search(r'\b(\d{6})\b', body)
    if code_match:
        code = code_match.group(1)
        print(code)
        sys.exit(0)
    else:
        print("❌ No 6-digit code found in email", file=sys.stderr)
        sys.exit(1)
        
except Exception as e:
    print(f"❌ IMAP Error: {e}", file=sys.stderr)
    sys.exit(1)
finally:
    try:
        imap.close()
    except:
        pass
PYTHON_EOF
}

# Export for use
export -f extract_2fa_code extract_2fa_code_python
