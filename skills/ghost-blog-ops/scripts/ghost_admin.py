#!/usr/bin/env python3
"""Minimal Ghost Admin API client, standard library only.

Environment:
  GHOST_URL            public site URL (used for the Host header and as default base)
  GHOST_ADMIN_API_KEY  "id:hex_secret" from Admin -> Integrations -> Custom
  GHOST_ENV_FILE       optional path to a .env holding the two variables above
  GHOST_LOCAL_URL      optional, e.g. http://127.0.0.1:2368 when calling from the
                       host behind Cloudflare (adds Host + X-Forwarded-Proto headers)

Commands:
  get <path>                                     GET /ghost/api/admin/<path>
  post-html <posts|pages> --title T --html-file F [--tags a,b] [--status draft]
                                                 create from HTML (?source=html)
  put-html  <posts|pages> <id> --html-file F     replace the body (fresh updated_at fetched first)
  put-partial <posts|pages> <id> --json '{...}'  change only the given fields (optimistic lock)
  backup <posts|pages> <slug> [--out FILE]       save html + lexical of one item
  theme-upload <file.zip>                        POST /themes/upload/ (zip name = theme name)

All writes fetch the item first and send its current updated_at, which is
Ghost's collision check. Never send html without ?source=html: Ghost would
treat it as lexical and destroy the content.
"""
import argparse
import base64
import hashlib
import hmac
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid


def load_env_file(path):
    if not path or not os.path.isfile(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def token(key):
    kid, secret = key.split(":", 1)
    b64 = lambda b: base64.urlsafe_b64encode(b).rstrip(b"=").decode()
    now = int(time.time())
    header = b64(json.dumps({"alg": "HS256", "kid": kid, "typ": "JWT"}, separators=(",", ":")).encode())
    payload = b64(json.dumps({"iat": now, "exp": now + 300, "aud": "/admin/"}, separators=(",", ":")).encode())
    sig = b64(hmac.new(bytes.fromhex(secret), f"{header}.{payload}".encode(), hashlib.sha256).digest())
    return f"{header}.{payload}.{sig}"


class Ghost:
    def __init__(self):
        load_env_file(os.environ.get("GHOST_ENV_FILE"))
        self.site = os.environ.get("GHOST_URL", "").rstrip("/")
        self.key = os.environ.get("GHOST_ADMIN_API_KEY", "")
        if not self.site or not self.key:
            sys.exit("[fatal] GHOST_URL and GHOST_ADMIN_API_KEY are required (or GHOST_ENV_FILE)")
        local = os.environ.get("GHOST_LOCAL_URL", "").rstrip("/")
        self.base = (local or self.site) + "/ghost/api/admin/"
        self.extra_headers = {}
        if local:
            host = urllib.parse.urlparse(self.site).netloc
            self.extra_headers = {"Host": host, "X-Forwarded-Proto": "https"}

    def request(self, method, path, body=None, content_type="application/json", raw=None):
        url = self.base + path.lstrip("/")
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", f"Ghost {token(self.key)}")
        req.add_header("Accept-Version", "v5.0")
        if data is not None:
            req.add_header("Content-Type", content_type)
        for k, v in self.extra_headers.items():
            req.add_header(k, v)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                text = r.read().decode("utf-8", "replace")
                return json.loads(text) if text else {}
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")
            sys.exit(f"[http {e.code}] {method} {path}\n{detail[:2000]}")

    # helpers -------------------------------------------------------------
    def fetch_one(self, kind, item_id, formats="html,lexical"):
        r = self.request("GET", f"{kind}/{item_id}/?formats={formats}")
        return r[kind][0]

    def fetch_by_slug(self, kind, slug, formats="html,lexical"):
        r = self.request("GET", f"{kind}/?filter=slug:{slug}&formats={formats}")
        items = r.get(kind, [])
        if not items:
            sys.exit(f"[fatal] no {kind} with slug '{slug}'")
        return items[0]


def cmd_get(g, a):
    print(json.dumps(g.request("GET", a.path), indent=2, ensure_ascii=False))


def cmd_post_html(g, a):
    html = open(a.html_file, encoding="utf-8").read()
    item = {"title": a.title, "html": html, "status": a.status}
    if a.tags:
        item["tags"] = [{"name": t.strip()} for t in a.tags.split(",") if t.strip()]
    if a.excerpt:
        item["custom_excerpt"] = a.excerpt
    if a.meta_description:
        item["meta_description"] = a.meta_description
    if a.custom_template:
        item["custom_template"] = a.custom_template
    if a.visibility:
        item["visibility"] = a.visibility
    r = g.request("POST", f"{a.kind}/?source=html", {a.kind: [item]})
    created = r[a.kind][0]
    print(json.dumps({"id": created["id"], "slug": created["slug"], "status": created["status"],
                      "url": created.get("url")}, indent=2))


def cmd_put_html(g, a):
    current = g.fetch_one(a.kind, a.id, formats="html")
    html = open(a.html_file, encoding="utf-8").read()
    payload = {a.kind: [{"html": html, "updated_at": current["updated_at"]}]}
    r = g.request("PUT", f"{a.kind}/{a.id}/?source=html", payload)
    print(json.dumps({"id": a.id, "updated_at": r[a.kind][0]["updated_at"]}, indent=2))


def cmd_put_partial(g, a):
    fields = json.loads(a.json)
    if "html" in fields:
        sys.exit("[fatal] use put-html for the body; a partial PUT must not carry html")
    current = g.fetch_one(a.kind, a.id, formats="html")
    fields["updated_at"] = current["updated_at"]
    r = g.request("PUT", f"{a.kind}/{a.id}/", {a.kind: [fields]})
    item = r[a.kind][0]
    print(json.dumps({k: item.get(k) for k in ["id", "slug", "status", "custom_template",
                                                "visibility", "updated_at"]}, indent=2))


def cmd_backup(g, a):
    item = g.fetch_by_slug(a.kind, a.slug)
    out = a.out or f"backup-{a.kind}-{a.slug}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump({a.kind: [item]}, f, indent=2, ensure_ascii=False)
    digest = hashlib.md5((item.get("html") or "").encode()).hexdigest()
    print(json.dumps({"file": out, "id": item["id"], "updated_at": item["updated_at"], "html_md5": digest}, indent=2))


def cmd_theme_upload(g, a):
    path = a.zip
    name = os.path.basename(path)
    if not name.endswith(".zip"):
        sys.exit("[fatal] expected a .zip file")
    print(f"[info] the theme will be named '{name[:-4]}' (from the file name), make sure it matches the active theme",
          file=sys.stderr)
    boundary = uuid.uuid4().hex
    ctype = mimetypes.guess_type(name)[0] or "application/zip"
    with open(path, "rb") as f:
        content = f.read()
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{name}\"\r\n"
            f"Content-Type: {ctype}\r\n\r\n").encode() + content + f"\r\n--{boundary}--\r\n".encode()
    r = g.request("POST", "themes/upload/", raw=body, content_type=f"multipart/form-data; boundary={boundary}")
    theme = r["themes"][0]
    print(json.dumps({"name": theme["name"], "active": theme.get("active"), "package": theme.get("package", {}).get("version")},
                     indent=2))


