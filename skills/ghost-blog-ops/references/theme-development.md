# Theme development and deployment

## Theme layout

```
my-theme/
  package.json        # name, engines.ghost, posts_per_page, config.custom
  default.hbs         # shell: <head>, nav, status bar, footer
  index.hbs           # home: feed + sidebar
  post.hbs / page.hbs / author.hbs / tag.hbs / error.hbs
  custom-<name>.hbs   # selectable per page via custom_template (e.g. custom-landing.hbs)
  assets/css/screen.css
  assets/js/main.js
```

Content comes from Ghost variables (`{{@site.*}}`, `{{@custom.*}}`,
`{{#get}}`), never hardcoded in templates. Keep the visual identity (fonts,
palette, spacing, component specs) in a `reference/guideline.md` next to the
theme and consult it before touching styles.

## Validate

```bash
npx gscan my-theme/          # folder
npx gscan -z my-theme.zip    # zip: the -z flag is mandatory, without it gscan fails
```

`gscan` validates templates only. It does not see the navigation (a DB row)
or the custom settings rows. A green gscan with a 404 in the menu is normal.

## Package and deploy

```bash
rm -f my-theme.zip                                   # zip -r APPENDS to an existing archive
(cd my-theme && zip -r ../my-theme.zip . -x "node_modules/*")
npx gscan -z my-theme.zip
python scripts/ghost_admin.py theme-upload my-theme.zip   # or Admin → Design → Themes
```

`scripts/theme_package.sh <theme-folder>` runs exactly this and refuses to
produce a zip whose name differs from the folder.

**The zip file name becomes the theme name**, not the `name` in
`package.json`. `theme-upload.zip` creates a new inactive theme called
`theme-upload`, the site does not change, and the integration token cannot
delete the leftover (403): manual cleanup in the Admin UI.

Alternative deploy (volume copy):

```bash
cp -r my-theme/. /path/to/ghost/data/themes/my-theme/
docker restart ghost-blog && sleep 20    # .hbs changes need it; CSS-only does not, but it clears the version hash
```

Sync back after any direct container edit:

```bash
docker cp ghost-blog:/var/lib/ghost/content/themes/my-theme/assets/css/screen.css my-theme/assets/css/screen.css
diff <(docker exec ghost-blog cat /var/lib/ghost/content/themes/my-theme/assets/css/screen.css) my-theme/assets/css/screen.css && echo in-sync
```

Confirm the target before editing files: the active theme is
`SELECT value FROM settings WHERE \`key\`='active_theme'`. An older folder
with a near-identical name (`my-theme-theme`, `my-theme-old`) is the classic
wrong target and everything looks deployed while nothing changes.

## Cache: verify on the served response

- Ghost appends `?v=<hash>` to asset URLs; browsers still serve the old file.
  Hard reload (Ctrl+Shift+R) or check with curl:
  `curl -s "$GHOST_URL/assets/css/screen.css?v=<hash>" | grep ".hero {"`.
- A container restart forces Ghost to re-read theme files and regenerates the
  hash.

## Custom settings (`@custom.*`)

Declare in `package.json`:

```json
{ "config": { "custom": {
  "hero_title":   { "type": "text", "default": "Systems that scale." },
  "github_url":   { "type": "text", "default": "" },
  "apply_url":    { "type": "text", "default": "https://example.com/apply" }
}}}
```

Use as `{{@custom.hero_title}}`; guard with `{{#if @custom.github_url}}`.

Gotchas:

- A new key is **not** picked up by a restart. Ghost needs a row in
  `settings` (`group_name='theme'`, 24-char hex `id`) and the runtime value in
  `custom_theme_settings`. Update **both** tables when writing via MySQL, then
  restart. Admin → Design writes both for you.
- `@custom.*` is **global to the theme**, not per page. It is not a slot for
  per-landing copy.
- Good use: URLs that change with the environment (an application form on a
  staging host today, production tomorrow) so the switch is an Admin edit, not
  a redeploy.

## Handlebars gotchas

- **No `eq` helper**: `{{#if (eq a b)}}` throws `Missing helper: "eq"`.
  Per-tag icons without logic: `<span class="tag-icon tag-icon-{{primary_tag.slug}}"></span>`
  and one CSS rule per slug using `mask-image: url("data:image/svg+xml,...")`.
- `{{#has tag="#internal"}}` sees internal tags (it reads the raw tag list);
  `{{tags}}` applies the visibility filter and hides them. That is why an
  internal tag can be a per-page feature flag invisible to readers.
- Ghost puts `tag-hash-<name>` in `body_class` for internal tags, so CSS alone
  can react to them: a `#focus` tag that hides nav, search and footer columns
  (keep the brand anchor and the dark-mode toggle) without a template or a
  redeploy.
- Navigation renders from `{{#foreach @site.navigation}}` / `{{navigation}}`;
  the data is `settings.navigation`.
- Members form works in any template or HTML card: `<form data-members-form="signup">`,
  `<input data-members-email type="email" required>`,
  `<input data-members-label type="hidden" value="lead:{{slug}}">`. Ghost adds
  `loading` / `success` / `error` classes to the form; CSS shows the notices.

## CSS / layout notes that saved time

- Three equal footer columns: `display:grid; grid-template-columns:1fr 1fr 1fr`
  (`justify-content: space-between` on flex misbehaves with auto widths).
- Breakpoints that worked for an editorial layout: 900 px (tablet), 768 px,
  600 px (mobile).
- Dark mode: `body.dark-mode` class, persisted in `localStorage`, system
  preference detected on first load.

## Second-language UI toggle

- One default language; a `.lang-toggle` in the nav (and a floating one on
  landings that hide the nav) switches and persists `localStorage.lang`.
- Markup: `data-i18n="key"` for innerHTML, `data-i18n-placeholder="key"` for
  inputs. A global dictionary for shared UI, `window.PAGE_I18N = { pt: {...} }`
  inline per custom page or HTML card.
- The default language is restored from the original markup captured on first
  apply, so only the second language needs entries.
- Server-rendered strings (reading time) are patched by text replacement.
- Brand terms (site name, section names, tag names, status bar) never
  translate and get `translate="no"` against browser auto-translate.
- Editor content (titles, bodies) stays in its written language; the toggle
  covers UI and hardcoded copy only. HTML-card pages carry their own
  `data-i18n` and `PAGE_I18N`; card edits must preserve them.

## Tests before committing

Keep a Playwright E2E suite next to the theme (nav links, dark mode, members
form states, landing pages, mobile). Notes that bit:

- WebKit may not install on a new distro (missing `libicu`/`libxml2`): move
  the mobile project to a Chromium device profile.
- `page.screenshot({ clip })` fails when `y + height` exceeds the viewport:
  use a tall viewport or `fullPage: true`.
- Update the nav constants in the tests whenever the real menu changes.
- `git hash-object -w` + `git update-index --cacheinfo` commits a file
  generated in `/tmp` without touching the working tree; always finish with a
  sync back so the working tree matches.
