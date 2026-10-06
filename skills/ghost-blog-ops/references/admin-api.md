# Ghost Admin API — the recipe that works, and the walls

Validated on Ghost 5.x and 6.x self-hosted in Docker behind Cloudflare.

## Authentication: JWT with the standard library

The Admin API key (`Admin → Settings → Integrations → Add custom integration`)
has the form `id:hex_secret`. Build an HS256 JWT with `kid = id`,
`aud = "/admin/"`, 5-minute expiry. No npm or pip package needed:

```python
import hmac, hashlib, base64, json, time

def ghost_token(key: str) -> str:
    kid, secret = key.split(":")
    b64 = lambda b: base64.urlsafe_b64encode(b).rstrip(b"=").decode()
    now = int(time.time())
    header = b64(json.dumps({"alg": "HS256", "kid": kid, "typ": "JWT"}, separators=(",", ":")).encode())
    payload = b64(json.dumps({"iat": now, "exp": now + 300, "aud": "/admin/"}, separators=(",", ":")).encode())
    sig = b64(hmac.new(bytes.fromhex(secret), f"{header}.{payload}".encode(), hashlib.sha256).digest())
    return f"{header}.{payload}.{sig}"
```

Header: `Authorization: Ghost <token>`. Generate a fresh token per call.
Keep the key in a `.env` outside any repo. A key that ever landed in a notes
file, a chat, or a commit is leaked: rotate it in the Admin UI.

## Behind Cloudflare: call localhost with the right headers

The public URL returns **403, Cloudflare error 1010** for API clients. Call
the container directly and impersonate the canonical host:

```bash
curl -s "http://127.0.0.1:2368/ghost/api/admin/posts/?limit=1" \
  -H "Authorization: Ghost $TOKEN" \
  -H "Host: blog.example.com" \
  -H "X-Forwarded-Proto: https"
```

Without `Host` + `X-Forwarded-Proto`, Ghost answers 302 to its canonical URL,
which lands on Cloudflare again. With a self-signed local certificate use
`curl -k`.

## Reading and writing content

| Need | Call |
|---|---|
| Read a page/post body | `GET /ghost/api/admin/pages/?filter=slug:<slug>&formats=html,lexical` |
| Create from HTML | `POST /ghost/api/admin/posts/?source=html` with `{"posts":[{"title","html","tags":[{"name":..}],"custom_excerpt","meta_description","status":"draft"}]}` |
| Update from HTML | `PUT /ghost/api/admin/posts/<id>/?source=html` with a **fresh `updated_at`** |
| Change one field | `PUT /ghost/api/admin/pages/<id>/` with only that field + `updated_at` |
| Set a page template | field `custom_template: "custom-landing"` (file `custom-landing.hbs` in the theme) |
| Members-only | field `visibility: "members"` (or `"public"`) |
| Free-tier welcome page | `PUT /ghost/api/admin/tiers/<id>/` with `welcome_page_url` |
| Deploy a theme | `POST /ghost/api/admin/themes/upload/` as `multipart/form-data`, field `file`, type `application/zip` |

Rules:

- **`updated_at` is the collision check.** GET right before the PUT and send
  the value you just read. A stale value returns 409. If `updated_at` moved
  and you did not PUT, the editor is open and autosaving: do not overwrite.
- **Never send `html` without `?source=html`.** Ghost treats the payload as
  lexical and replaces the content with garbage. This is how a hand-built HTML
  card page gets destroyed.
- A PUT does not return `html` by default; re-GET with `?formats=html`.
- Partial PUT (only the target field + `updated_at`) is the safe way to touch
  metadata on pages whose copy is hand-edited.
- Theme upload: **the zip file name is the theme name.** If it matches the
  active theme it overwrites and stays active (`active: true` in the
  response, effect immediate). Any other name creates a new, inactive theme.

### Safe-edit protocol for hand-edited pages

