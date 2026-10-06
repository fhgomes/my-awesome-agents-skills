---
name: ghost-blog-ops
description: >-
  Run, maintain and evolve a self-hosted Ghost CMS blog end to end: theme
  development and deployment (Handlebars templates, gscan, zip naming trap,
  custom settings and their TWO database tables, cache verification), Admin API
  operations from behind Cloudflare (stdlib JWT, localhost + Host header,
  create/update posts and pages with ?source=html, partial PUT with updated_at
  as optimistic lock, theme upload, tier welcome page), what the API cannot do
  and the MySQL fallbacks (navigation, settings, custom_theme_settings,
  post_revisions recovery), custom pages and landing pages (custom_template,
  hand-edited HTML cards, safe-edit protocol), lead magnets on native Ghost
  Members (signup label per slug, members-only delivery page, single global
  welcome page and the Library pattern, instant vs manual delivery), internal
  tags as per-page feature flags, a PT/EN UI toggle, the draft-only review
  loop with inline // comments, and the QA rules (verify the served HTML, not
  the DB or the container). Use whenever the user asks to "fix the blog",
  "deploy the theme", "create a page/landing on Ghost", "the menu link is
  wrong", "add a custom setting", "post this on the blog", "edit the post via
  API", "set up a lead magnet", "the CSS didn't change", or anything about
  operating a Ghost site. For bootstrap/2FA login scripts and a full API
  client see the optional openclaw/ghost tools. Also triggers on the
  equivalent phrases in other languages.
---

# Ghost blog operations (self-hosted)

You own the whole blog: theme, pages, posts, settings, and the database
behind them. Most wasted sessions come from editing the wrong layer, so start
with the map.

## 0. Where each thing lives (read before touching anything)

| Thing | Lives in | Changed by |
|---|---|---|
| Templates, CSS, JS, `package.json` | the theme folder (your theme repo) | edit + deploy (section 2) |
| Menu / navigation links | `settings.navigation` in the DB | Admin UI, or MySQL (section 4). **Not the theme.** |
| Theme custom settings (`@custom.*`) | `settings` (`group=theme`) AND `custom_theme_settings` | Admin → Design, or BOTH tables in MySQL |
| Post and page bodies | `posts` table (lexical + html) | Ghost editor, or Admin API `?source=html` |
| Which template a page uses | `posts.custom_template` | Admin page settings, or a partial PUT |
| Members-only gating | `posts.visibility` | same |
| Free-tier welcome page | `tiers.welcome_page_url` | Admin → Membership, or `PUT /tiers/<id>/` |
| Active theme name | `settings.active_theme` | Admin → Design, or `POST /themes/upload/` |

Real case: a NEWSLETTER menu item pointed at a 404 for two sessions while
the template and the page were fixed twice, because the link is a row in the
database, not a file. `gscan` reports the theme as valid while a nav item
404s.

Machine facts (container names, paths, domain, key location) belong in the
agent's memory for that server, not in this skill. Use `GHOST_URL`,
`GHOST_ADMIN_API_KEY`, `GHOST_LOCAL_URL` and `GHOST_ENV_FILE` environment
variables; never hardcode them.

## 1. Admin API: the recipe that works

Full detail in `references/admin-api.md`. The five rules:

1. **Key**: `GHOST_ADMIN_API_KEY=id:hex_secret` (Admin → Integrations → Custom).
   Keep it in a `.env` outside the repo. A key pasted in a notes file is a
   leaked key: rotate it.
2. **JWT HS256 with the standard library**, `kid=id`, `aud=/admin/`, exp 5 min.
   Generate a fresh token per call. `scripts/ghost_admin.py` does it.
3. **Behind Cloudflare, call localhost**: `http://127.0.0.1:2368` with headers
   `Host: <your-domain>` and `X-Forwarded-Proto: https`. The public URL
   returns Cloudflare error 1010; without the headers Ghost 302s to the
   canonical URL, which goes back to Cloudflare.
4. **HTML in, HTML out**: create/update with `?source=html`, read with
   `?formats=html,lexical`. Sending `html` without `?source=html` is
   interpreted as lexical and destroys the content.
5. **`updated_at` is the optimistic lock.** GET immediately before every PUT
   and send the fresh `updated_at`; a stale one returns 409. A partial PUT
   (only the field you change plus `updated_at`) is safe on hand-edited pages.

What the integration token can and cannot do:

