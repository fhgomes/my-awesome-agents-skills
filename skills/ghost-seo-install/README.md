# ghost-seo-install

Ghost has no SEO plugins and does not need one; it needs configuration. This skill turns the
theme into the "plugin": five custom settings (Google/Bing/Meta verification, GA4, Meta Pixel)
rendered in `<head>`, plus scripts to audit, fix site identity, and write settings that the
Admin API refuses.

```bash
set -a; . ~/.config/ghost-seo/env; set +a   # GHOST_ADMIN_API_KEY, GHOST_HOST, GHOST_URL in a chmod 600 file, never on the command line
python3 scripts/seo_audit.py https://blog.example.com        # 1. read-only audit
# 2. merge scripts/theme-seo-fields.json into package.json, paste scripts/theme-seo-head.hbs before {{ghost_head}}, deploy safely
scripts/ghost-setting.sh custom ga4_measurement_id G-XXXXXXXXXX   # MySQL password read inside the container
python3 scripts/og_cover.py --brand "..." --author "..." --line1 "..." --domain blog.example.com --out ./out
```

- `SKILL.md`: the six-step workflow and guardrails (backup, prove on served HTML, approval before visible changes)
- `references/ghost-seo-checklist.md`: acceptance criteria per item
- `references/ghost-admin-api-recipes.md`: JWT, proxy headers, what tokens cannot write, MySQL fallbacks

Pairs with `google-seo-data` for verification, sitemap submission and reading the numbers.
