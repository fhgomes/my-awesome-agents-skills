# google-seo-data

Search Console and GA4 from the terminal, through a service account. Verify a site, submit
its sitemap, read top queries/pages and index coverage, read traffic by page/source/country.

```bash
pip install -r scripts/requirements.txt
export GOOGLE_SA_JSON=~/.config/google-seo/sa.json
export SEO_SITE=https://www.example.com/
python3 scripts/gsc.py token && python3 scripts/gsc.py verify && python3 scripts/gsc.py add && python3 scripts/gsc.py sitemap
python3 scripts/gsc.py top 28
python3 scripts/ga4.py props && GA4_PROPERTY=<id> python3 scripts/ga4.py report 28
```

- `SKILL.md`: workflow, reporting format, guardrails
- `references/setup-google-cloud.md`: the one-time browser setup (project, APIs, key, GA4 access)
- `references/reading-the-data.md`: how to turn rows into a decision, weekly template

The key file stays outside the repo with `chmod 600`; the scripts refuse a world-readable key. Scopes are
per command (reads never get a write scope). `owner` needs `--yes` and a real email.
Pairs with `ghost-seo-install`, which puts the verification tag and analytics id on a Ghost site.
