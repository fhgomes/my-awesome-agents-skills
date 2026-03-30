#!/usr/bin/env python3
"""
ghost-setup-complete.py — Full Ghost setup automation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Login (2FA auto) + customize Ghost blog

Usage:
    python3 ghost-setup-complete.py --env /path/to/.env

Dependencies:
    pip install requests python-dotenv
"""

import os
import sys
import argparse
import json
import time
import requests
import imaplib
import ssl
import re
from pathlib import Path
from dotenv import load_dotenv


class GhostSetup:
    def __init__(self, ghost_url: str, admin: str, password: str, gmail_user: str, gmail_password: str):
        self.ghost_url = ghost_url.rstrip('/')
        self.admin = admin
        self.password = password
        self.gmail_user = gmail_user
        self.gmail_password = gmail_password
        self.session = requests.Session()
        
    def extract_2fa_code(self) -> str:
        """Extract 2FA code from Gmail (unread emails only)"""
        print("[1/4] Extracting 2FA code from Gmail...")
        
        try:
            context = ssl.create_default_context()
            mail = imaplib.IMAP4_SSL('imap.gmail.com', 993, ssl_context=context)
            mail.login(self.gmail_user, self.gmail_password)
            
            mail.select('INBOX')
            
            # Search for UNREAD emails only
            status, messages = mail.search(None, 'UNSEEN')
            msg_ids = messages[0].split()
            
            if not msg_ids:
                print("   ⚠️  No unread emails found")
                mail.close()
                mail.logout()
                return None
            
            print(f"   Found {len(msg_ids)} unread email(s)")
            
            # Get most recent unread email (last in list)
            msg_id = msg_ids[-1]
            status, msg_data = mail.fetch(msg_id, '(RFC822)')
            
            code_found = None
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg_body = response_part[1].decode('utf-8', errors='ignore')
                    
                    # Check if it's a Ghost email
                    if 'ghost' in msg_body.lower() or 'signin' in msg_body.lower():
                        # Extract 6-digit code
                        pattern = r'\b(\d{6})\b'
                        matches = re.findall(pattern, msg_body)
                        
                        if matches:
                            code_found = matches[0]
                            break
            
            if code_found:
                # Mark email as read
                mail.store(msg_id, '+FLAGS', '\\Seen')
                print(f"   ✅ Code found: {code_found}")
                print(f"   ✅ Email marked as read")
                
                mail.close()
                mail.logout()
                return code_found
            else:
                print("   ❌ No 2FA code found in most recent unread email")
                mail.close()
                mail.logout()
                return None
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return None
    
    def login(self) -> bool:
        """Login to Ghost with 2FA"""
        print("[2/4] Creating session and verifying 2FA...")
        
        # Step 1: Request session (triggers 2FA email)
        headers = {
            "Content-Type": "application/json",
            "Accept-Version": "v5.0",
            "Origin": self.ghost_url,
        }
        
        payload = {
            "username": self.admin,
            "password": self.password,
        }
        
        try:
            resp = self.session.post(
                f"{self.ghost_url}/ghost/api/admin/session/",
                json=payload,
                headers=headers
            )
            
            if resp.status_code not in [201, 403]:
                print(f"   ❌ Unexpected status: {resp.status_code}")
                print(f"      {resp.text[:200]}")
                return False
            
            # Step 2: Extract and submit 2FA code
            code = self.extract_2fa_code()
            if not code:
                print("   ⏳ No code found, waiting and retrying...")
                time.sleep(5)
                code = self.extract_2fa_code()
                if not code:
                    print("   ❌ Still no code, giving up")
                    return False
            
            # Step 3: Verify code
            verify_payload = {"token": code}
            resp = self.session.put(
                f"{self.ghost_url}/ghost/api/admin/session/verify/",
                json=verify_payload,
                headers=headers
            )
            
            if resp.status_code == 200:
                print("   ✅ 2FA verified!")
                return True
            else:
                print(f"   ❌ Verification failed: {resp.status_code}")
                return False
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False
    
    def is_logged_in(self) -> bool:
        """Verify logged in"""
        try:
            headers = {"Accept-Version": "v5.0"}
            resp = self.session.get(
                f"{self.ghost_url}/ghost/api/admin/users/me/",
                headers=headers
            )
            return resp.status_code == 200
        except:
            return False
    
    def update_settings(self, settings_dict: dict) -> bool:
        """Update Ghost settings"""
        print("[3/4] Updating Ghost settings...")
        
        headers = {
            "Content-Type": "application/json",
            "Accept-Version": "v5.0",
            "Origin": self.ghost_url,
        }
        
        payload = {"settings": settings_dict}
        
        try:
            resp = self.session.put(
                f"{self.ghost_url}/ghost/api/admin/settings/",
                json=payload,
                headers=headers
            )
            
            if resp.status_code == 200:
                print("   ✅ Settings updated!")
                return True
            else:
                print(f"   ⚠️  Settings update: {resp.status_code}")
                if resp.status_code != 200:
                    print(f"      {resp.text[:200]}")
                return False
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False
    
    def run_setup(self) -> bool:
        """Run full setup"""
        print("╔════════════════════════════════════════════════════════════════╗")
        print("║  🎨 Ghost Blog Full Setup                                     ║")
        print("╚════════════════════════════════════════════════════════════════╝")
        print()
        
        # Login with 2FA
        if not self.login():
            return False
        
        # Verify logged in
        if not self.is_logged_in():
            print("❌ Verification failed - not logged in")
            return False
        
        print("   ✅ Logged in successfully!")
        print()
        
        # Update settings
        settings = [
            {
                "key": "title",
                "value": "Your Blog Title"
            },
            {
                "key": "description",
                "value": "Carreira técnica de verdade. FinTech pragmático. Tudo o que funciona em produção."
            },
            {
                "key": "lang",
                "value": "pt"
            },
            {
                "key": "timezone",
                "value": "Europe/Berlin"
            }
        ]
        
        self.update_settings(settings)
        
        print("[4/4] Setup complete!")
        print()
        print("╔════════════════════════════════════════════════════════════════╗")
        print("║  ✅ Ghost is now configured!                                  ║")
        print("╚════════════════════════════════════════════════════════════════╝")
        print()
        print("Next manual steps (via Ghost admin UI):")
        print("  1. Upload logo: Settings → General → Publication Logo")
        print("  2. Set menu: Settings → General → Navigation")
        print("  3. Set social: Settings → General → Social accounts")
        print()
        print(f"Admin URL: {self.ghost_url}/ghost/")
        print()
        
        return True


