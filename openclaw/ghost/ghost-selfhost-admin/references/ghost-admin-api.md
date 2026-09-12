# Ghost Admin API — Quick Reference

## Authentication

The Ghost Admin API uses JWT with an Admin API Key in the `id:secret` format.

```
Header: Authorization: Ghost {jwt_token}
Header: Accept-Version: v5.0
```

JWT payload: `{ iat, exp (5min), aud: "/admin/" }`
Signing: HMAC-SHA256 with `secret` (hex-decoded) as the key.

## Base URL

```
https://{ghost_url}/ghost/api/admin/
```

## Stable Endpoints (Documented)

### Site Info
- `GET /site/` — Basic info (title, version, URL). Not an array.

### Settings
- `GET /settings/` — All settings. Not an array.
- `PUT /settings/` — Update. Payload: `{ settings: [{ key, value }] }`

Known settings keys:
- `title`, `description`, `logo`, `icon` (favicon)
- `cover_image`, `meta_title`, `meta_description`
- `og_title`, `og_description`, `og_image`
- `twitter_title`, `twitter_description`, `twitter_image`
- `timezone`, `locale`, `accent_color`
- `navigation` (JSON stringified array)
- `secondary_navigation` (JSON stringified array)
- `codeinjection_head`, `codeinjection_foot`

### Posts
- `GET /posts/` — Browse (filter, limit, page, order, include, fields)
- `GET /posts/{id}/` — Read
- `GET /posts/slug/{slug}/` — Read by slug
- `POST /posts/` — Create. Payload: `{ posts: [{ title, html, status, ... }] }`
- `PUT /posts/{id}/` — Update (requires `updated_at` for conflict detection)
- `DELETE /posts/{id}/` — Delete

Post fields: title, slug, html, mobiledoc, lexical, status (draft/published/scheduled),
feature_image, featured, published_at, custom_excerpt, meta_title, meta_description,
og_title, og_description, og_image, twitter_title, twitter_description, twitter_image,
tags (array of objects), authors (array)

### Pages
- Same structure as Posts, endpoint `/pages/`

### Tags
- `GET /tags/` — Browse
- `GET /tags/{id}/` — Read
- `POST /tags/` — Create: `{ tags: [{ name, slug, description, ... }] }`
- `PUT /tags/{id}/` — Update
- `DELETE /tags/{id}/` — Delete

### Users
- `GET /users/` — Browse
- `GET /users/{id}/` — Read (include=roles)

### Members
- `GET /members/` — Browse
- `GET /members/{id}/` — Read
- `POST /members/` — Create
- `PUT /members/{id}/` — Update
- `DELETE /members/{id}/` — Delete

### Newsletters
- `GET /newsletters/` — Browse
- `POST /newsletters/` — Create
- `PUT /newsletters/{id}/` — Update

### Tiers
- `GET /tiers/` — Browse
- `PUT /tiers/{id}/` — Update

### Offers
- `GET /offers/` — Browse
- `GET /offers/{id}/` — Read
- `POST /offers/` — Create
- `PUT /offers/{id}/` — Update

### Images
- `POST /images/upload/` — Upload (multipart/form-data, field "file")
- Response: `{ images: [{ url, ref }] }`
- Accepted formats: jpg, jpeg, png, gif, svg, webp, ico

### Themes
- `GET /themes/` — List (includes the `active: true` field)
- `POST /themes/upload/` — Upload zip
- `PUT /themes/{name}/activate/` — Activate

### Webhooks
- `GET /webhooks/` — Browse (via integration)
- `POST /webhooks/` — Create
- `PUT /webhooks/{id}/` — Update
- `DELETE /webhooks/{id}/` — Delete

Webhook events: post.added, post.deleted, post.edited, post.published, post.unpublished,
page.added, page.deleted, page.edited, page.published, page.unpublished,
member.added, member.deleted, member.edited, tag.added, tag.deleted, tag.edited

## UNDOCUMENTED Endpoints (discovered via the Ghost Admin UI)

These endpoints exist but have no stable documentation.
Use with care — they may change between versions:

- `PUT /settings/` with design keys (accent_color, etc.)
- `/custom_theme_settings/` — Theme custom settings
- `/labels/` — Member labels
- `/snippets/` — Reusable content snippets
- `/integrations/` — Custom integrations CRUD
- `/invites/` — Staff invites

## Filters (NQL — Ghost Filter Language)

```
filter=status:published
filter=tag:getting-started
filter=status:published+tag:news
filter=published_at:>'2024-01-01'
filter=featured:true
```

Operators: `:` (equals), `-` (not), `>`, `<`, `>=`, `<=`, `~` (contains), `[in]`
Combination: `+` (AND), `,` (OR), `()` for grouping