```bash
# 1) backup both formats
python scripts/ghost_admin.py get "pages/?filter=slug:$SLUG&formats=html,lexical" > "backup-$SLUG.json"
# 2) fingerprint the copy
python - "backup-$SLUG.json" <<'EOF'
import json,hashlib,sys; d=json.load(open(sys.argv[1])); print(hashlib.md5(d["pages"][0]["html"].encode()).hexdigest())
EOF
# 3) partial PUT of the metadata only
python scripts/ghost_admin.py put-partial pages "$ID" --json '{"custom_excerpt":"new summary"}'
# 4) re-fingerprint; identical hash = copy untouched
```

## What the integration token cannot do

| Call | Result | Do instead |
|---|---|---|
| `PUT /settings/` | Ghost 5: `501 NotImplementedError`; Ghost 6: `403 NoPermissionError` | Admin UI, session login, or MySQL |
| `PUT /users/<id>/` | `NotImplementedError` (also: ids are hex, not `1`; use `/users/me/`) | MySQL or Admin UI |
| `GET /themes/`, `DELETE /themes/<name>/` | 403 | Admin → Design → Themes (a wrongly named upload needs manual cleanup) |
| Portal, e-mail/SMTP, labs, integrations, staff | no endpoint or 403 | Admin UI / browser automation |

Different Ghost versions give a different error for the same wall. Do not
spend a session retrying: switch layer.

## MySQL fallbacks

Credentials come from the Ghost `.env` (`MYSQL_ROOT_PASSWORD`); the database
is usually `ghost` in a container next to the blog container.

- `key` is a **reserved word in MySQL 8**: write `` `key` `` or the statement
  errors out.
- Pipe the SQL through stdin; `-e` breaks on nested quotes through `docker exec`.
- Settings are **cached in memory**: restart the Ghost container after the
  write and wait ~12–25 s. Verify on the served HTML, not on the row.

```bash
ROOT_PASS=$(grep -oE '^MYSQL_ROOT_PASSWORD=.*' "$GHOST_ENV_FILE" | cut -d= -f2-)
cat > /tmp/nav-fix.sql <<'EOF'
SELECT `key`, `value` FROM settings WHERE `key`='navigation';   -- backup first
UPDATE settings SET `value`='[{"label":"Home","url":"/"},{"label":"Newsletter","url":"/newsletter/"}]', updated_at=NOW()
 WHERE `key`='navigation';
SELECT ROW_COUNT();
EOF
docker exec -i -e MYSQL_PWD="$ROOT_PASS" ghost-mysql mysql -u root ghost < /tmp/nav-fix.sql
docker restart ghost-blog && sleep 20
curl -s "$GHOST_URL/" | grep -oE 'href="[^"]*"[^>]*>[[:space:]]*Newsletter'
```

Theme custom settings live in **two** tables and both must change:

```sql
-- what the Admin UI/API writes
UPDATE settings SET `value`='<new>', updated_at=NOW() WHERE `key`='<setting_key>';
-- what Handlebars reads at runtime
UPDATE custom_theme_settings SET `value`='<new>' WHERE `key`='<setting_key>' AND theme='<theme-name>';
```

A new custom setting declared in `package.json` needs a row in `settings`
(`group_name='theme'`, `type='string'`, 24-char hex `id`) before Ghost sees
it; a restart alone does nothing.

Which theme is active: `SELECT value FROM settings WHERE \`key\`='active_theme';`
(a stale folder with a similar name is the classic wrong deploy target).

Recovering an overwritten manual edit: the `post_revisions` table keeps the
editor's history for the post id. Diff against it before writing again.

## Verify, always on the served page

```bash
# the CSS the browser actually gets (hash from the page source)
curl -s "$GHOST_URL/assets/css/screen.css?v=<hash>" | grep -c ".hero {"
# the menu the visitor sees
curl -s "$GHOST_URL/" | grep -oE '<a[^>]*class="nav-link"[^>]*>[^<]*'
```

A container file, a DB row or a `gscan` pass are not proof. The served
response is.
