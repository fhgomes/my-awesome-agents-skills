#!/usr/bin/env node
/**
 * ghost-create-integration.js
 * Creates a Custom Integration in Ghost Admin via Playwright and extracts the API key.
 * Handles 2FA automatically via Gmail IMAP.
 *
 * Usage:
 *   GHOST_URL=https://your-ghost.com \
 *   GHOST_ADMIN=admin@your-ghost.com \
 *   GHOST_PASSWORD=your-password \
 *   GHOST_GMAIL_USER=your@gmail.com \
 *   GHOST_GMAIL_PASSWORD="xxxx xxxx xxxx xxxx" \
 *   node ghost-create-integration.js [--name="Integration Name"]
 *
 * Or with .env file:
 *   node ghost-create-integration.js --env=/path/to/.env
 *
 * Requires: npx playwright install chromium (first time)
 */

const { execSync } = require('child_process');
const path = require('path');

// Parse CLI args
const args = process.argv.slice(2);
const opts = {};
for (const arg of args) {
  if (arg.startsWith('--')) {
    const [key, ...v] = arg.slice(2).split('=');
    opts[key] = v.join('=') || true;
  }
}

// Load .env if provided
const envFile = opts.env || process.env.GHOST_ENV_FILE || '';
if (envFile) {
  try {
    const fs = require('fs');
    const content = fs.readFileSync(envFile, 'utf-8');
    for (const line of content.split('\n')) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith('#')) continue;
      const eqIdx = trimmed.indexOf('=');
      if (eqIdx > 0) {
        const key = trimmed.slice(0, eqIdx).trim();
        let val = trimmed.slice(eqIdx + 1).trim();
        if ((val.startsWith('"') && val.endsWith('"')) || (val.startsWith("'") && val.endsWith("'"))) {
          val = val.slice(1, -1);
        }
        process.env[key] = val;
      }
    }
  } catch (e) {
    console.error(`⚠️ Could not load .env from ${envFile}: ${e.message}`);
  }
}

const GHOST_URL = process.env.GHOST_URL;
const GHOST_ADMIN = process.env.GHOST_ADMIN || process.env.GHOST_USER;
const GHOST_PASSWORD = process.env.GHOST_PASSWORD;
const GHOST_GMAIL_USER = process.env.GHOST_GMAIL_USER;
const GHOST_GMAIL_PASSWORD = process.env.GHOST_GMAIL_PASSWORD;
const INTEGRATION_NAME = opts.name || 'OpenClaw Automation';

if (!GHOST_URL || !GHOST_ADMIN || !GHOST_PASSWORD) {
  console.error('❌ Required: GHOST_URL, GHOST_ADMIN, GHOST_PASSWORD');
  console.error('   Set via environment variables or --env=/path/to/.env');
  process.exit(1);
}

const ADMIN_URL = `${GHOST_URL.replace(/\/$/, '')}/ghost`;

function extract2FACode() {
  if (!GHOST_GMAIL_USER || !GHOST_GMAIL_PASSWORD) {
    console.log('   ⚠️ No Gmail credentials — cannot extract 2FA code automatically');
    return '';
  }
  try {
    return execSync(`python3 -c "
import imaplib, ssl, re
ctx = ssl.create_default_context()
mail = imaplib.IMAP4_SSL('imap.gmail.com', 993, ssl_context=ctx)
mail.login('${GHOST_GMAIL_USER}', '${GHOST_GMAIL_PASSWORD}')
mail.select('INBOX')
_, msgs = mail.search(None, 'UNSEEN')
ids = msgs[0].split()
if ids:
    _, data = mail.fetch(ids[-1], '(RFC822)')
    body = data[0][1].decode('utf-8', errors='ignore')
    codes = [c for c in __import__('re').findall(r'\\\\b(\\\\d{6})\\\\b', body)]
    if codes:
        print(codes[0], end='')
        mail.store(ids[-1], '+FLAGS', '\\\\\\\\Seen')
mail.close()
mail.logout()
"`, { encoding: 'utf-8' }).trim();
  } catch (e) {
    return '';
  }
}

