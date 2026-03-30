#!/usr/bin/env python3
"""
ghost-setup.py — Setup Ghost blog with Playwright
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Login to Ghost admin + customize (logo, menu, social links)

Usage:
    python3 ghost-setup.py --env /path/to/.env --action logo
    python3 ghost-setup.py --env /path/to/.env --action all

Actions:
    logo       — Upload logo image
    menu       — Set navigation menu
    social     — Set social links
    all        — Do everything

Dependencies:
    pip install playwright python-dotenv pillow
    playwright install chromium

Output:
    Screenshots saved to: /tmp/ghost-setup-*.png
"""

import os
import sys
import argparse
import time
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from playwright.async_api import async_playwright, expect


async def load_env(env_file: str = ".env") -> dict:
    """Load environment variables from .env file"""
    env_path = Path(env_file)
    if not env_path.exists():
        print(f"❌ Error: .env file not found: {env_file}")
        sys.exit(1)
    
    load_dotenv(env_path)
    
    config = {
        "GHOST_URL": os.getenv("GHOST_URL", ""),
        "GHOST_ADMIN": os.getenv("GHOST_ADMIN", os.getenv("GHOST_USER", "")),
        "GHOST_PASSWORD": os.getenv("GHOST_PASSWORD", ""),
        "GHOST_GMAIL_USER": os.getenv("GHOST_GMAIL_USER", ""),
        "GHOST_GMAIL_PASSWORD": os.getenv("GHOST_GMAIL_PASSWORD", ""),
    }
    
    # Validate required vars
    required = ["GHOST_URL", "GHOST_ADMIN", "GHOST_PASSWORD"]
    missing = [k for k in required if not config[k]]
    if missing:
        print(f"❌ Missing required variables: {', '.join(missing)}")
        sys.exit(1)
    
    return config


async def login_to_ghost(page, config: dict) -> bool:
    """Login to Ghost admin and handle 2FA"""
    print("[1/4] Navigating to Ghost admin...")
    admin_url = f"{config['GHOST_URL']}/ghost/#/signin"
    await page.goto(admin_url)
    
    print("[2/4] Entering credentials...")
    # Enter email
    await page.fill('input[type="email"]', config["GHOST_ADMIN"])
    await page.fill('input[type="password"]', config["GHOST_PASSWORD"])
    
    # Click login button
    await page.click('button:has-text("Sign in")')
    
    # Wait for either 2FA or success
    await asyncio.sleep(2)
    
    # Check if we get 2FA page
    try:
        await page.wait_for_selector('input[placeholder*="code"]', timeout=5000)
        print("[3/4] 2FA required - check your email for code...")
        
        # Wait for user to enter code
        code_input = await page.query_selector('input[placeholder*="code"]')
        if code_input:
            print("   ⏳ Waiting for you to enter 2FA code manually...")
            print("   (Will wait 60 seconds)")
            try:
                await page.wait_for_url("**/signin-success/**", timeout=60000)
                print("   ✓ 2FA verified!")
            except:
                print("   ❌ 2FA timeout or error")
                return False
    except:
        # No 2FA, check if we're logged in
        pass
    
    # Wait for dashboard
    await asyncio.sleep(2)
    try:
        await page.wait_for_selector('a[href*="/editor/"]', timeout=10000)
        print("[4/4] ✅ Logged in successfully!")
        return True
    except:
        print("❌ Login failed - could not reach dashboard")
        return False


async def upload_logo(page, config: dict) -> bool:
    """Upload logo to Ghost"""
    print("\n[LOGO] Uploading logo image...")
    
    # Navigate to settings
    await page.goto(f"{config['GHOST_URL']}/ghost/#/settings/general")
    await asyncio.sleep(2)
    
    # Find and upload logo
    try:
        # Look for logo upload button
        await page.wait_for_selector('input[type="file"]', timeout=5000)
        
        # Use Instagram avatar if it exists
        logo_path = Path.home() / ".openclaw" / "assets" / "logo.png"
        if not logo_path.exists():
            print(f"   ⚠️  Logo not found at {logo_path}")
            print("   Using placeholder: will upload after")
            return False
        
        # Upload file
        file_input = await page.query_selector('input[type="file"]')
        await file_input.set_input_files(str(logo_path))
        
        await asyncio.sleep(2)
        
        # Save settings
        await page.click('button:has-text("Save")')
        await asyncio.sleep(2)
        
        print("   ✅ Logo uploaded!")
        return True
    except Exception as e:
        print(f"   ⚠️  Logo upload error: {e}")
        return False