| Works | Does not work (session/owner only) |
|---|---|
| Posts, pages, tags: full CRUD, `custom_template`, `visibility`, `custom_excerpt` | `PUT /settings/` (Ghost 5: 501 NotImplemented; Ghost 6: 403 NoPermission) |
| `POST /themes/upload/` (overwrites and keeps active if the name matches) | `GET /themes/`, `DELETE /themes/<name>/` (403) |
| `PUT /tiers/<id>/` incl. `welcome_page_url` | `PUT /users/<id>/` |
| `GET /settings/`, `GET /users/me/`, images upload, members, newsletters, webhooks | Portal, email, labs, integrations, staff |

Do not burn a session retrying a wall that is documented: go to MySQL or the
Admin UI.

```bash
# read a page with both formats (backup before any edit)
python scripts/ghost_admin.py get "pages/?filter=slug:my-landing&formats=html,lexical" > backup.json
# create a draft post from an HTML file
python scripts/ghost_admin.py post-html posts --title "Title" --html-file post.html --tags "tag-a,tag-b" --status draft
# change ONE field on an existing page (partial PUT with fresh updated_at)
python scripts/ghost_admin.py put-partial pages <id> --json '{"custom_template":"custom-landing"}'
# deploy a theme zip (the zip file name IS the theme name)
python scripts/ghost_admin.py theme-upload my-theme.zip
```

## 2. Theme development and deployment

Detail in `references/theme-development.md`.

- Validate the folder with `npx gscan <theme>/` and the zip with
  `npx gscan -z <theme>.zip` (the `-z` flag is mandatory for zips).
- **The zip file name becomes the theme name**, not `package.json`. Uploading
  `theme-upload.zip` creates a new, inactive theme called `theme-upload`: a
  silent no-op on the site plus garbage the token cannot delete. Name the zip
  exactly like the active theme. `scripts/theme_package.sh` does it and
  refuses a wrong name.
- `zip -r` appends to an existing archive; `rm -f` the old zip first.
- Deploy either with `POST /themes/upload/` (immediate, keeps active) or by
  copying into the theme volume plus a container restart (`.hbs` changes need
  the restart; CSS does not, but the restart also clears the version hash).
- **Verify on the served URL, never on the container copy**:
  `curl -s "$GHOST_URL/assets/css/screen.css?v=<hash>" | grep ".hero {"`.
  Browsers cache the old CSS: hard reload.
- Confirm which theme is active before editing files:
  `SELECT value FROM settings WHERE \`key\`='active_theme'`. An old folder
  with a similar name is the classic wrong target.
- Ghost's Handlebars has **no `eq` helper** (`Missing helper: "eq"`). For
  per-tag icons use the slug as a CSS class:
  `<span class="tag-icon tag-icon-{{primary_tag.slug}}"></span>` and style
  each class with `mask-image`.
- **Internal tags are per-page feature flags.** Ghost puts `tag-hash-<name>`
  in `body_class` and the `{{#has tag="#name"}}` helper sees internal tags
  (the `{{tags}}` helper filters them out). A `#focus` tag can hide the site
  chrome with CSS alone: no template, no redeploy, reversible by removing the
  tag. Never hide the brand anchor (top status bar) and never stack such a
  flag on a landing that already manages its own chrome.
- Custom settings added to `package.json` are not picked up by a restart.
  They must exist in `settings` (`group=theme`, 24-char hex id) **and** in
  `custom_theme_settings` (what Handlebars reads at runtime). Update both,
  then restart. `@custom.*` is global to the theme, never per page.
- Run the E2E suite (Playwright) before committing a theme change; keep the
  nav constants in the tests equal to the real menu.

## 3. Pages, landings and lead magnets

Detail in `references/lead-magnets.md`.

- A page can use a **custom template** (`custom-<name>.hbs`, set via
  `custom_template`) or be a **self-contained HTML card** on the default page
  template. The card wins when the copy is hand-edited: it survives theme
  redeploys and needs no template per landing.
- **Hand-edited HTML card pages are the source of truth for their copy.** Do
  not regenerate them. Adjust = edit the existing HTML. Safe-edit protocol:
  backup `?formats=html,lexical`, partial PUT with `?source=html`, then
  `md5sum` of the html before/after to prove the copy did not change when you
  only touched metadata.
- Lead magnet on native Members, no third party: public landing with a
  signup form carrying `<input data-members-label hidden value="lead:<slug>">`
  → confirmation email (double opt-in) → free-tier welcome page → members-only
  delivery page with the links. The label segments members by origin.
