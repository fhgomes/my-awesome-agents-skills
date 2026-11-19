#!/usr/bin/env python3
"""Sentinel toolbox: detect which vetted open-source security tools are missing on each
host, suggest them (never install), and run the installed ones with normalized JSON.

  sentinel_toolbox.py check [--all-hosts | --host LABEL] [--text]
  sentinel_toolbox.py check --all-hosts --notify-cmd 'CMD'   # message on stdin, only when suggestions change
  sentinel_toolbox.py run <tool> [targets...] [--host LABEL]
  sentinel_toolbox.py show [--host LABEL]                    # last saved results

Catalog: ../references/toolbox-catalog.json (trust notes, install channel, why). Output schema:
sentinel-toolbox/v1. Secrets are never stored. Python 3.8+ standard library only.

Configuration (environment, all optional):
  SENTINEL_TOOLBOX_HOSTS        remote hosts as "label=ssh_alias,label2=alias2" (one SSH connection per call)
  SENTINEL_TOOLBOX_LOCAL_LABEL  label of this host in results (default: local)
  SENTINEL_TOOLBOX_STATE        where results are saved (default: ~/.local/state/sentinel-toolbox)
  SENTINEL_SCOPE_EXCLUDE_RE     regex; targets, containers and findings matching it are dropped
  SENTINEL_REPO_ROOTS           os.pathsep-separated roots searched for git repos (default: cwd)
  SENTINEL_DOCKER_BENCH_DIR     docker-bench-security checkout (default: /opt/docker-bench-security)
"""
import argparse
import datetime as dt
import glob
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import tarfile
import tempfile

HERE = Path(__file__).resolve().parent
CATALOG = next((p for p in (HERE.parent / 'references' / 'toolbox-catalog.json', HERE / 'toolbox-catalog.json')
                if p.is_file()), HERE.parent / 'references' / 'toolbox-catalog.json')
STATE = Path(os.environ.get('SENTINEL_TOOLBOX_STATE') or Path.home() / '.local' / 'state' / 'sentinel-toolbox')
_SCOPE = os.environ.get('SENTINEL_SCOPE_EXCLUDE_RE', '')
SCOPE_EXCLUDE = re.compile(_SCOPE, re.I) if _SCOPE else None
REMOTE_HOSTS = dict(kv.split('=', 1) for kv in os.environ.get('SENTINEL_TOOLBOX_HOSTS', '').split(',') if '=' in kv)
LOCAL_LABEL = os.environ.get('SENTINEL_TOOLBOX_LOCAL_LABEL', 'local')
REPO_ROOTS = [Path(p) for p in os.environ.get('SENTINEL_REPO_ROOTS', os.getcwd()).split(os.pathsep) if p]
SEVERITIES = ['critical', 'high', 'medium', 'low', 'info']
NOTIFY_EVERY = dt.timedelta(days=28)
UTC = dt.timezone.utc


def now():
    return dt.datetime.now(UTC).replace(microsecond=0)


def catalog():
    return json.loads(CATALOG.read_text())


def sh(cmd, timeout=60, sudo=False, env=None):
    if sudo and os.geteuid() != 0:
        cmd = ['sudo', '-n'] + cmd
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL, env=env)
        return p.returncode, p.stdout, p.stderr
    except FileNotFoundError:
        return 127, '', 'not found'
    except subprocess.TimeoutExpired:
        return 124, '', f'timeout after {timeout}s'


def in_scope(value):
    if SCOPE_EXCLUDE is None:
        return True
    return not SCOPE_EXCLUDE.search(json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value)


# ---------------------------------------------------------------- detection

def locate(tool):
    if tool.get('path_env') or tool.get('default_dir'):
        d = os.environ.get(tool.get('path_env', ''), '') or tool.get('default_dir', '')
        p = Path(d) / tool['binary']
        return str(p) if p.is_file() else None
    for name in [tool['binary']] + tool.get('alt_binaries', []):
        found = shutil.which(name) or next((p for p in (f'/usr/sbin/{name}', f'/usr/bin/{name}') if os.access(p, os.X_OK)), None)
        if found:
            return found
    return None


