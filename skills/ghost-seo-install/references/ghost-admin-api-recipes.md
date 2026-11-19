# Ghost Admin API recipes and gotchas (Ghost 5/6, self-hosted behind a proxy)

## Auth

Integration key `id:secret` from Settings > Integrations > Custom integration. Token is a
5-minute HS256 JWT with `aud: "/admin/"`, `kid: id`, signed with the **hex-decoded** secret.
`scripts/ghost_admin.py` does this; headers that work:

```
Authorization: Ghost <jwt>
Accept-Version: v5.0
Content-Type: application/json
```

### Talking to Ghost on localhost behind nginx/Cloudflare

Ghost validates requests against its configured `url`. Hitting `http://127.0.0.1:2368`
directly needs the public identity restored:

```
Host: blog.example.com
X-Forwarded-Proto: https
```

Set `GHOST_HOST=blog.example.com GHOST_URL=http://127.0.0.1:2368` and `ghost_admin.py` adds
both. Going through the public URL instead works too but pays for the proxy round trip.

## What integration tokens can and cannot do

| Endpoint | Token | Fallback |
|---|---|---|
| `GET/PUT posts, pages, tags` | yes | - |
| `POST images/upload` (`purpose=image|icon|profile_image`) | yes | - |
| `GET settings` | yes | - |
| `PUT settings` | **no** (6.x `403 NoPermissionError`, 5.x `NotImplementedError`) | MySQL `UPDATE settings` + restart |
| `GET/PUT custom_theme_settings` | **no** | Admin UI, or MySQL `UPDATE custom_theme_settings` + restart |
| `POST themes/upload`, `PUT themes/<name>/activate` | yes | - |
| `POST invites`, session login | no | do it in Ghost Admin UI (out of scope for this skill) |

Ghost caches settings in memory: after any direct SQL write, `docker restart <ghost>` and
verify on the served HTML.

## Updating a post's meta description

```python
p = g.call('GET', f'/ghost/api/admin/posts/slug/{slug}/?fields=id,updated_at')['posts'][0]
g.call('PUT', f"/ghost/api/admin/posts/{p['id']}/",
       {'posts': [{'meta_description': text, 'updated_at': p['updated_at']}]})
```

`updated_at` is mandatory (optimistic locking). Unpublish with `{'status': 'draft', ...}`.

## Custom theme settings

- Declared in the theme's `package.json` under `config.custom`; max 20; `group` is one of
  `site-wide`, `homepage`, `post`. Types: `text`, `select`, `boolean`, `color`, `image`.
- Ghost syncs the declaration into `custom_theme_settings` when the theme is activated or
  Ghost boots with it active. A deploy that copies files + restarts is enough.
- Templates read them as `{{@custom.key}}`; guard with `{{#if @custom.key}}` so an empty
  field renders nothing.

## MySQL notes

- `key` is a reserved word: always `` `key` ``.
- Custom settings table: `custom_theme_settings (theme, key, type, value)`.
- Site settings: `settings (key, value, updated_at)`. Read before write, keep the old value.

## Page bodies

Pages created with `?source=html` are re-parsed by Ghost and lose `<div>`-based structure.
Complex layouts live in a lexical `{"type":"html"}` card. Never regenerate a page body to add
SEO data; use the page's `meta_description`, `og_*`, `twitter_*` fields instead.
