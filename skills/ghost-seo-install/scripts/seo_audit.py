#!/usr/bin/env python3
"""SEO audit of a Ghost site: what Google sees + what the Admin API says is missing.

Needs GHOST_ADMIN_API_KEY (+ GHOST_URL / GHOST_HOST, see ghost_admin.py) and the public URL:

  python3 seo_audit.py https://blog.example.com

Read-only. Prints a checklist with PASS / WARN / FAIL lines and exits 1 if anything FAILs.
"""
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ghost_admin as g  # noqa: E402

PLACEHOLDER_COVER = 'static.ghost.org'


def clean(s, n=120):
    """Untrusted text (site HTML, API rows) -> one printable line. Control chars could forge [PASS]/[FAIL] lines."""
    return re.sub(r'[\x00-\x1f\x7f]+', ' ', str(s))[:n]

status = {'FAIL': 0, 'WARN': 0}


def say(level, msg):
    if level in status:
        status[level] += 1
    print(f'[{level}] {msg}')


def fetch(url):
    r = subprocess.run(['curl', '-sL', '-o', '-', '-w', '\n%{http_code}', '--', url], capture_output=True, text=True)
    body, _, code = r.stdout.rpartition('\n')
    return code.strip(), body


def tag(html, pattern):
    m = re.search(pattern, html, re.I)
    return m.group(1) if m else None


def audit_public(site):
    code, home = fetch(site + '/')
    say('PASS' if code == '200' else 'FAIL', f'homepage HTTP {code}')
    for path in ('/sitemap.xml', '/robots.txt'):
        c, body = fetch(site + path)
        say('PASS' if c == '200' else 'FAIL', f'{path} HTTP {c}')
        if path == '/robots.txt' and c == '200' and 'Sitemap:' not in body:
            say('WARN', 'robots.txt does not reference the sitemap')
    desc = tag(home, r'<meta name="description" content="([^"]*)"')
    say('PASS' if desc else 'FAIL', f'meta description: {clean(desc, 90) if desc else "missing"}')
    if desc and len(desc) > 160:
        say('WARN', f'meta description is {len(desc)} chars (>160 gets truncated)')
    og = tag(home, r'<meta property="og:image" content="([^"]*)"')
    if not og:
        say('FAIL', 'og:image missing')
    elif PLACEHOLDER_COVER in og:
        say('FAIL', 'og:image is the Ghost placeholder cover (set Publication cover in Settings > Design)')
    else:
        say('PASS', f'og:image {clean(og)}')
    icon = tag(home, r'<link rel="icon" href="([^"]*)"')
    say('PASS' if icon else 'WARN', f'favicon: {clean(icon) if icon else "missing (Settings > Design > Publication icon)"}')
    say('PASS' if 'application/ld+json' in home else 'FAIL', 'JSON-LD structured data present')
    say('PASS' if 'rel="canonical"' in home else 'FAIL', 'canonical link present')
    for name, pat in (('google-site-verification', r'name="google-site-verification"'),
                      ('GA4 tag', r'googletagmanager\.com/gtag/js\?id=G-'),
                      ('Bing verification', r'name="msvalidate\.01"')):
        say('PASS' if re.search(pat, home) else 'WARN', f'{name}: {"present" if re.search(pat, home) else "absent"}')
    lang = tag(home, r'<html[^>]*lang="([^"]*)"')
    say('PASS' if lang else 'WARN', f'html lang: {clean(lang, 10) if lang else "missing"}')


def audit_admin():
    r = g.call('GET', '/ghost/api/admin/posts/?filter=status:published&limit=all'
                      '&fields=slug,title,custom_excerpt,meta_description,feature_image,published_at')
    if 'posts' not in r:
        say('WARN', 'Admin API not reachable (check GHOST_ADMIN_API_KEY / GHOST_HOST): ' + str(r)[:120])
        return
    posts = r['posts']
    print(f'\n-- {len(posts)} published posts')
    for p in posts:
        p = {k: (clean(v, 80) if isinstance(v, str) else v) for k, v in p.items()}
        misses = [k for k in ('meta_description', 'custom_excerpt', 'feature_image') if not p[k]]
        if p['slug'] == 'coming-soon' or p['title'].lower().startswith('coming soon'):
            say('WARN', f"{p['slug']}: default Ghost starter post is still published (unpublish it)")
        elif 'meta_description' in misses and 'custom_excerpt' in misses:
            say('FAIL', f"{p['slug']}: no meta description and no excerpt (Google picks a random sentence)")
        elif misses:
            say('WARN', f"{p['slug']}: missing {', '.join(misses)}")
        else:
            say('PASS', p['slug'])
    s = g.call('GET', '/ghost/api/admin/settings/')
    if 'settings' in s:
        kv = {x['key']: x['value'] for x in s['settings']}
        if kv.get('cover_image') and PLACEHOLDER_COVER in kv['cover_image']:
            say('FAIL', 'settings.cover_image is the Ghost placeholder')
        if not kv.get('icon'):
            say('WARN', 'settings.icon (favicon) empty')
        if not kv.get('meta_description'):
            say('WARN', 'settings.meta_description empty (homepage falls back to site description)')
        print(f"    site description: {clean(kv.get('description'))!r}")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    site = sys.argv[1].rstrip('/')
    if not re.fullmatch(r'https?://[A-Za-z0-9.-]+(:[0-9]+)?', site):
        sys.exit('site must be like https://blog.example.com (scheme + host only)')
    print(f'== public: {site}')
    audit_public(site)
    print('\n== admin API')
    audit_admin()
    print(f"\n{status['FAIL']} FAIL, {status['WARN']} WARN")
    sys.exit(1 if status['FAIL'] else 0)