def version_of(tool, path):
    cmd = tool.get('version_cmd')
    if not cmd:
        return ''
    cmd = [path] + cmd[1:] if cmd[0] == tool['binary'] or cmd[0] in tool.get('alt_binaries', []) else cmd
    _, out, err = sh(cmd, timeout=15)
    m = re.search(r'(\d+\.\d+(?:\.\d+)?(?:[.+~-][0-9A-Za-z.]+)?)', out + '\n' + err)
    return m.group(1) if m else ''


def detect_tool(tool):
    path = locate(tool)
    row = {'id': tool['id'], 'installed': bool(path), 'path': path, 'version': '', 'issues': []}
    if path:
        row['version'] = version_of(tool, path)
        if any(row['version'].startswith(v) for v in tool.get('known_bad_versions', [])):
            row['issues'].append(f"version {row['version']} is a known-compromised release; remove and reinstall a verified one")
        service = tool.get('install', {}).get('service')
        if service:
            rc, out, _ = sh(['systemctl', 'is-active', service], timeout=10)
            row['service_active'] = out.strip() == 'active'
            if not row['service_active']:
                row['issues'].append(f'installed but service {service} is {out.strip() or "unknown"}')
    return row


def local_check():
    cat = catalog()
    rows = [detect_tool(t) for t in cat['tools']]
    by_id = {t['id']: t for t in cat['tools']}
    suggestions = []
    for r in rows:
        t = by_id[r['id']]
        if r['installed'] and not r['issues']:
            continue
        suggestions.append({'id': t['id'], 'priority': t['priority'], 'category': t['category'],
                            'action': 'fix' if r['installed'] else 'install',
                            'reason': '; '.join(r['issues']) if r['issues'] else 'not installed',
                            'purpose': t['purpose'], 'why_here': t['why_here'], 'weight': t['weight'],
                            'trust': t['trust'], 'install': t['install'], 'requires_owner_ok': True})
    suggestions.sort(key=lambda s: (s['priority'], s['id']))
    return {'schema': 'sentinel-toolbox-check/v1', 'host': socket.gethostname(), 'checked_at': now().isoformat(),
            'tools': rows, 'suggestions': suggestions}


# ---------------------------------------------------------------- normalized results

def result(tool, status, target=None, findings=(), summary=None, error=None, version=''):
    findings = [f for f in findings if in_scope(f)]
    counts = {s: 0 for s in SEVERITIES}
    for f in findings:
        counts[f['severity']] = counts.get(f['severity'], 0) + 1
    doc = {'schema': 'sentinel-toolbox/v1', 'tool': tool, 'tool_version': version, 'host': socket.gethostname(),
           'ran_at': now().isoformat(), 'status': status, 'target': target, 'counts': counts,
           'summary': summary or {}, 'findings': findings}
    if error:
        doc['error'] = error
    return doc


def finding(fid, severity, title, location='', detail=''):
    sev = (severity or 'info').lower()
    sev = {'warn': 'medium', 'moderate': 'medium', 'ok': 'info', 'unknown': 'info', 'negligible': 'info'}.get(sev, sev)
    if sev not in SEVERITIES:
        sev = 'info'
    return {'id': str(fid)[:160], 'severity': sev, 'title': str(title)[:300], 'location': str(location)[:300],
            'detail': str(detail)[:500]}


def cvss_severity(score):
    try:
        s = float(score)
    except (TypeError, ValueError):
        return 'medium'
    return 'critical' if s >= 9 else 'high' if s >= 7 else 'medium' if s >= 4 else 'low'


def default_repos():
    repos = []
    for root in REPO_ROOTS:
        hits = [root / '.git'] + [Path(g) for depth in ('*', '*/*') for g in glob.glob(str(root / depth / '.git'))]
        for git in sorted(h for h in hits if h.exists()):
            repo = str(git.parent)
            if in_scope(repo) and repo not in repos:
                repos.append(repo)
    return repos


def default_domains():
    names = set()
    for conf in glob.glob('/etc/nginx/sites-enabled/*') + glob.glob('/etc/nginx/conf.d/*.conf'):
        try:
            text = Path(conf).read_text(errors='replace')
        except OSError:
            continue
        for line in re.findall(r'^\s*server_name\s+([^;]+);', text, re.M):
            for n in line.split():
                if '.' in n and not n.startswith(('*', '~')) and in_scope(n):
                    names.add(n)
    return sorted(names)