def main():
    parser = argparse.ArgumentParser(description="Full Ghost blog setup with 2FA")
    parser.add_argument("--env", default="/path/to/.env", help="Path to .env file")
    
    args = parser.parse_args()
    
    # Load env
    env_path = Path(args.env)
    if not env_path.exists():
        print(f"❌ Error: .env file not found: {args.env}")
        sys.exit(1)
    
    load_dotenv(env_path)
    
    config = {
        "GHOST_URL": os.getenv("GHOST_URL", ""),
        "GHOST_ADMIN": os.getenv("GHOST_ADMIN", os.getenv("GHOST_USER", "")),
        "GHOST_PASSWORD": os.getenv("GHOST_PASSWORD", ""),
        "GHOST_GMAIL_USER": os.getenv("GHOST_GMAIL_USER", ""),
        "GHOST_GMAIL_PASSWORD": os.getenv("GHOST_GMAIL_PASSWORD", ""),
    }
    
    # Validate
    required = ["GHOST_URL", "GHOST_ADMIN", "GHOST_PASSWORD", "GHOST_GMAIL_USER", "GHOST_GMAIL_PASSWORD"]
    missing = [k for k in required if not config[k]]
    if missing:
        print(f"❌ Missing: {', '.join(missing)}")
        sys.exit(1)
    
    # Run setup
    setup = GhostSetup(
        config["GHOST_URL"],
        config["GHOST_ADMIN"],
        config["GHOST_PASSWORD"],
        config["GHOST_GMAIL_USER"],
        config["GHOST_GMAIL_PASSWORD"]
    )
    
    if setup.run_setup():
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
