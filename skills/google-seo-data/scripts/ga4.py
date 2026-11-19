#!/usr/bin/env python3
"""Google Analytics 4 through the same service account as gsc.py (read-only).

Environment:
  GOOGLE_SA_JSON   path to the service-account key   (default: ~/.config/google-seo/sa.json)
  GA4_PROPERTY     numeric property id, e.g. 123456789 (required when the key sees more than one)

Commands:
  props            accounts/properties visible to the service account
  report [DAYS]    top pages, sources and countries, last DAYS days (default 28)
  landing [DAYS]   landing pages with sessions and engagement rate
  realtime         active users right now, by page
"""
import os
import re
import sys
from datetime import date, timedelta

from google.oauth2 import service_account
from googleapiclient.discovery import build

SA_JSON = os.path.expanduser(os.environ.get('GOOGLE_SA_JSON', '~/.config/google-seo/sa.json'))
SCOPES = ['https://www.googleapis.com/auth/analytics.readonly']


def creds():
    if not os.path.exists(SA_JSON):
        sys.exit(f'service-account key not found at {SA_JSON} (set GOOGLE_SA_JSON)')
    mode = os.stat(SA_JSON).st_mode & 0o777
    if mode & 0o077 and os.environ.get('GOOGLE_SA_JSON_INSECURE') != '1':
        sys.exit(f'{SA_JSON} is readable by others (mode {mode:o}); run chmod 600 (or GOOGLE_SA_JSON_INSECURE=1 to override)')
    return service_account.Credentials.from_service_account_file(SA_JSON, scopes=SCOPES)


def clean(s, n=120):
    """Untrusted text (site HTML, API rows) -> one printable line. Control chars could forge output lines."""
    return re.sub(r'[\x00-\x1f\x7f]+', ' ', str(s))[:n]


def admin():
    return build('analyticsadmin', 'v1beta', credentials=creds(), cache_discovery=False)


def data():
    return build('analyticsdata', 'v1beta', credentials=creds(), cache_discovery=False)


def properties():
    out = []
    for acc in admin().accountSummaries().list().execute().get('accountSummaries', []):
        for p in acc.get('propertySummaries', []):
            out.append((acc['displayName'], p['displayName'], p['property']))
    return out


def prop_id():
    env = os.environ.get('GA4_PROPERTY')
    if env:
        return env if env.startswith('properties/') else 'properties/' + env
    ps = properties()
    if not ps:
        sys.exit('the service account sees no GA4 property: add its client_email as Viewer under Admin > Property access management')
    if len(ps) > 1:
        sys.exit('several GA4 properties visible; set GA4_PROPERTY explicitly (run: props)')
    return ps[0][2]


def cmd_props():
    ps = properties()
    for acc, name, pid in ps:
        print(f'{pid:<22} {clean(acc)} / {clean(name)}')
    if not ps:
        print('no property visible (grant the service account access first)')


def run(dims, mets, days, limit=15):
    end = date.today()
    start = end - timedelta(days=int(days))
    r = data().properties().runReport(property=prop_id(), body={
        'dateRanges': [{'startDate': start.isoformat(), 'endDate': end.isoformat()}],
        'dimensions': [{'name': d} for d in dims], 'metrics': [{'name': m} for m in mets],
        'limit': limit, 'orderBys': [{'metric': {'metricName': mets[0]}, 'desc': True}],
    }).execute()
    return r.get('rows', [])


def _print(rows, fmt):
    for row in rows:
        # query strings can carry emails, member ids or tokens: never report them
        k = ' / '.join(clean(v['value'].split('?')[0]) for v in row['dimensionValues'])
        print(fmt(*(v['value'] for v in row['metricValues'])), k)
    if not rows:
        print('   (no data yet)')


def cmd_report(days='28'):
    print(f'== GA4 {prop_id()} - last {days} days')
    for title, dims in (('pages', ['pagePath']), ('sources', ['sessionSource', 'sessionMedium']), ('countries', ['country'])):
        print(f'\n-- {title}')
        _print(run(dims, ['screenPageViews', 'activeUsers'], days), lambda pv, au: f'{pv:>6} views {au:>5} users ')


def cmd_landing(days='28'):
    print(f'== GA4 {prop_id()} - landing pages, last {days} days')
    _print(run(['landingPage'], ['sessions', 'engagementRate'], days),
           lambda s, er: f'{s:>6} sessions  engaged {float(er) * 100:4.1f}% ')


def cmd_realtime():
    r = data().properties().runRealtimeReport(property=prop_id(), body={
        'dimensions': [{'name': 'unifiedScreenName'}], 'metrics': [{'name': 'activeUsers'}],
    }).execute()
    for row in r.get('rows', []):
        print(row['metricValues'][0]['value'], 'active on', clean(row['dimensionValues'][0]['value']))
    if not r.get('rows'):
        print('nobody on the site right now')


if __name__ == '__main__':
    cmds = {'props': cmd_props, 'report': cmd_report, 'landing': cmd_landing, 'realtime': cmd_realtime}
    if len(sys.argv) < 2 or sys.argv[1] not in cmds:
        sys.exit(__doc__)
    cmds[sys.argv[1]](*sys.argv[2:])