def run_needrestart(path, targets, ver):
    rc, out, err = sh([path, '-b', '-r', 'l'], timeout=120, sudo=True)
    if rc not in (0, 1) and not out:
        return result('needrestart', 'error', error=err.strip()[:300], version=ver)
    kv = re.findall(r'^NEEDRESTART-(\w+):\s*(.*)$', out, re.M)
    data = {}
    services = []
    for k, v in kv:
        if k == 'SVC':
            services.append(v.strip())
        else:
            data[k] = v.strip()
    findings = []
    ksta = data.get('KSTA', '0')
    if ksta in ('2', '3'):
        findings.append(finding('kernel-reboot-pending', 'medium', 'Running kernel is older than the installed one (reboot pending)',
                                'kernel', f"running {data.get('KCUR', '?')}, expected {data.get('KEXP', '?')}"))
    for svc in services:
        findings.append(finding('service-restart:' + svc, 'low', 'Service still uses outdated libraries', svc, 'restart picks up patched libraries'))
    return result('needrestart', 'ok', 'host', findings,
                  {'kernel_running': data.get('KCUR'), 'kernel_expected': data.get('KEXP'), 'kernel_status': ksta,
                   'services_pending': len(services)}, version=ver)


def run_lynis(path, targets, ver):
    with tempfile.TemporaryDirectory(prefix='sentinel-lynis-') as d:
        report, log = f'{d}/report.dat', f'{d}/lynis.log'
        rc, out, err = sh([path, 'audit', 'system', '--quick', '--no-colors', '--quiet',
                           '--report-file', report, '--logfile', log], timeout=900, sudo=True)
        _, text, _ = sh(['cat', report], timeout=10, sudo=True)
        sh(['rm', '-f', report, log], timeout=10, sudo=True)
    if not text:
        return result('lynis', 'error', error=(err or out).strip()[:300] or 'no report', version=ver)
    findings = []
    for kind, sev in (('warning', 'medium'), ('suggestion', 'low')):
        for line in re.findall(rf'^{kind}\[\]=(.*)$', text, re.M):
            parts = line.split('|')
            findings.append(finding(parts[0], sev, parts[1] if len(parts) > 1 else line,
                                    'lynis:' + kind, parts[2] if len(parts) > 2 and parts[2] != '-' else ''))
    idx = re.search(r'^hardening_index=(\d+)', text, re.M)
    return result('lynis', 'ok', 'host', findings,
                  {'hardening_index': int(idx.group(1)) if idx else None,
                   'warnings': sum(1 for f in findings if f['severity'] == 'medium'),
                   'suggestions': sum(1 for f in findings if f['severity'] == 'low')}, version=ver)


def run_testssl(path, targets, ver):
    domains = [t for t in (targets or default_domains()) if in_scope(t)]
    findings, errors = [], []
    for dom in domains:
        with tempfile.TemporaryDirectory(prefix='sentinel-testssl-') as d:
            jf = f'{d}/out.json'
            rc, out, err = sh([path, '--quiet', '--color', '0', '--warnings', 'off', '--ip', 'one',
                               '--severity', 'LOW', '--jsonfile', jf, dom], timeout=900)
            try:
                rows = json.loads(Path(jf).read_text())
            except (OSError, ValueError):
                errors.append(f'{dom}: no JSON (rc={rc})')
                continue
        for r in rows if isinstance(rows, list) else []:
            if str(r.get('severity', '')).upper() in ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL'):
                findings.append(finding(r.get('id', ''), r['severity'], r.get('finding', ''),
                                        f"{dom}:{r.get('port', '443')}", ' '.join(x for x in (r.get('cve', ''), r.get('cwe', '')) if x)))
    status = 'ok' if domains and len(errors) < len(domains) else 'error'
    return result('testssl', status, domains, findings, {'domains': len(domains), 'errors': errors}, version=ver)


