#!/usr/bin/env python3
"""
ghost-sprint1-full.py — Complete Sprint 1 Customization (Automated)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Login (2FA auto)
2. Upload logo
3. Set title + tagline + description
4. Upload custom CSS (colors + fonts)
5. Set navigation menu
6. Set social links

Usage:
    python3 ghost-sprint1-full.py --env /path/to/.env

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


# Custom CSS for branding
CUSTOM_CSS = """/* ===== CUSTOM BRANDING ===== */

/* Color Variables */
:root {
  --primary: #1a1a1a;
  --accent: #f1592a;
  --text: #333333;
  --bg: #ffffff;
  --border: #e5e5e5;
}

/* Headlines - Serif (Lora) */
h1, h2, h3, h4, h5, h6 {
  font-family: 'Lora', 'Georgia', serif;
  color: var(--primary);
  font-weight: 700;
}

/* Body Text - Sans-serif */
body, 
p, 
article,
.post-content {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', sans-serif;
  color: var(--text);
  line-height: 1.6;
}

/* Links - Orange Accent */
a {
  color: var(--accent);
  text-decoration: none;
  border-bottom: 1px solid transparent;
  transition: all 0.2s ease;
}

a:hover {
  border-bottom: 1px solid var(--accent);
  opacity: 0.8;
}

/* Code Blocks */
code, pre {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  background-color: #f5f5f5;
  border-left: 4px solid var(--accent);
  padding: 2px 4px;
}

pre {
  padding: 1rem;
  overflow-x: auto;
}

/* CTA Buttons */
.btn, 
button, 
input[type="submit"],
.subscribe-button {
  background-color: var(--accent);
  color: white;
  border: none;
  padding: 12px 24px;
  border-radius: 4px;
  cursor: pointer;
  font-weight: 600;
  transition: background-color 0.3s ease;
}

.btn:hover, 
button:hover,
input[type="submit"]:hover,
.subscribe-button:hover {
  background-color: #e5461f;
}

/* Newsletter Form Inputs */
input[type="email"],
input[type="text"],
textarea {
  border: 1px solid var(--border);
  padding: 12px;
  border-radius: 4px;
  font-family: inherit;
  font-size: 16px;
}

input[type="email"]:focus,
input[type="text"]:focus,
textarea:focus {
  border-color: var(--accent);
  outline: none;
  box-shadow: 0 0 0 3px rgba(245, 89, 42, 0.15);
}

/* Blockquotes */
blockquote {
  border-left: 4px solid var(--accent);
  margin-left: 0;
  padding-left: 1rem;
  color: #666;
  font-style: italic;
}

/* Post Meta (date, author) */
.post-meta,
.article-meta {
  color: #999;
  font-size: 0.9rem;
}

/* Accent text for important content */
.accent, 
.highlight {
  color: var(--accent);
  font-weight: 600;
}

