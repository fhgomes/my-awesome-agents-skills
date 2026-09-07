#!/usr/bin/env python3
"""Minimal Ghost Admin API client (JWT from an integration key). Import or run.

Environment:
  GHOST_ADMIN_API_KEY   id:secret from Settings > Integrations > Custom integration (required), or
  GHOST_ADMIN_API_KEY_FILE  path to a chmod 600 file holding it (never type the secret on a command line)
  GHOST_URL             where to send requests, default https://<GHOST_HOST> or http://127.0.0.1:2368
  GHOST_HOST            public hostname; sent as Host header when GHOST_URL points at localhost
                        behind a proxy (Ghost validates the JWT audience against its configured url)

  python3 ghost_admin.py GET /ghost/api/admin/site/
"""
import base64
import hashlib
import hmac
import json
import os
import subprocess
import sys
import time



def _secret(name):
    v = os.environ.get(name, '')
    f = os.environ.get(name + '_FILE')
    if not v and f:
        v = open(os.path.expanduser(f)).read().strip()
    return v


KEY = _secret('GHOST_ADMIN_API_KEY')
HOST = os.environ.get('GHOST_HOST', '')
BASE = os.environ.get('GHOST_URL') or (f'https://{HOST}' if HOST else 'http://127.0.0.1:2368')


def token():
    if ':' not in KEY:
        sys.exit('GHOST_ADMIN_API_KEY missing (format id:secret)')
    key_id, secret = KEY.split(':', 1)
    now = int(time.time())

    def b64(obj):
        raw = json.dumps(obj, separators=(',', ':')).encode()
        return base64.urlsafe_b64encode(raw).rstrip(b'=').decode()

    msg = b64({'alg': 'HS256', 'kid': key_id, 'typ': 'JWT'}) + '.' + \
          b64({'iat': now, 'exp': now + 300, 'aud': '/admin/'})
    sig = hmac.new(bytes.fromhex(secret), msg.encode(), hashlib.sha256).digest()
    return msg + '.' + base64.urlsafe_b64encode(sig).rstrip(b'=').decode()


def headers():
    h = ['-H', 'Authorization: Ghost ' + token(), '-H', 'Accept-Version: v5.0']
    if HOST and BASE.startswith('http://127.0.0.1'):
        h += ['-H', 'Host: ' + HOST, '-H', 'X-Forwarded-Proto: https']
    return h


def call(method, path, body=None):
    cmd = ['curl', '-s', '-X', method, '-H', 'Content-Type: application/json'] + headers() + ['--', BASE + path]
    if body is not None:
        cmd += ['-d', json.dumps(body, ensure_ascii=False)]
    out = subprocess.run(cmd, capture_output=True, text=True).stdout
    try:
        return json.loads(out)
    except ValueError:
        raise RuntimeError('non-JSON answer from Ghost: ' + out[:400])


def upload_image(path, purpose='image'):
    """purpose: image | profile_image | icon. Returns the public URL."""
    if not os.path.isfile(path) or any(c in path for c in ';,"'):
        raise ValueError('upload path must be an existing file without ; , or " (curl -F parses them)')
    cmd = ['curl', '-s', '-X', 'POST', '-F', 'purpose=' + purpose, '-F', 'file=@' + path] + headers() + \
          ['--', BASE + '/ghost/api/admin/images/upload/']
    r = json.loads(subprocess.run(cmd, capture_output=True, text=True).stdout)
    if 'images' not in r:
        raise RuntimeError('upload failed: ' + json.dumps(r)[:300])
    return r['images'][0]['url']


if __name__ == '__main__':
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    body = json.loads(sys.argv[3]) if len(sys.argv) > 3 else None
    print(json.dumps(call(sys.argv[1], sys.argv[2], body), indent=1, ensure_ascii=False)[:4000])
