---
name: ghost-selfhost-admin
description: >
  Full administration of a self-hosted Ghost CMS instance — initial setup (2FA login),
  ongoing config via Admin API (settings, themes, images, navigation, code injection,
  social links), and Playwright fallback for UI-only operations (portal, email config,
  labs, custom theme settings, user management).
metadata:
  openclaw:
    emoji: "👻"
    requires:
      env: ["GHOST_URL"]
      binaries: ["node", "python3"]
    primaryEnv: "GHOST_ADMIN_API_KEY"
    files: ["scripts/*", "lib/*"]
---

# Ghost Self-Host Admin

Full administration skill for self-hosted Ghost CMS. Covers initial setup through
ongoing configuration, with three operational phases.

## Three Phases of Ghost Admin

### Phase 1: Initial Setup (before API key exists)

First-time login uses email + password + 2FA. These scripts handle the bootstrap
before you have an Admin API key.

```bash
# Automated setup: login with 2FA + configure site
python3 scripts/ghost-setup.py --env /path/to/.env

# Shell alternative: login only (saves session for ghost-post.sh)
./scripts/ghost-login.sh /path/to/.env
```

**After first login:** create an Admin API key. You can do this via Playwright:

```bash
node scripts/ghost-create-integration.js --env=/path/to/.env --name="My Automation"
# Outputs: GHOST_ADMIN_API_KEY=id:secret → add to .env
```

Or manually: Ghost Admin UI → Settings → Integrations → Add Custom Integration → copy `id:secret`.

### Phase 2: Admin API (preferred — with API key)

Once you have an API key, use JWT-based scripts for everything the API supports.
Faster, no 2FA needed, fully scriptable.

```bash
# Health check
node scripts/ghost-api-check.js

# Settings (title, description, timezone, language, navigation, social, code injection, accent color)
node scripts/ghost-admin-client.js settings get
node scripts/ghost-admin-client.js settings update --json='{"title":"My Blog","description":"...", "navigation":"[...]"}'

# Images
node scripts/ghost-admin-client.js images upload --file=/path/to/logo.png

# Themes
node scripts/ghost-admin-client.js themes list
node scripts/ghost-admin-client.js themes upload --file=/path/to/theme.zip
node scripts/ghost-admin-client.js themes activate --name=casper

# Generic CRUD (posts, pages, tags, members, newsletters, tiers, offers, webhooks)
node scripts/ghost-admin-client.js posts list --limit=5 --status=published
node scripts/ghost-admin-client.js members list --limit=10
```

**What the API key (JWT) covers:**

| Operation | Endpoint | API Key? |
|-----------|----------|----------|
| Read all settings | `GET /settings/` | ✅ read-only |
| **Write settings** (title, nav, social, etc.) | `PUT /settings/` | ❌ **session auth only** |
| Themes (upload, activate, list) | `/themes/` | ✅ |
| Posts, pages, tags | Full CRUD | ✅ |
| Members, newsletters, tiers, offers | Full CRUD | ✅ |
| Webhooks | Full CRUD | ✅ |
| Images | `POST /images/upload/` | ✅ |
| Users | `GET /users/` | ✅ read-only |

> **Important:** Ghost 5.x does NOT allow writing settings via Integration API keys.
> `PUT /settings/` returns 501 "Not Implemented" with JWT auth.
> To change settings programmatically, use **Phase 1 scripts** (session-based login with 2FA)
> or **Playwright**.

### Phase 3: Playwright (UI-only operations)

For things with no stable API endpoint:

```bash
node scripts/ghost-playwright-admin.js login
node scripts/ghost-playwright-admin.js screenshot --page=dashboard
node scripts/ghost-playwright-admin.js code-injection --header="..." --footer="..."
```

**Operations that require Playwright or session auth:**
- **Write settings** (title, description, navigation, social, code injection, accent color)
- Create custom integrations (generate API keys)
- Invite/create/delete staff users
- Portal configuration (signup form, plans, button style)
- Email/Mailgun/SMTP configuration
- Labs feature toggles
- Custom theme settings (theme-specific design options)
- Routes.yaml editor

## Environment Variables

### Required
```bash
GHOST_URL=https://your-ghost.com
```

### For API operations (Phase 2)
```bash
GHOST_ADMIN_API_KEY=id:secret    # Settings > Integrations > Custom Integration
```

### For Playwright operations (Phase 3)
```bash
GHOST_ADMIN_EMAIL=admin@your-ghost.com
GHOST_ADMIN_PASSWORD=your-password
```

### For initial setup (Phase 1)
```bash
GHOST_ADMIN=admin@your-ghost.com
GHOST_PASSWORD=your-password
GHOST_GMAIL_USER=your@gmail.com
GHOST_GMAIL_PASSWORD=xxxx xxxx xxxx xxxx   # Gmail app password for 2FA extraction
```

## File Structure

```
ghost-selfhost-admin/
  SKILL.md                              ← this file
  package.json
  scripts/
    ghost-setup.py                      ← Phase 1: initial setup (2FA login + config)
    ghost-login.sh                      ← Phase 1: shell login alternative
    ghost-post.sh                       ← Phase 1: post creation via shell session
    ghost-create-integration.js         ← Phase 1→2: create API key via Playwright
    ghost-admin-client.js               ← Phase 2: API client (read settings, themes, CRUD)
    ghost-api-check.js                  ← Phase 2: health check
    ghost-playwright-admin.js           ← Phase 3: browser automation
  lib/
    ghost-api.js                        ← Shared: JWT, HTTP, upload, CLI parsing
    config.sh                           ← Shell: env loading
    email.sh                            ← Shell: IMAP 2FA extraction
    http.sh                             ← Shell: HTTP helpers
  references/
    ghost-admin-api.md                  ← API reference
```

## Rules

1. **API first, Playwright second** — always prefer API when available
2. **Backup before destructive changes** — export content before bulk operations
3. **Never expose API keys** — use environment variables, never hardcode
4. **Validate theme before activating** — use gscan locally if possible
5. **Respect rate limits** — avoid burst requests
