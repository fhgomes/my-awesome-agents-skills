# Lead magnets on native Ghost Members

A landing page with a reward: the visitor subscribes, confirms the e-mail,
and the resource link arrives through Ghost's own magic link and lands on a
members-only delivery page. No Zapier, no external mailer.

## Flow

```
Landing page (public; custom template or HTML card)
  └─ signup form → member created with label "lead:<slug>"
       └─ Ghost sends the confirmation e-mail (double opt-in)
            └─ visitor clicks → e-mail confirmed
                 └─ redirect to the FREE TIER welcome page
                      └─ delivery page (members-only) with the links
```

The gate is real: the resource lives on a members-only page, so only
confirmed e-mails reach it. The label per slug lets you filter members by
origin in Admin → Members.

## One welcome page per site (verified in the Ghost source)

The free-tier welcome page is global. There is no per-magnet redirect:

1. `core/server/services/members/middleware.js`: on `action=signup` Ghost
   builds the redirect from the tier welcome page and returns right there; the
   referrer is only consulted in a later block that signup never reaches.
2. The portal script's `data-members-form` handler sends only
   `{email, emailType, labels, name, autoRedirect, urlHistory, newsletters}`.
   The API accepts a `redirect` field, but no `data-members-redirect`
   attribute exists, so a theme form cannot send it.

Strategies:

- **Library (recommended)**: one members-only page listing every resource;
  each new magnet adds a section. Anyone entering through any magnet gets
  everything, which raises the perceived value.
- **Per magnet**: separate delivery pages, each landing links its own
  members-only URL in the success notice; the post-confirmation redirect
  still goes to the global welcome page.
- **Advanced**: Ghost webhook → transactional e-mail per label, if true
  per-magnet delivery ever matters.

## Two delivery modes

Switched by an internal tag on the landing page (`#request-access`), read in
the template with `{{#has tag="#request-access"}}`:

| Mode | Tag | Copy | When |
|---|---|---|---|
| Instant (default) | none | eyebrow `>_ subscribe --get <slug>` · "Get the download link by e-mail" · CTA "Send me the download link →" | the resource is public (open repo, PDF); the link lives on the delivery page |
| Manual | `#request-access` | eyebrow `>_ request --access <slug>` · "Request access to my repository" · CTA "Request my invite →" · 24 h SLA | you grant access by hand (repository invite by e-mail address) |

Never use the instant copy for a manual resource. Promising an immediate link
that does not arrive burns trust with a senior audience. For manual mode,
GitHub accepts collaborator invites by e-mail address, so the captured e-mail
is enough; filter members by the label and invite in batch.

## Setting up a magnet (Admin UI, zero code once the templates exist)

1. **Delivery page first**: Pages → New. Title "You're in — here's your
   access", template `Thank You` (or the Library page), access
   *Members only*, body = the links plus a short "what's inside" list.
2. **Landing page**: Pages → New. Title = H1 (artifact + action, e.g.
   "Download my agents & skills library"), template `Lead Magnet`, access
   *Public*, slug = `<slug>` (becomes the label `lead:<slug>`), body = one
   code block with the product sample (`tree --depth 1` style, 1–2 value
   lines), then prose ("Who this is for"). Custom excerpt = the sticky bar
   summary, short, `·`-separated.
3. **Welcome page**: Settings → Membership → Free tier → Welcome page =
   the delivery/Library page. Also settable with
   `PUT /ghost/api/admin/tiers/<id>/` and `welcome_page_url`.
4. **Double opt-in**: confirm signups require e-mail confirmation (default on
   self-hosted with Mailgun/SMTP configured).
5. **Test** in a private window with your own e-mail: success state → e-mail
   → click → delivery page → label visible in Admin → Members. This creates a
   real member and sends a real e-mail; there is no dry run.

## Page slots (one rich field per page)

| Admin field | Becomes |
|---|---|
| Title | the H1; must name the artifact **and** the action |
| Body | first code block → rendered inside the terminal window; anything after it → prose below |
| Custom excerpt | the sticky CTA bar summary |
| Internal tag `#request-access` | manual delivery mode across all copy |
| Slug | eyebrow argument and label suffix |

`@custom.*` theme settings are global, not per page: they are not a slot.

## Landing anatomy that tested well ("engineering artifact page")

1. Eyebrow as a terminal command in mono/accent (`>_ request --access <slug>`).
2. Action-explicit H1, line-height ~1.18.
3. Terminal window with the product sample; no trailing "full source after
   signup" line (that is the form's job).
4. Light divider (short `hr`, minimal margins) so sample and ask read as one
   step.
5. Signup card: h3 directly, steps 1-2-3 compact inside the card with accent
   badges, privacy line, members form with the hidden label.
6. `offered-by: <Author> · <site>` — the **only** authority line.
7. Sticky CTA at the bottom (summary + anchor button to the form).
8. Floating light/dark toggle mirroring the theme's `body.dark-mode` +
   `localStorage`.

Chrome: the template hides the main nav, footer and post header with scoped
CSS and **keeps the top status bar** (brand anchor). Do not additionally
apply a `#focus` tag to such landings; a first version that also hid the
status bar cost two pages their header in production for two days.

## Copy rules that held up

- Artifact + action + mechanism: never "access" without an object; CTA =
  verb + artifact; the form states which e-mail and what arrives.
- Authority is the offered-by line. Never a client or a brand as a
  credential unless you were employed there; no cheesy taglines.
- English by default for a global technical audience; the toggle handles the
  second language.
- Hand-edited HTML card landings are the source of truth. Never regenerate
  them; adjust the existing HTML (safe-edit protocol in `admin-api.md`).
- Keep the previous version as an archived draft (`<slug>-a`) for rollback
  when a landing is redesigned.
