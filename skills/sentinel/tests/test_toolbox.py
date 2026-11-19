import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
import re
spec = importlib.util.spec_from_file_location('toolbox', HERE / 'scripts' / 'sentinel_toolbox.py')
tb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tb)


class CatalogTest(unittest.TestCase):
    def test_catalog_entries_are_complete(self):
        cat = tb.catalog()
        for t in cat['tools']:
            for key in ('id', 'binary', 'category', 'priority', 'purpose', 'why_here', 'trust', 'install'):
                self.assertIn(key, t, t['id'])
            self.assertIn(t['trust']['level'], ('high', 'medium'))
            if t.get('wrapper'):
                self.assertIn(t['wrapper'], tb.WRAPPERS)

    def test_trivy_compromised_versions_listed(self):
        trivy = next(t for t in tb.catalog()['tools'] if t['id'] == 'trivy')
        self.assertEqual(trivy['known_bad_versions'], ['0.69.4', '0.69.5', '0.69.6'])


class NormalizeTest(unittest.TestCase):
    @mock.patch.object(tb, 'SCOPE_EXCLUDE', re.compile('internal-only', re.I))
    def test_scope_exclusion_drops_findings(self):
        doc = tb.result('x', 'ok', findings=[tb.finding('a', 'high', 't', '/srv/internal-only/app'),
                                              tb.finding('b', 'high', 't', '/srv/shop')])
        self.assertEqual([f['id'] for f in doc['findings']], ['b'])
        self.assertEqual(doc['counts']['high'], 1)

    def test_severity_mapping(self):
        self.assertEqual(tb.finding('a', 'WARN', 't')['severity'], 'medium')
        self.assertEqual(tb.finding('a', 'weird', 't')['severity'], 'info')
        self.assertEqual(tb.cvss_severity('9.8'), 'critical')
        self.assertEqual(tb.cvss_severity(None), 'medium')


class WrapperTest(unittest.TestCase):
    def test_no_scope_configured_keeps_everything(self):
        with mock.patch.object(tb, 'SCOPE_EXCLUDE', None):
            self.assertTrue(tb.in_scope('/srv/anything'))

    @mock.patch.object(tb, 'SCOPE_EXCLUDE', re.compile('internal-only', re.I))
    def test_needrestart_parse(self):
        out = ('NEEDRESTART-VER: 3.11\nNEEDRESTART-KCUR: 7.0.0-38-generic\nNEEDRESTART-KEXP: 7.0.0-43-generic\n'
               'NEEDRESTART-KSTA: 3\nNEEDRESTART-SVC: ssh.service\nNEEDRESTART-SVC: internal-only-api.service\n')
        with mock.patch.object(tb, 'sh', return_value=(0, out, '')):
            doc = tb.run_needrestart('/usr/sbin/needrestart', [], '3.11')
        ids = [f['id'] for f in doc['findings']]
        self.assertIn('kernel-reboot-pending', ids)
        self.assertIn('service-restart:ssh.service', ids)
        self.assertFalse(any('internal-only' in i for i in ids))

    def test_lynis_parse(self):
        report = ('hardening_index=67\nwarning[]=SSH-7408|Root login allowed|-|-|\n'
                  'suggestion[]=KRNL-6000|Harden sysctl|net.ipv4.conf.all.rp_filter|-|\n')
        calls = iter([(0, '', ''), (0, report, ''), (0, '', '')])
        with mock.patch.object(tb, 'sh', side_effect=lambda *a, **k: next(calls)):
            doc = tb.run_lynis('/usr/sbin/lynis', [], '3.1.6')
        self.assertEqual(doc['summary']['hardening_index'], 67)
        self.assertEqual(doc['counts']['medium'], 1)
        self.assertEqual(doc['counts']['low'], 1)

    def test_gitleaks_never_stores_secret(self):
        rows = [{'RuleID': 'generic-api-key', 'Description': 'Generic API Key', 'File': 'app.yml', 'StartLine': 3,
                 'Commit': 'abcdef1234567890', 'Date': '2026-01-01T00:00:00Z', 'Secret': 'SUPERSECRETVALUE',
                 'Match': 'key=SUPERSECRETVALUE', 'Fingerprint': 'abcdef:app.yml:generic-api-key:3'}]

        def fake_sh(cmd, **k):
            Path(cmd[cmd.index('--report-path') + 1]).write_text(json.dumps(rows))
            return 0, '', ''
        with mock.patch.object(tb, 'sh', side_effect=fake_sh):
            doc = tb.run_gitleaks('/usr/bin/gitleaks', ['/srv/demo'], '8.16.0')
        blob = json.dumps(doc)
        self.assertNotIn('SUPERSECRETVALUE', blob)
        self.assertEqual(doc['counts']['high'], 1)

    def test_trivy_refuses_compromised_version(self):
        doc = tb.run_trivy('/usr/bin/trivy', [], '0.69.4')
        self.assertEqual(doc['status'], 'refused')

    def test_osv_parse(self):
        out = json.dumps({'results': [{'source': {'path': '/r/build.gradle'}, 'packages': [{
            'package': {'name': 'log4j-core', 'version': '2.14.1', 'ecosystem': 'Maven'},
            'groups': [{'ids': ['GHSA-jfh8'], 'max_severity': '10.0'}],
            'vulnerabilities': [{'id': 'GHSA-jfh8', 'aliases': ['CVE-2021-44228']}]}]}]})
        with mock.patch.object(tb, 'sh', return_value=(1, out, '')):
            doc = tb.run_osv('/usr/bin/osv-scanner', ['/r'], '2.0.0')
        self.assertEqual(doc['findings'][0]['severity'], 'critical')
        self.assertIn('CVE-2021-44228', doc['findings'][0]['detail'])

    def test_missing_tool_returns_suggestion(self):
        with mock.patch.object(tb, 'locate', return_value=None):
            doc = tb.local_run('gitleaks', [])
        self.assertEqual(doc['status'], 'not_installed')
        self.assertTrue(doc['suggestion']['requires_owner_ok'])


class CheckTest(unittest.TestCase):
    def test_check_suggests_missing_and_inactive(self):
        def fake_detect(tool):
            return {'id': tool['id'], 'installed': tool['id'] == 'auditd', 'path': None, 'version': '',
                    'issues': ['installed but service auditd is inactive'] if tool['id'] == 'auditd' else []}
        with mock.patch.object(tb, 'detect_tool', side_effect=fake_detect):
            doc = tb.local_check()
        by = {s['id']: s for s in doc['suggestions']}
        self.assertEqual(by['auditd']['action'], 'fix')
        self.assertEqual(by['lynis']['action'], 'install')
        self.assertEqual(doc['suggestions'][0]['priority'], 1)

    def test_notify_dedups(self):
        docs = {'local': {'suggestions': [{'id': 'lynis', 'action': 'install', 'priority': 1, 'purpose': 'p',
                                            'trust': {'level': 'high'}, 'install': {'method': 'distro'}}]}}
        with tempfile.TemporaryDirectory() as d, mock.patch.object(tb, 'STATE', Path(d)):
            out = Path(d) / 'sent.txt'
            cmd = f"cat >> '{out}'"
            self.assertEqual(tb.notify(docs, cmd), 'SENT')
            self.assertEqual(tb.notify(docs, cmd), 'UNCHANGED')
            self.assertIn('lynis', out.read_text())
            self.assertEqual(out.read_text().count('Sentinel toolbox'), 1)


if __name__ == '__main__':
    unittest.main()
