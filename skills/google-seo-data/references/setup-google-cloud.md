# One-time Google setup for `google-seo-data`

Everything here is done once, in a browser, by the site owner. After it the scripts need no
clicks. Budget: 15 minutes.

## 1. Which Google account

Use the account that should own the data long term. A **personal Gmail** is usually the
easier choice, because Google Workspace organizations frequently enforce the org policy
`iam.disableServiceAccountKeyCreation`, which blocks step 3. Search Console properties and
GA4 properties accept multiple owners/users, so another account can be added later without
losing anything.

## 2. Cloud project and APIs

1. https://console.cloud.google.com > New project. One project can serve every site the
   user owns; name it after the person or company, not the site.
2. APIs & Services > Library. Enable:
   - Google Search Console API
   - Site Verification API
   - Google Analytics Admin API
   - Google Analytics Data API

Skipping one shows up later as `HttpError 403 ... SERVICE_DISABLED` with the activation
URL in the message.

## 3. Service account and key

1. IAM & Admin > Service Accounts > Create. Name like `seo-reader`. **Grant no role.**
2. Open the account > Keys > Add key > JSON. A file downloads.
3. Move it to the machine that runs the scripts, outside every git repository:
   ```bash
   mkdir -p ~/.config/google-seo && mv ~/Downloads/*.json ~/.config/google-seo/sa.json
   chmod 600 ~/.config/google-seo/sa.json
   ```
4. Note the `client_email` inside the file (`...@<project>.iam.gserviceaccount.com`).

## 4. Search Console

Nothing to click. `gsc.py token` + putting the code on the site + `gsc.py verify` makes the
service account a verified owner, and `gsc.py add` lists the property. To see it in the
owner's own Search Console UI, run `gsc.py owner their@email` when they ask.

### URL-prefix vs domain property

| | URL-prefix (`https://blog.example.com/`) | Domain (`sc-domain:example.com`) |
|---|---|---|
| Verification | `<meta name="google-site-verification">` | DNS TXT at the apex |
| Covers | exactly that origin | every subdomain, http and https |
| Needs | ability to edit the site's `<head>` | access to DNS |
| Sitemap | `gsc.py sitemap` (default path) | `gsc.py sitemap https://host/sitemap.xml` (full URL) |

Start with URL-prefix if DNS is not at hand; add the domain property later. Data is not
lost, both properties keep reporting.

## 5. GA4

1. https://analytics.google.com > Admin > Create property (one property per product with
   its own audience; a blog and the app it funnels into on subdomains of the same domain
   belong in **one** property, since subdomains share the `_ga` cookie).
2. Data streams > Web > the site URL. Copy the **Measurement ID** (`G-XXXXXXXXXX`) for the
   site's tag.
3. Admin > Property access management > Add users > paste the service account
   `client_email`, role **Viewer**. That is all `ga4.py` needs.
4. `ga4.py props` prints the numeric property id; export it as `GA4_PROPERTY`.

## 6. Bing (optional, two minutes)

https://www.bing.com/webmasters > "Import from Google Search Console" with the same Google
account. Bing's index also feeds Copilot and ChatGPT search.

## Rotation and revocation

- Rotate the key: Service Accounts > Keys > delete the old one, add a new JSON, replace the
  file. Ownerships and property access follow the account email, not the key.
- Revoke everything: delete the service account. Remove it from Search Console owners and
  GA4 users too, since those lists keep stale emails.
