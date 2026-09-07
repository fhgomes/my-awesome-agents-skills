#!/usr/bin/env python3
"""Google Search Console through a service account: verify, submit sitemap, read data.

Environment (all optional except the key file):
  GOOGLE_SA_JSON   path to the service-account key   (default: ~/.config/google-seo/sa.json)
  SEO_SITE         property URL, trailing slash        (default: https://example.com/)
                   or a domain property: sc-domain:example.com

Commands:
  token            print the verification code for the <meta name="google-site-verification"> tag
                   (URL-prefix property) or the TXT record (domain property)
  verify           ask Google to verify the property (the tag/TXT must already be live)
  add              add the property to Search Console (verify alone does not list it)
  owner EMAIL --yes  add a Google account as owner (only an email the user typed); without --yes it only previews
  sitemap [PATH]   submit a sitemap (default: <site>/sitemap.xml) and print status
  status           sitemaps known to Google, with errors/warnings
  top [DAYS]       top queries and pages, last DAYS days (default 28)
  inspect URL      index coverage for one URL
"""
import json
import os
import re
import sys
from datetime import date, timedelta

from google.oauth2 import service_account
from googleapiclient.discovery import build

SITE = os.environ.get('SEO_SITE') or sys.exit('SEO_SITE not set (https://www.example.com/ or sc-domain:example.com); refusing to guess a property')
SA_JSON = os.path.expanduser(os.environ.get('GOOGLE_SA_JSON', '~/.config/google-seo/sa.json'))
# least privilege per command: reads never get a write scope, verify never gets owner management
SCOPE = {
    'read':   ['https://www.googleapis.com/auth/webmasters.readonly'],
    'write':  ['https://www.googleapis.com/auth/webmasters'],
    'verify': ['https://www.googleapis.com/auth/siteverification.verify_only'],
    'owner':  ['https://www.googleapis.com/auth/siteverification'],
}
IS_DOMAIN = SITE.startswith('sc-domain:')
DOMAIN = SITE.split(':', 1)[1] if IS_DOMAIN else None


def creds(kind):
    if not os.path.exists(SA_JSON):
        sys.exit(f'service-account key not found at {SA_JSON} (set GOOGLE_SA_JSON)')
    mode = os.stat(SA_JSON).st_mode & 0o777
    if mode & 0o077 and os.environ.get('GOOGLE_SA_JSON_INSECURE') != '1':
        sys.exit(f'{SA_JSON} is readable by others (mode {mode:o}); run chmod 600 (or GOOGLE_SA_JSON_INSECURE=1 to override)')
    return service_account.Credentials.from_service_account_file(SA_JSON, scopes=SCOPE[kind])


def gsc(kind='read'):
    return build('searchconsole', 'v1', credentials=creds(kind), cache_discovery=False)


def sv(kind='verify'):
    return build('siteVerification', 'v1', credentials=creds(kind), cache_discovery=False)


def clean(s, n=120):
    """Untrusted text (site HTML, API rows) -> one printable line. Control chars could forge output lines."""
    return re.sub(r'[\x00-\x1f\x7f]+', ' ', str(s))[:n]


def _sv_site():
    if IS_DOMAIN:
        return {'type': 'INET_DOMAIN', 'identifier': DOMAIN}
    return {'type': 'SITE', 'identifier': SITE}


def _sv_method():
    return 'DNS_TXT' if IS_DOMAIN else 'META'


def cmd_token():
    r = sv().webResource().getToken(body={'site': _sv_site(), 'verificationMethod': _sv_method()}).execute()
    tok = r['token']
    if IS_DOMAIN:
        print(f'add this TXT record at the apex of {DOMAIN} (name "@"), then run: verify')
        print(tok)
    else:
        content = tok.split('content="')[1].split('"')[0]
        print('put this in <meta name="google-site-verification" content="..."> (theme field or code injection), then run: verify')
        print(content)


def cmd_verify():
    r = sv().webResource().insert(verificationMethod=_sv_method(), body={'site': _sv_site()}).execute()
    print('verified:', r.get('id'), '| owners:', len(r.get('owners', [])), '(emails not printed)')


def cmd_add():
    gsc('write').sites().add(siteUrl=SITE).execute()
    for e in gsc('write').sites().list().execute().get('siteEntry', []):
        print(e['siteUrl'], e['permissionLevel'])


def cmd_owner(email, confirm=None):
    if not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', email):
        sys.exit(f'not an email: {email!r}')
    if confirm != '--yes':
        sys.exit(f'about to add {email} as OWNER of {SITE}. Re-run: owner {email} --yes (only if the user typed this exact email)')
    api = sv('owner').webResource()
    rid = DOMAIN if IS_DOMAIN else SITE  # the client library URL-encodes the id itself
    cur = api.get(id=rid).execute()
    owners = sorted(set(cur.get('owners', [])) | {email})
    r = api.update(id=rid, body={'site': cur['site'], 'owners': owners}).execute()
    print('owners now:', len(r.get('owners', [])), '(the one you named is included)')


def cmd_sitemap(path=None):
    if path is None:
        if IS_DOMAIN:
            sys.exit('domain property: pass the full sitemap URL, e.g. sitemap https://www.example.com/sitemap.xml')
        path = SITE + 'sitemap.xml'
    gsc('write').sitemaps().submit(siteUrl=SITE, feedpath=path).execute()
    print('submitted:', path)
    cmd_status()


def cmd_status():
    r = gsc().sitemaps().list(siteUrl=SITE).execute()
    for s in r.get('sitemap', []):
        print(f"{s['path']}  last_downloaded={s.get('lastDownloaded', '-')}  "
              f"errors={s.get('errors', 0)} warnings={s.get('warnings', 0)} pending={s.get('isPending')}")
        for c in s.get('contents', []):
            print(f"   {c['type']}: submitted={c.get('submitted')} indexed={c.get('indexed', '?')}")
    if not r.get('sitemap'):
        print('no sitemap submitted yet')


def cmd_top(days='28'):
    end = date.today() - timedelta(days=2)  # Search Console data lags ~2 days
    start = end - timedelta(days=int(days))
    for dim in ('query', 'page'):
        r = gsc().searchanalytics().query(siteUrl=SITE, body={
            'startDate': start.isoformat(), 'endDate': end.isoformat(),
            'dimensions': [dim], 'rowLimit': 15,
        }).execute()
        print(f'\n== top {dim} ({start} -> {end})')
        for row in r.get('rows', []):
            ctr = row['ctr'] * 100
            print(f"{row['clicks']:>5} clicks {row['impressions']:>7} impr  ctr {ctr:4.1f}%  pos {row['position']:5.1f}  {clean(row['keys'][0])}")
        if not r.get('rows'):
            print('   (no data yet)')


def cmd_inspect(url):
    r = gsc().urlInspection().index().inspect(body={'inspectionUrl': url, 'siteUrl': SITE}).execute()
    print(json.dumps(r['inspectionResult'].get('indexStatusResult', {}), indent=1))


if __name__ == '__main__':
    cmds = {'token': cmd_token, 'verify': cmd_verify, 'add': cmd_add, 'owner': cmd_owner,
            'sitemap': cmd_sitemap, 'status': cmd_status, 'top': cmd_top, 'inspect': cmd_inspect}
    if len(sys.argv) < 2 or sys.argv[1] not in cmds:
        sys.exit(__doc__)
    cmds[sys.argv[1]](*sys.argv[2:])
