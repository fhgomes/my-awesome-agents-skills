# Ghost Admin API — Referência Rápida

## Autenticação

Ghost Admin API usa JWT com Admin API Key no formato `id:secret`.

```
Header: Authorization: Ghost {jwt_token}
Header: Accept-Version: v5.0
```

JWT payload: `{ iat, exp (5min), aud: "/admin/" }`
Signing: HMAC-SHA256 com `secret` (hex-decoded) como chave.

## Base URL

```
https://{ghost_url}/ghost/api/admin/
```

## Endpoints Estáveis (Documentados)

### Site Info
- `GET /site/` — Info básica (título, versão, URL). Não é array.

### Settings
- `GET /settings/` — Todas as configurações. Não é array.
- `PUT /settings/` — Atualizar. Payload: `{ settings: [{ key, value }] }`

Chaves conhecidas de settings:
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
- `PUT /posts/{id}/` — Update (requer `updated_at` para conflict detection)
- `DELETE /posts/{id}/` — Delete

Campos do post: title, slug, html, mobiledoc, lexical, status (draft/published/scheduled),
feature_image, featured, published_at, custom_excerpt, meta_title, meta_description,
og_title, og_description, og_image, twitter_title, twitter_description, twitter_image,
tags (array de objetos), authors (array)

### Pages
- Mesma estrutura que Posts, endpoint `/pages/`

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
- `POST /images/upload/` — Upload (multipart/form-data, campo "file")
- Resposta: `{ images: [{ url, ref }] }`
- Formatos aceitos: jpg, jpeg, png, gif, svg, webp, ico

### Themes
- `GET /themes/` — Listar (inclui campo `active: true`)
- `POST /themes/upload/` — Upload zip
- `PUT /themes/{name}/activate/` — Ativar

### Webhooks
- `GET /webhooks/` — Browse (via integração)
- `POST /webhooks/` — Create
- `PUT /webhooks/{id}/` — Update
- `DELETE /webhooks/{id}/` — Delete

Eventos de webhook: post.added, post.deleted, post.edited, post.published, post.unpublished,
page.added, page.deleted, page.edited, page.published, page.unpublished,
member.added, member.deleted, member.edited, tag.added, tag.deleted, tag.edited

## Endpoints NÃO documentados (descobertos via Ghost Admin UI)

Estes endpoints existem mas não têm documentação estável.
Use com cuidado — podem mudar entre versões:

- `PUT /settings/` com chaves de design (accent_color, etc.)
- `/custom_theme_settings/` — Theme custom settings
- `/labels/` — Member labels
- `/snippets/` — Reusable content snippets
- `/integrations/` — Custom integrations CRUD
- `/invites/` — Staff invites

## Filtros (NQL — Ghost Filter Language)

```
filter=status:published
filter=tag:getting-started
filter=status:published+tag:news
filter=published_at:>'2024-01-01'
filter=featured:true
```

Operadores: `:` (equals), `-` (not), `>`, `<`, `>=`, `<=`, `~` (contains), `[in]`
Combinação: `+` (AND), `,` (OR), `()` para agrupamento
