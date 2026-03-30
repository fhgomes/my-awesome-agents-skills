# Claude Scripts Reference Library — v2

**Location:** `/home/unando/ghost/references-claude-scripts-v2/`  
**Date:** 2026-03-30  
**Status:** ✅ Reference & Learning Material

---

## 📚 What's Inside

### 1. **ghost-content-pipeline/**
OpenClaw skill for Ghost content publishing workflow automation.

**Files:**
- `SKILL.md` — Complete skill documentation
- `scripts/ghost-content-ops.js` — Content operations
- `scripts/submit-indexing.js` — Search indexing
- `references/post-template.md` — Post structure template
- `references/improvement-rules.md` — Quality rules
- `references/cron-setup.md` — Scheduling guide
- `package.json` — Dependencies

**Use Case:** Automated content pipeline for Ghost blogs

---

### 2. **ghost-selfhost-admin/**
OpenClaw skill for Ghost admin API + browser automation.

**Files:**
- `SKILL.md` — Complete skill documentation
- `scripts/ghost-admin-client.js` — Admin API client
- `scripts/ghost-api-check.js` — API health check
- `scripts/ghost-playwright-admin.js` — Browser automation
- `references/ghost-admin-api.md` — API reference
- `package.json` — Dependencies

**Use Case:** Self-hosted Ghost admin automation

---

## 🎯 Quick Reference

### For Content Publishing:
→ Read: `ghost-content-pipeline/SKILL.md`
→ Check: `ghost-content-pipeline/references/post-template.md`

### For Admin Automation:
→ Read: `ghost-selfhost-admin/SKILL.md`
→ Check: `ghost-selfhost-admin/references/ghost-admin-api.md`

### For Scheduling:
→ Read: `ghost-content-pipeline/references/cron-setup.md`

---

## 📖 Documentation Structure

Each skill folder has:
- `SKILL.md` ← Start here
- `scripts/` ← Implementation code
- `references/` ← Supporting docs
- `package.json` ← Dependencies

---

## 🔗 Related Files

**Your custom scripts:**
- `/home/unando/.openclaw/workspace/runbook/ghost-*.py` — Python automation suite
- `/home/unando/.openclaw/workspace/runbook/ghost-*.sh` — Shell scripts
- `/home/unando/.openclaw/workspace/runbook/PRODUCTION_READY.md` — Full docs

**GitHub:**
- https://github.com/fhgomes/my-awesome-agents-skills → `openclaw/ghost/`

---

## 💡 How to Use

1. **Read** the SKILL.md in each folder to understand the feature
2. **Review** the references/ docs for detailed patterns
3. **Check** the scripts/ code for implementation
4. **Adapt** to your Ghost instance URL + credentials

---

## ⚠️ Important

These are **reference implementations** from Claude Code sessions. Adapt them to:
- Your Ghost URL
- Your authentication method
- Your specific use case

Do NOT commit any `.env` files or credentials!

---

**Status:** ✅ Educational Reference Material

Use these as templates and learning material for building your own Ghost automation workflows.
