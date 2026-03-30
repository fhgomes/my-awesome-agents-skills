# Ghost Blog Automation — Production Ready ✅

**Status:** ✅ Fully tested and working  
**Date:** 2026-03-30  
**Owner:** Captain (CelebDev)  

---

## 🎯 What Was Built

A complete, **zero-intervention** Ghost blog automation suite:

1. **ghost-setup-complete.py** (⭐ USE THIS ONE)
   - Login to Ghost with 2FA (extracts code from Gmail)
   - Updates site title + description
   - Session-based authentication
   - Error handling + retry logic

2. Supporting scripts (for reference/future):
   - `ghost-login.sh` — Shell version (uses IMAP)
   - `ghost-post.sh` — Create posts (reuses session)
   - `ghost-setup-api.py` — Manual 2FA entry version
   - Libraries: `config.sh`, `email.sh`, `http.sh`

---

## 🚀 How to Use

### One-command setup:

```bash
cd /path/to/your/runbook
python3 ghost-setup-complete.py --env /path/to/.env
```

**What happens:**
1. Reads `.env` file (Ghost + Gmail credentials)
2. Creates session on Ghost
3. Automatically extracts 2FA code from Gmail inbox
4. Verifies code with Ghost
5. Updates site title + description
6. Done ✅

**Time:** ~10 seconds

---

## 📋 Configuration

### .env file: `/path/to/.env`

```bash
# Database (unchanged)
GHOST_DB_PASSWORD=your_db_password
MYSQL_ROOT_PASSWORD=your_mysql_root_password

# Ghost Admin
GHOST_URL=https://your-blog.com
GHOST_ADMIN=your@email.com
GHOST_USER=your@email.com
GHOST_PASSWORD=your_ghost_password

# Gmail (for 2FA code extraction)
GHOST_GMAIL_USER=your@gmail.com
GHOST_GMAIL_PASSWORD=xxxx xxxx xxxx xxxx
```

---

## 🔐 How the 2FA Works

**Old (Manual):**
1. Run script → Ghost sends code to email
2. You check email manually
3. You run script again with code
4. Script logs in

**New (Automatic):**
1. Run script
2. Script does everything:
   - Creates session request (Ghost sends code)
   - Connects to Gmail IMAP
   - Extracts 6-digit code from inbox
   - Verifies code with Ghost
   - Logs in automatically
3. Done ✅

**Why this works:**
- We have Gmail app password (in .env)
- We have Ghost password (in .env)
- IMAP access to email is automatic
- No manual intervention needed

---

## 🛠️ Maintenance & Monitoring

### Daily usage:
```bash
# Just run it
python3 ghost-setup-complete.py --env /path/to/.env
```

### If password changes:
```bash
# Update .env
nano /path/to/.env

# Update GHOST_PASSWORD = new password
# Update GHOST_GMAIL_PASSWORD = new app password (from Google)

# Run script again
python3 ghost-setup-complete.py --env /path/to/.env
```

### If Gmail app password expires:
1. Go to: https://myaccount.google.com/apppasswords
2. Generate new app password (16 chars)
3. Update `.env` → `GHOST_GMAIL_PASSWORD=`
4. Run script again

### If code extraction fails:
The script will:
1. Wait 5 seconds
2. Try again
3. If still no code, exit gracefully

Check email manually if needed:
```bash
python3 << 'EOF'
import imaplib, ssl, re, os
from dotenv import load_dotenv

load_dotenv('/path/to/.env')
mail = imaplib.IMAP4_SSL('imap.gmail.com', 993)
mail.login(os.getenv('GHOST_GMAIL_USER'), os.getenv('GHOST_GMAIL_PASSWORD'))
mail.select('INBOX')
status, msgs = mail.search(None, 'ALL')
msg_id = msgs[0].split()[-1]
status, data = mail.fetch(msg_id, 'RFC822')
body = data[0][1].decode('utf-8', errors='ignore')
code = re.findall(r'\b(\d{6})\b', body)[0]
print(f"Code: {code}")
EOF
```

---

## 📊 What Each File Does

