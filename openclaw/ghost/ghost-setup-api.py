#!/usr/bin/env python3
"""
ghost-setup-api.py — Setup Ghost blog using API (no browser needed)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Login via /admin/session/ endpoint + customize Ghost

Usage:
    python3 ghost-setup-api.py --env /path/to/.env

Dependencies:
    pip install requests python-dotenv

Reference:
    https://ghost.org/docs/admin-api/#user-authentication
"""

import os
import sys
import argparse
import json
import time
import requests
from pathlib import Path
from dotenv import load_dotenv


class GhostAPI:
    def __init__(self, ghost_url: str, admin: str, password: str):
        self.ghost_url = ghost_url.rstrip('/')
        self.admin = admin
        self.password = password
        self.session = requests.Session()
        self.session_token = None
        self.needs_2fa = False
        
    def _make_request(self, method: str, endpoint: str, data: dict = None, headers: dict = None) -> dict:
        """Make API request"""
        url = f"{self.ghost_url}/ghost/api/admin{endpoint}"
        
        _headers = {
            "Content-Type": "application/json",
            "Accept-Version": "v5.0",
            "Origin": self.ghost_url,
        }
        if headers:
            _headers.update(headers)
        
        try:
            if method == "POST":
                resp = self.session.post(url, json=data, headers=_headers)
            elif method == "PUT":
                resp = self.session.put(url, json=data, headers=_headers)
            elif method == "GET":
                resp = self.session.get(url, headers=_headers)
            else:
                raise ValueError(f"Unknown method: {method}")
            
            # Debug
            if resp.status_code >= 400:
                print(f"[DEBUG] {method} {endpoint} -> {resp.status_code}")
                print(f"Response: {resp.text[:200]}")
            
            return resp
        except Exception as e:
            print(f"❌ Request error: {e}")
            return None
    
    def create_session(self) -> bool:
        """Create a session (login)"""
        print("[1/3] Creating session (login)...")
        
        payload = {
            "username": self.admin,
            "password": self.password,
        }
        
        resp = self._make_request("POST", "/session/", data=payload)
        
        if resp is None:
            print("❌ Session request failed")
            return False
        
        if resp.status_code == 201:
            print("   ✅ Session created (no 2FA needed)")
            return True
        
        elif resp.status_code == 403:
            error_msg = resp.json().get("errors", [{}])[0].get("message", "")
            if "verify" in error_msg.lower() or "2fa" in error_msg.lower():
                print("   ⚠️  2FA required - code sent to your email")
                self.needs_2fa = True
                return True
            else:
                print(f"❌ Error: {error_msg}")
                return False
        
        else:
            print(f"❌ Unexpected status: {resp.status_code}")
            print(f"   {resp.text[:200]}")
            return False
    
    def verify_2fa(self, code: str) -> bool:
        """Verify 2FA code"""
        if not self.needs_2fa:
            return True
        
        print(f"[2/3] Verifying 2FA code...")
        
        payload = {"token": code}
        resp = self._make_request("PUT", "/session/verify/", data=payload)
        
        if resp and resp.status_code == 200:
            print("   ✅ 2FA verified!")
            return True
        else:
            print(f"❌ 2FA verification failed: {resp.status_code if resp else 'error'}")
            return False
    
    def get_settings(self) -> dict:
        """Get site settings"""
        resp = self._make_request("GET", "/settings/")
        if resp and resp.status_code == 200:
            return resp.json().get("settings", {})
        return {}
    
    def update_settings(self, settings_dict: dict) -> bool:
        """Update site settings"""
        payload = {"settings": [settings_dict]}
        resp = self._make_request("PUT", "/settings/", data=payload)
        
        if resp and resp.status_code == 200:
            return True
        return False
    
    def is_logged_in(self) -> bool:
        """Check if session is valid"""
        try:
            resp = self._make_request("GET", "/users/me/")
            return resp and resp.status_code == 200
        except:
            return False