def main():
    ap = argparse.ArgumentParser(description="Ghost Admin API, stdlib only")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("get", help="GET an admin path, e.g. 'posts/?limit=3'")
    p.add_argument("path")
    p.set_defaults(fn=cmd_get)

    p = sub.add_parser("post-html", help="create a post or page from an HTML file (draft by default)")
    p.add_argument("kind", choices=["posts", "pages"])
    p.add_argument("--title", required=True)
    p.add_argument("--html-file", required=True)
    p.add_argument("--tags", default="", help="comma-separated tag names")
    p.add_argument("--status", default="draft", choices=["draft", "published", "scheduled"])
    p.add_argument("--excerpt", default="")
    p.add_argument("--meta-description", default="")
    p.add_argument("--custom-template", default="")
    p.add_argument("--visibility", default="", choices=["", "public", "members", "paid"])
    p.set_defaults(fn=cmd_post_html)

    p = sub.add_parser("put-html", help="replace the body of an existing item from an HTML file")
    p.add_argument("kind", choices=["posts", "pages"])
    p.add_argument("id")
    p.add_argument("--html-file", required=True)
    p.set_defaults(fn=cmd_put_html)

    p = sub.add_parser("put-partial", help="change only the given JSON fields (optimistic lock on updated_at)")
    p.add_argument("kind", choices=["posts", "pages"])
    p.add_argument("id")
    p.add_argument("--json", required=True)
    p.set_defaults(fn=cmd_put_partial)

    p = sub.add_parser("backup", help="save html + lexical of one item by slug and print the html md5")
    p.add_argument("kind", choices=["posts", "pages"])
    p.add_argument("slug")
    p.add_argument("--out", default="")
    p.set_defaults(fn=cmd_backup)

    p = sub.add_parser("theme-upload", help="upload a theme zip (file name = theme name)")
    p.add_argument("zip")
    p.set_defaults(fn=cmd_theme_upload)

    a = ap.parse_args()
    a.fn(Ghost(), a)


if __name__ == "__main__":
    main()