def run_gitleaks(path, targets, ver):
    repos = [t for t in (targets or default_repos()) if in_scope(t)]
    findings, errors = [], []
    for repo in repos:
        with tempfile.TemporaryDirectory(prefix='sentinel-gitleaks-') as d:
            rf = f'{d}/r.json'
            rc, out, err = sh([path, 'detect', '--source', repo, '--report-format', 'json', '--report-path', rf,
                               '--redact', '--no-banner', '--exit-code', '0', '--log-level', 'error'], timeout=900)
            try:
                rows = json.loads(Path(rf).read_text() or '[]')
            except (OSError, ValueError):
                errors.append(f'{repo}: no report (rc={rc})')
                continue
        for r in rows:
            # Never keep Secret / Match / Line: even redacted, they are not needed.
            findings.append(finding(r.get('Fingerprint') or f"{r.get('RuleID')}:{r.get('File')}:{r.get('StartLine')}",
                                    'high', f"{r.get('RuleID', 'secret')}: {r.get('Description', '')}",
                                    f"{repo}/{r.get('File', '')}:{r.get('StartLine', '')}",
                                    f"commit {str(r.get('Commit', ''))[:12]} {str(r.get('Date', ''))[:10]}".strip()))
    return result('gitleaks', 'ok' if repos else 'error', repos, findings, {'repos': len(repos), 'errors': errors}, version=ver)


def run_osv(path, targets, ver):
    dirs = [t for t in (targets or default_repos()) if in_scope(t)]
    findings, errors = [], []
    for d in dirs:
        rc, out, err = sh([path, 'scan', 'source', '-r', '--format', 'json', d], timeout=600)
        if rc not in (0, 1) or not out.strip().startswith('{'):
            rc, out, err = sh([path, '--format', 'json', '-r', d], timeout=600)
        try:
            doc = json.loads(out)
        except ValueError:
            if 'no package sources found' not in (err + out).lower():
                errors.append(f'{d}: rc={rc}')
            continue
        for res in doc.get('results') or []:
            src = (res.get('source') or {}).get('path', d)
            for pkg in res.get('packages') or []:
                p = pkg.get('package') or {}
                sev = {}
                for g in pkg.get('groups') or []:
                    for i in g.get('ids') or []:
                        sev[i] = g.get('max_severity')
                for v in pkg.get('vulnerabilities') or []:
                    vid = v.get('id', '')
                    findings.append(finding(vid, cvss_severity(sev.get(vid)), f"{p.get('name')} {p.get('version')} ({p.get('ecosystem')})",
                                            src, ', '.join(a for a in v.get('aliases', []) if a.startswith('CVE-'))[:200]))
    return result('osv-scanner', 'ok' if dirs else 'error', dirs, findings, {'dirs': len(dirs), 'errors': errors}, version=ver)


def running_images():
    rc, out, _ = sh(['docker', 'ps', '--format', '{{.Names}}\t{{.Image}}'], timeout=20)
    images = {}
    for line in out.splitlines():
        name, _, image = line.partition('\t')
        if in_scope(name) and in_scope(image):
            images.setdefault(image, []).append(name)
    return images


def run_trivy(path, targets, ver):
    bad = next((t for t in catalog()['tools'] if t['id'] == 'trivy'), {}).get('known_bad_versions', [])
    if any(ver.startswith(b) for b in bad):
        return result('trivy', 'refused', error=f'trivy {ver} is a known-compromised release; not executed', version=ver)
    images = {t: [] for t in targets if in_scope(t)} if targets else running_images()
    findings, errors = [], []
    for image, containers in images.items():
        rc, out, err = sh([path, 'image', '--quiet', '--format', 'json', '--scanners', 'vuln',
                           '--severity', 'HIGH,CRITICAL', '--timeout', '10m', image], timeout=900)
        try:
            doc = json.loads(out)
        except ValueError:
            errors.append(f'{image}: rc={rc}')
            continue
        for res in doc.get('Results') or []:
            for v in res.get('Vulnerabilities') or []:
                findings.append(finding(v.get('VulnerabilityID'), v.get('Severity'),
                                        f"{v.get('PkgName')} {v.get('InstalledVersion')} -> {v.get('FixedVersion') or 'no fix'}",
                                        f"{image} ({', '.join(containers) or 'image'})", res.get('Target', '')))
    return result('trivy', 'ok' if images else 'error', sorted(images), findings, {'images': len(images), 'errors': errors}, version=ver)