(async () => {
  let pw;
  try {
    pw = require('playwright');
  } catch {
    console.log('📦 Installing Playwright...');
    execSync('npx playwright install chromium', { stdio: 'inherit' });
    pw = require('playwright');
  }

  const browser = await pw.chromium.launch({ headless: true });
  const page = await browser.newPage();

  try {
    // 1. Login
    console.log('[1/5] Logging in...');
    await page.goto(`${ADMIN_URL}/#/signin`, { waitUntil: 'networkidle' });
    await page.fill('input[name="identification"]', GHOST_ADMIN);
    await page.fill('input[name="password"]', GHOST_PASSWORD);
    await page.click('button[type="submit"], button:has-text("Sign in")');
    await page.waitForTimeout(5000);

    // 2. Handle 2FA if needed
    if (page.url().includes('signin')) {
      console.log('[2/5] Handling 2FA...');
      await page.waitForTimeout(5000);
      let code = extract2FACode();
      if (!code) {
        console.log('   Waiting longer for email...');
        await page.waitForTimeout(8000);
        code = extract2FACode();
      }
      if (!code) {
        console.error('   ❌ No 2FA code found. Check Gmail credentials.');
        await page.screenshot({ path: '/tmp/ghost-2fa-failed.png' });
        await browser.close();
        process.exit(1);
      }
      console.log(`   ✅ Code: ${code}`);

      const inputs = page.locator('#signin input[type="text"], .gh-signin input, input[name="token"]');
      if (await inputs.count() > 0) {
        await inputs.first().fill(code);
        await page.click('button[type="submit"], button:has-text("Verify"), button:has-text("Sign in")');
      }
      await page.waitForTimeout(5000);
    } else {
      console.log('[2/5] No 2FA needed');
    }

    // 3. Verify login
    if (page.url().includes('signin')) {
      console.error('[3/5] ❌ Login failed');
      await page.screenshot({ path: '/tmp/ghost-login-failed.png' });
      await browser.close();
      process.exit(1);
    }
    console.log('[3/5] ✅ Logged in');

    // 4. Create integration
    console.log('[4/5] Creating integration...');
    await page.goto(`${ADMIN_URL}/#/settings/integrations`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);

    const addSelectors = [
      'button:has-text("Add custom integration")',
      'a:has-text("Add custom integration")',
      '[data-test-link="add-custom-integration"]',
    ];

    let clicked = false;
    for (const sel of addSelectors) {
      const el = page.locator(sel);
      if (await el.count() > 0) {
        await el.first().click();
        await page.waitForTimeout(2000);
        clicked = true;
        break;
      }
    }

    if (!clicked) {
      await page.goto(`${ADMIN_URL}/#/settings/integrations/new`, { waitUntil: 'networkidle' });
      await page.waitForTimeout(2000);
    }

    // Fill name in modal (use force:true to bypass modal backdrop overlay)
    await page.waitForTimeout(1000);
    const nameInput = page.locator('#modal-backdrop input[type="text"], .modal input[type="text"], input[placeholder="Custom integration"]');
    if (await nameInput.count() > 0) {
      await nameInput.first().fill('');
      await nameInput.first().fill(INTEGRATION_NAME);

      const addBtn = page.locator('#modal-backdrop button:has-text("Add"), .modal button:has-text("Add")');
      if (await addBtn.count() > 0) {
        await addBtn.first().click({ force: true });
        await page.waitForTimeout(5000);
      }
    } else {
      console.error('   ❌ Could not find integration name input');
      await page.screenshot({ path: '/tmp/ghost-no-modal.png' });
      await browser.close();
      process.exit(1);
    }

    // 5. Extract API key
    console.log('[5/5] Extracting API key...');
    const bodyText = await page.locator('body').innerText();
    const keyMatch = bodyText.match(/[a-f0-9]{24}:[a-f0-9]{64}/);

    if (keyMatch) {
      console.log(`\n   🔑 ADMIN API KEY: ${keyMatch[0]}`);
      console.log(`\n   Add to your .env:`);
      console.log(`   GHOST_ADMIN_API_KEY=${keyMatch[0]}`);
    } else {
      console.log('   ⚠️ API key not found in page text. Check screenshot.');
      await page.screenshot({ path: '/tmp/ghost-integration-page.png' });

      // Dump all input values as fallback
      const allInputs = page.locator('input');
      const count = await allInputs.count();
      for (let i = 0; i < count; i++) {
        const val = await allInputs.nth(i).inputValue().catch(() => '');
        if (val && val.length > 20) console.log(`   input[${i}]: ${val}`);
      }
    }

  } catch (err) {
    console.error('💥 Error:', err.message);
    await page.screenshot({ path: '/tmp/ghost-error.png' }).catch(() => {});
    process.exit(1);
  } finally {
    await browser.close();
  }
})();