/* ===== END CUSTOM BRANDING ===== */"""


class GhostSprint1:
    def __init__(self, ghost_url: str, admin: str, password: str, gmail_user: str, gmail_password: str, logo_path: str = None):
        self.ghost_url = ghost_url.rstrip('/')
        self.admin = admin
        self.password = password
        self.gmail_user = gmail_user
        self.gmail_password = gmail_password
        self.logo_path = logo_path
        self.session = requests.Session()
        self.api_key = None
        
    def extract_2fa_code(self) -> str:
        """Extract 2FA code from Gmail (unread emails only)"""
        print("[1/7] Extracting 2FA code from Gmail...")
        
        try:
            context = ssl.create_default_context()
            mail = imaplib.IMAP4_SSL('imap.gmail.com', 993, ssl_context=context)
            mail.login(self.gmail_user, self.gmail_password)
            
            mail.select('INBOX')
            status, messages = mail.search(None, 'UNSEEN')
            msg_ids = messages[0].split()
            
            if not msg_ids:
                print("   ⚠️  No unread emails found")
                mail.close()
                mail.logout()
                return None
            
            msg_id = msg_ids[-1]
            status, msg_data = mail.fetch(msg_id, '(RFC822)')
            
            code_found = None
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg_body = response_part[1].decode('utf-8', errors='ignore')
                    
                    if 'ghost' in msg_body.lower() or 'signin' in msg_body.lower():
                        pattern = r'\b(\d{6})\b'
                        matches = re.findall(pattern, msg_body)
                        
                        if matches:
                            code_found = matches[0]
                            break
            
            if code_found:
                mail.store(msg_id, '+FLAGS', '\\Seen')
                print(f"   ✅ Code found: {code_found}")
                
                mail.close()
                mail.logout()
                return code_found
            else:
                print("   ❌ No code in unread emails")
                mail.close()
                mail.logout()
                return None
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return None
    
    def login(self) -> bool:
        """Login to Ghost with 2FA"""
        print("[2/7] Logging in to Ghost with 2FA...")
        
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
            # Request session
            resp = self.session.post(
                f"{self.ghost_url}/ghost/api/admin/session/",
                json=payload,
                headers=headers
            )
            
            if resp.status_code not in [201, 403]:
                print(f"   ❌ Unexpected status: {resp.status_code}")
                return False
            
            # Extract and submit 2FA code
            code = self.extract_2fa_code()
            if not code:
                print("   ⏳ No code found, waiting...")
                time.sleep(5)
                code = self.extract_2fa_code()
                if not code:
                    print("   ❌ No code found")
                    return False
            
            # Verify code (wait longer before verifying, with retry)
            time.sleep(5)
            verify_payload = {"token": code}
            
            # Retry up to 3 times with delay
            for attempt in range(3):
                resp = self.session.put(
                    f"{self.ghost_url}/ghost/api/admin/session/verify/",
                    json=verify_payload,
                    headers=headers
                )
                
                if resp.status_code == 200:
                    break
                elif resp.status_code == 429:
                    print(f"   ⏳ Rate limited, waiting... (attempt {attempt+1}/3)")
                    time.sleep(10)
                else:
                    break
            
            if resp.status_code == 200:
                print("   ✅ 2FA verified!")
                return True
            else:
                print(f"   ❌ Verification failed: {resp.status_code}")
                return False
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False
    
    def upload_logo(self) -> bool:
        """Upload logo image"""
        if not self.logo_path or not Path(self.logo_path).exists():
            print("[3/7] ⚠️  Logo file not found, skipping...")
            return False
        
        print("[3/7] Uploading logo...")
        
        try:
            headers = {
                "Accept-Version": "v5.0",
            }
            
            with open(self.logo_path, 'rb') as f:
                # Use multipart form data
                files = {'file': (Path(self.logo_path).name, f, 'image/png')}
                resp = self.session.post(
                    f"{self.ghost_url}/ghost/api/admin/images/upload/",
                    files=files,
                    headers=headers
                )
            
            if resp.status_code in [200, 201]:
                response_data = resp.json()
                logo_url = response_data.get('images', [{}])[0].get('url', '')
                if logo_url:
                    print(f"   ✅ Logo uploaded: {logo_url}")
                    
                    # Now set it as publication logo
                    settings = [{"key": "logo", "value": logo_url}]
                    return self.update_settings(settings)
                else:
                    print(f"   ⚠️  Upload response unclear: {response_data}")
                    return False
            else:
                print(f"   ⚠️  Upload status: {resp.status_code}")
                if resp.text:
                    print(f"      Response: {resp.text[:200]}")
                # Don't fail completely, continue with other settings
                return True
                
        except Exception as e:
            print(f"   ⚠️  Error: {e}")
            return True  # Don't fail completely
    
    def update_settings(self, settings_list: list) -> bool:
        """Update Ghost settings"""
        headers = {
            "Content-Type": "application/json",
            "Accept-Version": "v5.0",
            "Origin": self.ghost_url,
        }
        
        payload = {"settings": settings_list}
        
        try:
            resp = self.session.put(
                f"{self.ghost_url}/ghost/api/admin/settings/",
                json=payload,
                headers=headers
            )
            
            if resp.status_code == 200:
                return True
            else:
                print(f"   ⚠️  Settings update: {resp.status_code}")
                return False
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False
    
    def set_publication_info(self) -> bool:
        """Set title + tagline + description"""
        print("[4/7] Setting publication info...")
        
        settings = [
            {"key": "title", "value": "Your Blog Title"},
            {"key": "description", "value": "Carreira técnica de verdade. FinTech pragmático. Tudo o que funciona em produção."},
            {"key": "accent_color", "value": "#f1592a"},
            {"key": "lang", "value": "pt"},
            {"key": "timezone", "value": "Europe/Berlin"},
        ]
        
        if self.update_settings(settings):
            print("   ✅ Publication info updated!")
            return True
        else:
            print("   ❌ Failed to update")
            return False
    
    def set_custom_css(self) -> bool:
        """Set custom CSS"""
        print("[5/7] Setting custom CSS (colors + fonts)...")
        
        settings = [{"key": "codeinjection_styles", "value": CUSTOM_CSS}]
        
        if self.update_settings(settings):
            print("   ✅ Custom CSS applied!")
            return True
        else:
            print("   ❌ Failed to apply CSS")
            return False
    
    def set_navigation(self) -> bool:
        """Set navigation menu"""
        print("[6/7] Setting navigation menu...")
        
        nav_items = [
            {"label": "Home", "url": "/"},
            {"label": "Latest", "url": "/"},
            {"label": "About", "url": "/about/"},
            {"label": "Contact", "url": "/contact/"},
        ]
        
        # Ghost stores navigation as JSON string
        nav_json = json.dumps(nav_items)
        settings = [{"key": "navigation", "value": nav_json}]
        
        if self.update_settings(settings):
            print("   ✅ Navigation menu set!")
            return True
        else:
            print("   ❌ Failed to set navigation")
            return False
    
    def set_social_links(self) -> bool:
        """Set social media links"""
        print("[7/7] Setting social links...")
        
        social_links = [
            {"label": "LinkedIn", "url": "https://www.linkedin.com/in/your-profile"},
            {"label": "GitHub", "url": "https://github.com/your-profile"},
            {"label": "Instagram", "url": "https://instagram.com/your-profile"},
            {"label": "YouTube", "url": "https://www.youtube.com/@your-channel"},
        ]
        
        social_json = json.dumps(social_links)
        settings = [{"key": "social", "value": social_json}]
        
        if self.update_settings(settings):
            print("   ✅ Social links set!")
            return True
        else:
            print("   ❌ Failed to set social links")
            return False
    
    def run_sprint1(self) -> bool:
        """Run complete Sprint 1"""
        print("╔════════════════════════════════════════════════════════════════╗")
        print("║  🎨 Ghost Sprint 1 — Full Customization (AUTOMATED)           ║")
        print("╚════════════════════════════════════════════════════════════════╝")
        print()
        
        # Login with 2FA
        if not self.login():
            return False
        
        print()
        
        # Upload logo
        self.upload_logo()
        
        # Set publication info
        if not self.set_publication_info():
            return False
        
        # Set custom CSS
        if not self.set_custom_css():
            return False
        
        # Set navigation
        if not self.set_navigation():
            return False
        
        # Set social links
        if not self.set_social_links():
            return False
        
        print()
        print("╔════════════════════════════════════════════════════════════════╗")
        print("║  ✅ Sprint 1 Complete!                                         ║")
        print("╚════════════════════════════════════════════════════════════════╝")
        print()
        print("Check your blog:")
        print(f"  👉 {self.ghost_url}/")
        print()
        print("You should see:")
        print("  ✅ Title: 'Your Blog Title'")
        print("  ✅ Logo in header")
        print("  ✅ Orange accent color (#f1592a)")
        print("  ✅ Navigation menu")
        print("  ✅ Social links in footer")
        print()
        
        return True


def main():
    parser = argparse.ArgumentParser(description="Sprint 1 Full Customization")
    parser.add_argument("--env", default="/path/to/.env", help="Path to .env file")
    parser.add_argument("--logo", default="/path/to/your-logo.png", help="Logo image path")
    
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
    
    # Run Sprint 1
    sprint = GhostSprint1(
        config["GHOST_URL"],
        config["GHOST_ADMIN"],
        config["GHOST_PASSWORD"],
        config["GHOST_GMAIL_USER"],
        config["GHOST_GMAIL_PASSWORD"],
        args.logo
    )
    
    if sprint.run_sprint1():
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