def run_docker_bench(path, targets, ver):
    d = str(Path(path).parent)
    with tempfile.TemporaryDirectory(prefix='sentinel-dbench-') as tmp:
        log = f'{tmp}/bench'
        exclude = os.environ.get('SENTINEL_DOCKER_BENCH_EXCLUDE', '')   # container-name patterns for -x
        script = 'cd "$1" && exec sh ./docker-bench-security.sh -b -l "$2"' + (' -x "$3"' if exclude else '')
        rc, out, err = sh(['sh', '-c', script, 'x', d, log, exclude], timeout=900, sudo=True)
        _, text, _ = sh(['cat', log + '.json'], timeout=10, sudo=True)
        sh(['rm', '-f', log, log + '.json'], timeout=10, sudo=True)
    try:
        doc = json.loads(text)
    except ValueError:
        return result('docker-bench', 'error', error=(err or out).strip()[:300] or 'no JSON log', version=ver)
    findings = []
    for section in doc.get('tests') or []:
        for r in section.get('results') or []:
            if r.get('result') == 'WARN':
                items = [i for i in (r.get('items') or []) if in_scope(i)]
                findings.append(finding('CIS-' + str(r.get('id')), 'medium', r.get('desc', ''), section.get('desc', ''),
                                        ', '.join(map(str, items))[:400]))
    return result('docker-bench', 'ok', 'docker', findings, {'score': doc.get('score'), 'checks': doc.get('checks')}, version=ver)


def run_debsums(path, targets, ver):
    rc, out, err = sh([path, '-c'], timeout=1800, sudo=True)
    changed = [l.strip() for l in out.splitlines() if l.strip().startswith('/')]
    missing = re.findall(r'missing file (\S+)', err)
    findings = [finding('changed:' + f, 'medium', 'Package file differs from its package checksum', f) for f in changed]
    findings += [finding('missing:' + f, 'low', 'Package file is missing', f) for f in missing]
    return result('debsums', 'ok', 'host', findings, {'changed': len(changed), 'missing': len(missing)}, version=ver)


WRAPPERS = {'needrestart': run_needrestart, 'lynis': run_lynis, 'testssl': run_testssl, 'gitleaks': run_gitleaks,
            'osv-scanner': run_osv, 'trivy': run_trivy, 'docker-bench': run_docker_bench, 'debsums': run_debsums}


def local_run(tool_id, targets):
    tool = next((t for t in catalog()['tools'] if t['id'] == tool_id), None)
    if not tool or not tool.get('wrapper'):
        return result(tool_id, 'error', error='unknown tool or no wrapper')
    path = locate(tool)
    if not path:
        doc = result(tool_id, 'not_installed')
        doc['suggestion'] = {'install': tool['install'], 'trust': tool['trust'], 'why_here': tool['why_here'],
                             'requires_owner_ok': True}
        return doc
    return WRAPPERS[tool['wrapper']](path, targets, version_of(tool, path))


# ---------------------------------------------------------------- remote + persistence

def remote(label, argv):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode='w:gz') as tar:
        for f in (Path(__file__).resolve(), CATALOG):
            tar.add(f, arcname=f.name)
    # Forward scope/config so the remote side applies the same exclusions.
    fwd = ' '.join(f'{k}={shquote(os.environ[k])}' for k in
                   ('SENTINEL_SCOPE_EXCLUDE_RE', 'SENTINEL_REPO_ROOTS', 'SENTINEL_DOCKER_BENCH_DIR',
                    'SENTINEL_DOCKER_BENCH_EXCLUDE') if os.environ.get(k))
    cmd = ('d=$(mktemp -d); trap "rm -rf $d" EXIT; tar -xz -C "$d" && '
           + fwd + ' PYTHONDONTWRITEBYTECODE=1 python3 "$d/sentinel_toolbox.py" ' + ' '.join(map(shquote, argv)) + ' --local')
    try:
        p = subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=20', REMOTE_HOSTS[label], cmd],
                           input=buf.getvalue(), capture_output=True, timeout=1800)
    except subprocess.TimeoutExpired:
        return {'host_label': label, 'status': 'error', 'error': 'ssh timeout'}
    try:
        doc = json.loads(p.stdout.decode())
    except ValueError:
        return {'host_label': label, 'status': 'error', 'error': f'ssh rc={p.returncode}, no JSON'}
    return doc


def shquote(s):
    return "'" + str(s).replace("'", "'\"'\"'") + "'"


