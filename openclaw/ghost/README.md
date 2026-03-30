# Ghost Blog Automation Suite

Complete automation toolkit for Ghost CMS management via CLI.

**Status:** ✅ Production Ready  
**Version:** 1.0.0  
**Author:** Captain (CelebDev)  
**Date:** 2026-03-30

---

## 🚀 Quick Start

### Prerequisites

```bash
pip install requests python-dotenv
```

### Setup

1. Create `.env` file with your Ghost credentials:

```bash
cat > .env << 'EOF'
GHOST_URL=https://your-blog.com
GHOST_ADMIN=your@email.com
GHOST_USER=your@email.com
GHOST_PASSWORD=your_ghost_password
GHOST_GMAIL_USER=your@gmail.com
GHOST_GMAIL_PASSWORD=your_16char_app_password
EOF
```

2. Run a script:

```bash
python3 ghost-setup-complete.py --env .env
```

---

## 📋 Scripts

### 1. **ghost-sprint1-full.py** ⭐ MAIN
Complete blog customization in one command:
- Login with 2FA (extracts code from Gmail automatically)
- Upload logo
- Apply custom CSS (colors + fonts)
- Set navigation menu
- Set social links

```bash
python3 ghost-sprint1-full.py --env .env --logo /path/to/logo.png
```

### 2. **ghost-setup-complete.py**
Automatic setup (login + core settings):
```bash
python3 ghost-setup-complete.py --env .env
```

### 3. **ghost-setup-api.py**
Manual 2FA code entry (useful if automatic extraction fails):
```bash
python3 ghost-setup-api.py --env .env --show-2fa-input
```

### 4. **ghost-login.sh**
Shell-based login with IMAP:
```bash
./ghost-login.sh /path/to/.env
```

### 5. **ghost-post.sh**
Create and publish posts:
```bash
./ghost-post.sh --title "My Post" --body "Content here" --publish
```

---

## 📚 Documentation

See **PRODUCTION_READY.md** for:
- Detailed usage
- Troubleshooting
- Cron job setup
- Maintenance guide
- 2FA workflow explanation

---

## 🔐 Security Notes

✅ **Safe:**
- All credentials loaded from `.env` (never hardcoded)
- 2FA codes extracted automatically via IMAP
- Session tokens managed securely
- No passwords logged to console

⚠️ **IMPORTANT:**
- **Never commit `.env` file to git**
- **Never share `.env` file**
- Treat `.env` as highly sensitive
- Rotate credentials regularly (especially Gmail app password)

---

## 🛠️ For Developers

### Code Structure

```
ghost-setup-complete.py
├── GhostSetup class
│   ├── extract_2fa_code()      ← IMAP → Gmail → regex
│   ├── login()                 ← POST /session + PUT /session/verify
│   ├── update_settings()       ← PUT /settings
│   └── is_logged_in()          ← GET /users/me
│
└── main()
    ├── load_env()
    ├── validate()
    └── run setup
```

### Extending

To add new features (e.g., upload images):

```python
class GhostSetup:
    def upload_image(self, image_path):
        """Custom method"""
        with open(image_path, 'rb') as f:
            files = {'file': f}
            resp = self.session.post(
                f"{self.ghost_url}/ghost/api/admin/images/upload/",
                files=files,
                headers={"Accept-Version": "v5.0"}
            )
        return resp.status_code == 200
```

---

## 🆘 Troubleshooting

### "429 Too Many Requests"
- Ghost rate-limiting API calls
- Solution: Wait 30+ seconds before running script again
- Or: Use manual login via browser

### "No 6-digit code found"
- Gmail app password incorrect
- Check: `GHOST_GMAIL_PASSWORD` is 16 char app password (not main password)
- Solution: Generate new app password at https://myaccount.google.com/apppasswords

### ".env not found"
- Create it in current directory or use `--env /path/to/.env`
- Template included in this README

---

## 📞 Support

For issues, check:
1. PRODUCTION_READY.md (detailed docs)
2. Script help: `python3 ghost-setup-complete.py --help`
3. Ghost API docs: https://ghost.org/docs/admin-api/

---

## 📄 License

Part of CelebDev program. Use for your own Ghost blogs.

---

**Last Updated:** 2026-03-30  
**Status:** ✅ Production Ready
