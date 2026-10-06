# ghost-blog-ops

Run, maintain and evolve a self-hosted Ghost CMS blog from the command line: theme, pages, posts, settings and the database behind them.

## Purpose

Everything learned operating a production Ghost blog with an AI agent, written as procedures that work on any Ghost 5/6 install. It leads with the map of *where each thing lives* (theme files vs database rows vs editor content), because most wasted sessions come from editing the wrong layer.

## Features

- **Admin API recipe** — stdlib JWT, calling localhost behind Cloudflare with `Host` + `X-Forwarded-Proto`, `?source=html` in and `?formats=html,lexical` out, `updated_at` as the optimistic lock, partial PUTs, theme upload, tier welcome page; and the documented walls (settings, users, theme delete) so nobody retries them
- **Theme development** — gscan for folder and zip, the zip-name-is-the-theme-name trap, deploy via API or volume + restart, verify on the served URL, the two custom-settings tables, no `eq` helper, internal tags as per-page feature flags, PT/EN toggle pattern
- **Pages and lead magnets** — custom templates vs hand-edited HTML cards, safe-edit protocol with md5 proof, native Members lead-magnet flow, the single-welcome-page limitation (verified in Ghost source) and the Library pattern, instant vs manual delivery modes, copy rules
- **MySQL fallbacks** — navigation, settings, custom_theme_settings, post_revisions recovery, with the reserved-word and stdin-pipe gotchas
- **Content workflow** — draft-only, the `//` review loop in the editor, canonical text lives in Ghost, voice rules for a senior audience
- **Scripts** — `scripts/ghost_admin.py` (stdlib-only: get, post-html, put-partial, theme-upload, backup) and `scripts/theme_package.sh` (gscan + correctly named zip)

## Quick Start

```bash
export GHOST_URL=https://blog.example.com
export GHOST_ADMIN_API_KEY=id:hex_secret          # or GHOST_ENV_FILE=/path/to/.env
export GHOST_LOCAL_URL=http://127.0.0.1:2368      # only when calling from the host behind Cloudflare

python scripts/ghost_admin.py get "posts/?limit=3&fields=id,title,status"
python scripts/ghost_admin.py post-html posts --title "Hello" --html-file post.html --status draft
bash scripts/theme_package.sh my-theme            # gscan + my-theme.zip
python scripts/ghost_admin.py theme-upload my-theme.zip
```

## See Also

- [SKILL.md](SKILL.md) — the full procedure and checklists
- [references/admin-api.md](references/admin-api.md), [theme-development.md](references/theme-development.md), [lead-magnets.md](references/lead-magnets.md), [content-workflow.md](references/content-workflow.md)
- [openclaw/ghost](../../openclaw/ghost/) — optional companion: first-login/2FA bootstrap, a Node API client and a content pipeline