async def set_navigation_menu(page, config: dict) -> bool:
    """Set navigation menu in Ghost"""
    print("\n[MENU] Setting navigation menu...")
    
    await page.goto(f"{config['GHOST_URL']}/ghost/#/settings/general")
    await asyncio.sleep(2)
    
    try:
        # Navigate to navigation section
        # This typically requires scrolling and clicking on Navigation field
        
        menu_items = [
            {"label": "Home", "url": "/"},
            {"label": "Latest", "url": "/"},
            {"label": "About", "url": "/about/"},
            {"label": "Contact", "url": "/contact/"},
        ]
        
        # Find navigation input fields
        # (This part depends on Ghost's exact structure)
        # For now, we'll note that this needs manual verification
        
        print("   ⚠️  Navigation menu setup requires manual UI interaction")
        print("   Menu should include:")
        for item in menu_items:
            print(f"      - {item['label']}: {item['url']}")
        
        return False  # Return False to indicate manual step needed
        
    except Exception as e:
        print(f"   ⚠️  Menu error: {e}")
        return False


async def set_social_links(page, config: dict) -> bool:
    """Set social media links in Ghost"""
    print("\n[SOCIAL] Setting social media links...")
    
    await page.goto(f"{config['GHOST_URL']}/ghost/#/settings/general")
    await asyncio.sleep(2)
    
    try:
        social_links = {
            "LinkedIn": "https://www.linkedin.com/in/your-profile",
            "GitHub": "https://github.com/your-profile",
            "Instagram": "https://instagram.com/your-profile",
            "YouTube": "https://www.youtube.com/@your-channel",
        }
        
        # Find social links section
        # This typically requires scrolling and filling form fields
        
        print("   ⚠️  Social links setup requires manual UI interaction")
        print("   Add these links:")
        for platform, url in social_links.items():
            print(f"      - {platform}: {url}")
        
        return False  # Return False to indicate manual step needed
        
    except Exception as e:
        print(f"   ⚠️  Social links error: {e}")
        return False


async def take_screenshot(page, name: str) -> None:
    """Take a screenshot for debugging"""
    screenshot_path = f"/tmp/ghost-setup-{name}-{int(time.time())}.png"
    await page.screenshot(path=screenshot_path)
    print(f"   📸 Screenshot: {screenshot_path}")


async def main():
    parser = argparse.ArgumentParser(description="Setup Ghost blog with Playwright")
    parser.add_argument("--env", default="/path/to/.env", help="Path to .env file")
    parser.add_argument("--action", choices=["logo", "menu", "social", "all"], default="all", help="What to setup")
    parser.add_argument("--headless", action="store_true", default=False, help="Run in headless mode")
    parser.add_argument("--debug", action="store_true", default=False, help="Enable debug output")
    
    args = parser.parse_args()
    
    # Load config
    config = await load_env(args.env)
    
    print("╔════════════════════════════════════════════════════════════════╗")
    print("║  🎨 Ghost Blog Setup with Playwright                          ║")
    print("╚════════════════════════════════════════════════════════════════╝")
    print()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=args.headless)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # Login first
            if not await login_to_ghost(page, config):
                print("\n❌ Failed to login to Ghost")
                await take_screenshot(page, "login-failed")
                return 1
            
            # Do requested actions
            if args.action in ["all", "logo"]:
                await upload_logo(page, config)
            
            if args.action in ["all", "menu"]:
                await set_navigation_menu(page, config)
            
            if args.action in ["all", "social"]:
                await set_social_links(page, config)
            
            print("\n╔════════════════════════════════════════════════════════════════╗")
            print("║  ✅ Setup complete!                                           ║")
            print("╚════════════════════════════════════════════════════════════════╝")
            print()
            print("Next steps:")
            print("  1. Check your browser window (may still be open)")
            print("  2. Verify the changes in Ghost admin")
            print("  3. Some settings may need manual adjustment")
            
            # Keep browser open for verification
            if not args.headless:
                print("\n   Press Enter to close browser...")
                input()
            
            return 0
        
        finally:
            await context.close()
            await browser.close()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