- **One welcome page per site**, confirmed in Ghost source: the signup
  handler returns the tier welcome page before reading any referrer, and the
  portal form never sends a redirect. Pattern that scales: a single
  members-only **Library** page listing every resource; each new magnet adds a
  section. Everyone who enters through any magnet gets everything.
- Two delivery modes, switched by an internal tag on the landing
  (`#request-access`): **instant** (link lives on the delivery page) vs
  **manual** (you grant access by hand, 24 h SLA in the copy). Never use the
  instant copy for a manual resource: promising a link that does not arrive
  burns a senior audience.
- Page slots: Title = H1 (artifact + action), Body = one code block for the
  product sample then prose, Custom excerpt = sticky bar summary, Slug = label
  suffix and eyebrow argument, internal tag = mode.
- Copy rules that held up: the CTA is verb + artifact ("Send me the download
  link"), the form says which e-mail and what arrives, an "offered-by" line is
  the only authority claim (name + site), never a client or brand name as a
  credential, no cheesy taglines.
- The end-to-end signup test creates a real member and sends a real e-mail:
  run it in a private window with your own address and then check the label
  in Admin → Members.

## 4. When the API says no: MySQL

Detail in `references/admin-api.md`, section "MySQL fallbacks".

- `key` is reserved in MySQL 8: always `` `key` ``.
- Pipe SQL through stdin (`docker exec -i ... mysql ... < file.sql`) instead
  of `-e` to avoid quote nesting; `SELECT` the row first as a backup, `UPDATE`,
  then `SELECT ROW_COUNT()`.
- Settings are cached in memory: restart the container after the write
  (~12–25 s), then verify on the served HTML.
- Navigation: `UPDATE settings SET value='<json>', updated_at=NOW() WHERE
  \`key\`='navigation'`.
- Lost a manual edit? `post_revisions` keeps the editor history: compare
  before overwriting anything.

## 5. Content workflow (drafts, review loop, voice)

Detail in `references/content-workflow.md`.

1. The agent creates posts as `draft`, never publishes. Publishing is the
   owner's click.
2. The owner edits in the Ghost editor and leaves comments as paragraphs
   starting with `//`.
3. Fetch the current HTML via the API, read the `//` lines (intent over
   letter), rewrite the whole article respecting the owner's own edits, PUT it
   back without the `//` lines. Repeat until published.
4. **The canonical text is the one in Ghost**, not the draft file. After
   publication record URL, post id and date wherever the pipeline keeps its
   notes.
5. If `updated_at` moved without your PUT, the editor is open and
   autosaving. Do not overwrite; re-fetch and merge.

Voice rules that apply to any technical blog with a senior audience: no
em-dashes (they read as machine text; rewrite the sentence), contractions in
conversational passages, solution-first structure, concrete numbers from a
verified "ground truth" block that agents may not round, honest "still
pending" items, direct links in CTAs, and no claims the author cannot back
with an artifact.

## 6. PT/EN UI toggle (or any second language)

Default is one language; a `.lang-toggle` button switches and persists in
`localStorage`. Elements carry `data-i18n="key"` (and
`data-i18n-placeholder`); a global dictionary covers shared UI, each custom
page adds `window.PAGE_I18N = { pt: {...} }` inline. The default language is
restored from the original markup captured on first apply, so only the
second language needs a dictionary. Brand terms get `translate="no"` and stay
identical in both languages. Editor content stays in the language it was
written in; the toggle covers UI and hardcoded copy only. Pages living as
HTML cards must carry their own `data-i18n` + `PAGE_I18N` and future card
edits must preserve them.

## 7. QA and delivery checklist

- [ ] Verified on the served page (`curl` or browser hard reload), not on the
      DB row or the container file.
- [ ] `gscan` clean for the folder and for the zip; zip named as the active
      theme.
- [ ] Nav links click through (they are data, not templates).
- [ ] Custom settings present in both tables; container restarted.
- [ ] Hand-edited card pages: md5 unchanged unless the copy was the task.
- [ ] Drafts only; the owner publishes.
- [ ] E2E suite green; mobile project uses Chromium when WebKit cannot run
      on the host.
- [ ] Screenshots for visual checks use a tall viewport or `fullPage: true`
      (Playwright `clip` fails when `y + height` exceeds the viewport).
