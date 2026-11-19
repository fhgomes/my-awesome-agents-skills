# Ghost SEO checklist with acceptance criteria

Run `scripts/seo_audit.py <site>` before and after. Each item lists how to prove it.

## A. What Ghost already does (verify, do not rebuild)

| Item | Proof |
|---|---|
| `sitemap.xml` + `sitemap-posts.xml` etc. | `curl -I https://site/sitemap.xml` -> 200 |
| `robots.txt` referencing the sitemap | `curl https://site/robots.txt` contains `Sitemap:` |
| Canonical, OG, Twitter Card, JSON-LD | present in `curl https://site/` head (from `{{ghost_head}}`) |
| Per-post meta title/description, OG/Twitter overrides | editor sidebar > Meta data / X card / Facebook card |
| `<html lang>` | theme's `default.hbs`; must match the content language |

If a theme replaced `{{ghost_head}}` with hand-written tags, restore `{{ghost_head}}`.

## B. What Google needs

| Item | Acceptance |
|---|---|
| Search Console verification | `<meta name="google-site-verification">` served on every page; `gsc.py verify` succeeded |
| Sitemap submitted | `gsc.py status` shows `errors=0`, `last_downloaded` set |
| No starter content indexed | Ghost "Coming soon" post is draft (404 on its URL) |
| Meta description on every published post | `seo_audit.py` shows no FAIL under posts |
| Site description in the content language | `meta name="description"` on the homepage reads naturally to the audience |

## C. Site identity (what shows in LinkedIn/Slack/WhatsApp previews)

| Item | Acceptance |
|---|---|
| `cover_image` is not `static.ghost.org/.../publication-cover.jpg` | og:image on homepage points to `/content/images/...` |
| `og_image` / `twitter_image` set to the same cover | both tags present |
| Icon set | `<link rel="icon">` present; Ghost resizes to 256 |
| Posts have a `feature_image` or fall back gracefully | posts without one show the site cover as og:image (acceptable) |

Cover spec: 1200x630, under 300 KB, text readable at 400 px wide, no critical content in the
outer 5% (LinkedIn crops). Icon: square, >= 60 px, ideally 512.

## D. Analytics (owner's decision)

| Option | Cookies | Setup |
|---|---|---|
| GA4 | yes | `ga4_measurement_id` field; consent banner + Consent Mode for EU/UK/Brazil (GDPR/LGPD); privacy policy lists GA4 |
| Ghost native (6.x) | no | Tinybird account + Ghost config; more infra |
| Umami / Plausible self-hosted | no | one more container; snippet via theme field or code injection |
| None | - | Search Console still gives queries and clicks |

## E. Bing and Meta (optional)

- Bing Webmaster Tools: import from Search Console with the same Google account; if it asks
  for a tag, `bing_site_verification` field.
- Meta domain verification: only needed to run Meta Ads or edit link previews on a Facebook
  Page. Code from business.facebook.com > Brand Safety > Domains into `facebook_domain_verification`.
- Meta Pixel: only for ads/retargeting. Heavier privacy footprint than GA4: sends the visitor's
  page URL and browser data to Meta even for people without a Facebook account. Consent
  required; do not enable by default.

## F. After every change

1. `curl -s https://site/ | grep <tag>` proves it is served.
2. `seo_audit.py` returns 0 FAIL.
3. Backup path and restore command written in the report.
4. Project notes updated: which fields are filled, where the Google key lives, analytics decision.
5. If any tracker is enabled: the privacy policy page names it and the consent mechanism was
   verified on the served HTML before the id was filled.