async def load_env(env_file: str = ".env") -> dict:
    """Load environment variables from .env file"""
    env_path = Path(env_file)
    if not env_path.exists():
        print(f"❌ Error: .env file not found: {env_file}")
        sys.exit(1)
    
    load_dotenv(env_path)
    
    config = {
        "GHOST_URL": os.getenv("GHOST_URL", "https://your-blog.com"),
        "GHOST_ADMIN": os.getenv("GHOST_ADMIN", os.getenv("GHOST_USER", "your@email.com")),
        "GHOST_PASSWORD": os.getenv("GHOST_PASSWORD", ""),
        "GHOST_GMAIL_USER": os.getenv("GHOST_GMAIL_USER", "your@email.com"),
    }
    
    # Validate required vars
    required = ["GHOST_URL", "GHOST_ADMIN", "GHOST_PASSWORD"]
    missing = [k for k in required if not config[k]]
    if missing:
        print(f"❌ Missing required variables: {', '.join(missing)}")
        sys.exit(1)
    
    return config


def main():
    parser = argparse.ArgumentParser(description="Setup Ghost blog via API")
    parser.add_argument("--env", default="/path/to/.env", help="Path to .env file")
    parser.add_argument("--title", help="Set site title")
    parser.add_argument("--description", help="Set site description")
    parser.add_argument("--show-2fa-input", action="store_true", help="Prompt for 2FA code interactively")
    
    args = parser.parse_args()
    
    # Load config (sync version)
    env_path = Path(args.env)
    if not env_path.exists():
        print(f"❌ Error: .env file not found: {args.env}")
        sys.exit(1)
    
    load_dotenv(env_path)
    
    config = {
        "GHOST_URL": os.getenv("GHOST_URL", ""),
        "GHOST_ADMIN": os.getenv("GHOST_ADMIN", os.getenv("GHOST_USER", "")),
        "GHOST_PASSWORD": os.getenv("GHOST_PASSWORD", ""),
    }
    
    required = ["GHOST_URL", "GHOST_ADMIN", "GHOST_PASSWORD"]
    missing = [k for k in required if not config[k]]
    if missing:
        print(f"❌ Missing required variables: {', '.join(missing)}")
        sys.exit(1)
    
    print("╔════════════════════════════════════════════════════════════════╗")
    print("║  🔐 Ghost Blog Setup (API)                                    ║")
    print("╚════════════════════════════════════════════════════════════════╝")
    print()
    
    # Create API client
    api = GhostAPI(config["GHOST_URL"], config["GHOST_ADMIN"], config["GHOST_PASSWORD"])
    
    # Login
    if not api.create_session():
        print("\n❌ Failed to create session")
        return 1
    
    # Handle 2FA if needed
    if api.needs_2fa:
        if args.show_2fa_input:
            code = input("Enter 2FA code from email: ").strip()
            if not api.verify_2fa(code):
                return 1
        else:
            print("\n   ⏳ 2FA required. Check your email for the code.")
            print("   Run again with --show-2fa-input to continue:")
            print(f"   python3 ghost-setup-api.py --env {args.env} --show-2fa-input")
            return 2  # Signal that 2FA is needed
    
    # Check if logged in
    if not api.is_logged_in():
        print("❌ Session verification failed")
        return 1
    
    print("[3/3] ✅ Authenticated successfully!")
    print()
    
    # Update settings if provided
    if args.title or args.description:
        print("[4/3] Updating settings...")
        
        settings = {}
        if args.title:
            settings["title"] = args.title
            print(f"   Setting title: {args.title}")
        if args.description:
            settings["description"] = args.description
            print(f"   Setting description: {args.description}")
        
        if api.update_settings(settings):
            print("   ✅ Settings updated!")
        else:
            print("   ❌ Failed to update settings")
    
    print()
    print("╔════════════════════════════════════════════════════════════════╗")
    print("║  ✅ Setup complete!                                           ║")
    print("╚════════════════════════════════════════════════════════════════╝")
    print()
    print("Next: Use Ghost admin UI to:")
    print("  - Upload logo")
    print("  - Set navigation menu")
    print("  - Add social links")
    print("  - Configure newsletter")
    print()
    print(f"Admin: {config['GHOST_URL']}/ghost/")
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