| File | Purpose | Status |
|------|---------|--------|
| `ghost-setup-complete.py` | Full automation (login + 2FA + settings) | ✅ Production |
| `ghost-login.sh` | Shell-based login | ✅ Works |
| `ghost-post.sh` | Create posts | ✅ Ready |
| `ghost-setup-api.py` | Manual 2FA entry | ✅ Works |
| `ghost-setup.py` | Playwright (headless mode) | ⚠️ Needs X11 |
| `lib/config.sh` | Env loading | ✅ Shared |
| `lib/email.sh` | IMAP functions | ✅ Shared |
| `lib/http.sh` | HTTP/Ghost API | ✅ Shared |

---

## 🚦 Common Scenarios

### Scenario 1: First-time setup
```bash
python3 ghost-setup-complete.py --env /path/to/.env
# → Extracts code, logs in, updates title/description ✅
```

### Scenario 2: Update blog title later
```bash
# Edit ghost-setup-complete.py, change "Your Blog Title" to new title
# OR create wrapper script:

cat > /tmp/update-title.py << 'EOF'
import sys
sys.path.insert(0, '/path/to/your/runbook')
from ghost_setup_complete import GhostSetup
setup = GhostSetup(...)
setup.login()
setup.update_settings([{"key": "title", "value": "New Title"}])
EOF

python3 /tmp/update-title.py
```

### Scenario 3: Create a post
```bash
cd /path/to/your/runbook
./ghost-login.sh /path/to/.env
./ghost-post.sh --title "My Post" --body "Content" --publish
```

### Scenario 4: Cron job (daily check)
```bash
# Add to crontab:
0 6 * * * cd /path/to/your/runbook && python3 ghost-setup-complete.py --env /path/to/.env >> /tmp/ghost-setup.log 2>&1
```

---

## 🔄 Next Steps (Optional Expansions)

### Create pages via API
```bash
# Would use same login mechanism
# Example: Create About page
curl -X POST https://your-blog.com/ghost/api/admin/pages/ \
  -H "Authorization: Ghost $TOKEN" \
  -d '{"pages":[{"title":"About","html":"..."}]}'
```

### Upload images
```bash
# Requires multipart form-data + session
# Would follow same pattern
```

### Schedule posts
```bash
# Create post with "scheduled" status
# Requires timezone configuration
```

### Newsletter integration
```bash
# Ghost has native newsletter feature
# Can be configured via admin UI
```

---

## 🐛 Troubleshooting

### "No 6-digit code found"
- Check Gmail inbox manually
- Verify `GHOST_GMAIL_PASSWORD` is correct (app password, not main password)
- Try: `gmail_user=$(cat /path/to/.env | grep GHOST_GMAIL) && echo "$gmail_user"`

### "403 Verification failed"
- Code might be wrong or expired (valid for ~10 min)
- Try running script again (Ghost sends new code)

### "Connection refused"
- Ghost container might be down
- Check: `docker ps | grep ghost`
- Restart: `docker restart ghost-blog`

### ".env not found"
- Make sure `.env` exists at `/path/to/.env`
- Check: `ls -la /path/to/.env`

---

## 📝 Code Structure

```python
GhostSetup class:
├── extract_2fa_code()      # IMAP → Gmail → regex → code
├── login()                 # POST /session + PUT /session/verify
├── is_logged_in()          # GET /users/me (verify)
└── update_settings()       # PUT /settings

main():
├── load_env()              # Read .env
├── validate()              # Check required vars
└── run_setup()             # Execute GhostSetup
```

---

## 🎓 Learning & Future

This automation demonstrates:
- ✅ Session-based authentication flows
- ✅ 2FA code extraction via IMAP
- ✅ REST API integration
- ✅ Environment-based configuration
- ✅ Error handling + retries
- ✅ Modular function design

**Can be extended for:**
- Other CMS platforms (WordPress, Strapi, etc.)
- Other email providers (Outlook, Zoho, etc.)
- Automated content publishing workflows
- Monitoring + alerting

---

## 📞 Support

**Location:** `/path/to/your/runbook/`

**Main script:** `ghost-setup-complete.py`

**Test command:**
```bash
python3 ghost-setup-complete.py --env /path/to/.env
```

**Expected output:** ✅ All 4 steps complete

---

**Status:** ✅ PRODUCTION READY

**Created:** 2026-03-30  
**Tested:** YES (full run successful)  
**Maintenance:** Minimal (only if credentials change)

---

Happy blogging! 🚀