def save(label, name, doc):
    d = STATE / label
    d.mkdir(parents=True, exist_ok=True)
    (d / f'{name}.json').write_text(json.dumps(doc, ensure_ascii=False, indent=2))


def check_hosts(args):
    out = {}
    if not args.host or args.all_hosts:
        out[LOCAL_LABEL] = local_check()
    labels = list(REMOTE_HOSTS) if args.all_hosts else ([args.host] if args.host else [])
    for label in labels:
        out[label] = remote(label, ['check'])
    for label, doc in out.items():
        doc['host_label'] = label
        save(label, 'check', doc)
    return out


def text_summary(docs):
    lines = []
    for label, doc in docs.items():
        if doc.get('status') == 'error':
            lines.append(f'- {label}: check failed ({doc.get("error")})')
            continue
        sug = doc.get('suggestions', [])
        lines.append(f'- {label}: ' + (', '.join(f"{s['id']} ({s['action']}: {s['reason']})" for s in sug) or 'all vetted tools present'))
    return '\n'.join(lines)


def notify(docs, cmd):
    """Send a short suggestion summary through CMD (message on stdin), only when it changed
    or every NOTIFY_EVERY. Returns SENT or UNCHANGED."""
    state_file = STATE / 'notify.json'
    st = json.loads(state_file.read_text()) if state_file.exists() else {}
    fp_src = {l: sorted(f"{s['id']}:{s['action']}" for s in d.get('suggestions', []) if s['priority'] <= 2)
              for l, d in docs.items() if d.get('status') != 'error'}
    fp = hashlib.sha256(json.dumps(fp_src, sort_keys=True).encode()).hexdigest()
    last = st.get('sent_at')
    stale = not last or now() - dt.datetime.fromisoformat(last) > NOTIFY_EVERY
    if not any(fp_src.values()) or (st.get('fingerprint') == fp and not stale):
        return 'UNCHANGED'
    lines = ['Sentinel toolbox: suggested tools (nothing was installed; installing needs your OK)']
    for label, items in fp_src.items():
        rows = [s for s in docs[label]['suggestions'] if f"{s['id']}:{s['action']}" in items]
        if rows:
            lines.append(f'[{label}]')
            lines += [f"- {s['id']} ({s['action']}, trust {s['trust']['level']}, via {s['install']['method']}): {s['purpose']}"
                      for s in rows]
    p = subprocess.run(['sh', '-c', cmd], input='\n'.join(lines), text=True, capture_output=True, timeout=60)
    if p.returncode:
        raise SystemExit(f'notify command failed (rc={p.returncode}); state not updated')
    STATE.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps({'fingerprint': fp, 'sent_at': now().isoformat()}))
    return 'SENT'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    c = sub.add_parser('check')
    r = sub.add_parser('run')
    r.add_argument('tool')
    r.add_argument('targets', nargs='*')
    s = sub.add_parser('show')
    for p in (c, r, s):
        p.add_argument('--host', choices=sorted(REMOTE_HOSTS) or None)
        p.add_argument('--local', action='store_true', help=argparse.SUPPRESS)
    c.add_argument('--all-hosts', action='store_true')
    c.add_argument('--text', action='store_true')
    c.add_argument('--notify-cmd', help='shell command that receives the summary on stdin')
    args = ap.parse_args()

    if args.local:   # executed on the remote host: print JSON only, persist nothing there
        doc = local_check() if args.cmd == 'check' else local_run(args.tool, args.targets)
        print(json.dumps(doc, ensure_ascii=False))
        return
    if args.cmd == 'check':
        docs = check_hosts(args)
        if args.notify_cmd:
            print(notify(docs, args.notify_cmd))
        elif args.text:
            print(text_summary(docs))
        else:
            print(json.dumps(docs, ensure_ascii=False, indent=2))
    elif args.cmd == 'run':
        label = args.host or LOCAL_LABEL
        doc = remote(label, ['run', args.tool] + args.targets) if args.host else local_run(args.tool, args.targets)
        doc['host_label'] = label
        save(label, args.tool, doc)
        print(json.dumps(doc, ensure_ascii=False, indent=2))
    else:
        label = args.host or LOCAL_LABEL
        out = {p.stem: json.loads(p.read_text()) for p in sorted((STATE / label).glob('*.json'))} if (STATE / label).exists() else {}
        print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
