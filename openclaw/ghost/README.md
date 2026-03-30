# Ghost CMS Automation Suite

Tools for automating a self-hosted Ghost CMS instance — from initial setup to ongoing
content publishing and admin operations.

## Quick Start

```bash
# 1. Copy and fill your credentials
cp .env.example .env
nano .env

# 2. Initial setup (first time — login with 2FA + configure site)
cd ghost-selfhost-admin
python3 scripts/ghost-setup.py --env /path/to/.env

# 3. Create Admin API key (via Playwright or Ghost UI)
node scripts/ghost-create-integration.js --env=/path/to/.env
#    Or manually: Settings > Integrations > Add Custom Integration
#    Copy id:secret → add to .env as GHOST_ADMIN_API_KEY=id:secret

# 4. Verify connection
node scripts/ghost-api-check.js

# 5. Manage your Ghost via API
node scripts/ghost-admin-client.js settings get
node scripts/ghost-admin-client.js settings update --json='{"title":"My Blog"}'
```

## Structure

```
ghost/
  .env.example                         ← credential template
  ghost-selfhost-admin/                ← admin & setup skill
    scripts/
      ghost-setup.py                   ← initial setup (2FA login + config)
      ghost-create-integration.js      ← create API key via Playwright
      ghost-admin-client.js            ← API client (read settings, CRUD, themes)
      ghost-api-check.js               ← health check
      ghost-playwright-admin.js        ← browser automation (UI-only ops)
      ghost-login.sh                   ← shell login
      ghost-post.sh                    ← shell post creation
    lib/
      ghost-api.js                     ← shared JWT/HTTP (used by all JS scripts)
      config.sh, email.sh, http.sh     ← shell libraries
    references/
      ghost-admin-api.md               ← API reference

  ghost-content-pipeline/              ← content publishing skill
    scripts/
      ghost-content-ops.js             ← content CRUD, search, bulk-tag, export
      submit-indexing.js               ← Google/IndexNow indexing
    references/
      post-template.md                 ← SEO-optimized post template
      improvement-rules.md             ← content improver rules
      cron-setup.md                    ← scheduling guide
```

## Two Skills

### ghost-selfhost-admin
Full Ghost administration: initial setup (2FA), settings, themes, images, navigation,
code injection, and Playwright for UI-only operations.

→ See `ghost-selfhost-admin/SKILL.md`

### ghost-content-pipeline
Content publishing automation: create/update posts, SEO optimization, bulk tagging,
export, search indexing (Google/IndexNow).

→ See `ghost-content-pipeline/SKILL.md`

## Authentication Methods

| Method | When | Scripts |
|--------|------|---------|
| Session (email+password+2FA) | Initial setup, before API key | `ghost-setup.py`, `ghost-login.sh` |
| JWT (Admin API key) | Ongoing admin & content ops | All `.js` scripts |
| Playwright (browser) | UI-only settings | `ghost-playwright-admin.js` |

## Requirements

- Python 3 + `requests`, `python-dotenv` (for initial setup)
- Node.js 18+ (for API scripts — zero npm dependencies)
- Playwright (optional, for UI-only operations: `npx playwright install chromium`)
