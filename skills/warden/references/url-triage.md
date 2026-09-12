# URL, Domain and Phishing Triage

## Browsing rule

- **Never** open a suspicious URL in the user's real browser (e.g. `mcp__claude-in-chrome__*`).
  Session cookies, saved passwords and the logged-in profile get exposed, and a drive-by
  download lands straight on the machine.
- If rendering is truly necessary, use an isolated browser (e.g. `mcp__Claude_Browser__*`),
  separate from the real profile.
- Always prefer: inspect over HTTP without rendering.
- **Never** pipe a response into a shell (`curl ... | bash`), nor download and execute.

---

## Step 1 — Decompose the URL before touching it

```
https://login.microsoft.com.secure-verify[.]ru/auth?redirect=...
        └────── lure ──────┘└─ real domain ─┘
```

The real domain is always what comes **immediately before the TLD**. Everything to the left
is a subdomain and can say anything.

Check:
- Real registrable domain (eTLD+1) vs. claimed brand
- Homoglyphs and typosquatting: `rnicrosoft` (rn≈m), `goog1e`, `paypaI` (capital I),
  `arnazon`, punycode `xn--`
- TLD mimicking a file extension: `.zip`, `.mov`
- High-abuse TLD combined with a known brand: `.ru`, `.cn`, `.tk`, `.xyz`, `.top`, `.icu`
- Generic hosting domain serving a brand: `*.web.app`, `*.pages.dev`, `*.workers.dev`,
  `*.r2.dev`, `*.blob.core.windows.net`, `*.ngrok-free.app`, `*.duckdns.org`
- Embedded credential: `https://apple.com@evil.ru/` — the host is `evil.ru`
- Non-standard port (`:8080`, `:4444`) on a link claiming to be a bank/company
- Bare IP instead of a domain
- URL shortener (`bit.ly`, `t.co`, `is.gd`, `cutt.ly`, `tinyurl`) hiding the destination

---

## Step 2 — Headers and redirect chain (without downloading the body)

```bash
curl -sSIL --max-time 15 -A 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)' 'URL' \
  | grep -iE '^HTTP/|^location:|^content-type:|^content-disposition:|^content-length:|^server:'
```

Read:
- Each `Location:` in the chain — where the link really leads
- `Content-Type: application/octet-stream` or `application/x-msdownload` on a "page link"
- `Content-Disposition: attachment; filename=...` — it is a download, not a page
- Redirect that changes domain two or more times before landing on an unknown host
- Cloaking: different response for a bot User-Agent vs. a browser (compare both)

```bash
# compare behavior by User-Agent (cloaking signal)
curl -sSI --max-time 10 -A 'curl/8' 'URL' | head -1
curl -sSI --max-time 10 -A 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)' 'URL' | head -1
```

---

## Step 3 — Body as text, limited

```bash
curl -sS --max-time 20 --max-filesize 2000000 -A 'Mozilla/5.0' 'URL' > /tmp/page.html
file /tmp/page.html && wc -c /tmp/page.html
grep -oiE '<form[^>]*action="[^"]*"' /tmp/page.html | head
grep -oiE 'src="[^"]*"|href="[^"]*"' /tmp/page.html | sort -u | head -40
grep -icE 'atob\(|eval\(|fromCharCode|unescape\(|document\.write' /tmp/page.html
```

Red flags in the page:
- `<form action=` pointing to a domain different from the page's, with a `password` field
- Pixel-perfect login page of a known brand on a domain that is not the brand's
- Heavily obfuscated JS on a simple institutional site
- Invisible `<iframe>` loading a third-party domain
- Immediate meta refresh to another host
- Phishing kit: folder with `index.html` + `post.php` + the brand's logo

---

## Step 4 — Domain age and reputation

A domain registered a few days ago is the strongest single indicator of phishing.

```bash
whois domain.com 2>/dev/null | grep -iE 'creation|created|registrar|registrant|expiry'
```

(`whois` may not be available in every shell, e.g. Git Bash on Windows — in that case use
WSL/another host, or say you could not verify.)

```bash
nslookup domain.com
nslookup -type=MX domain.com     # phishing domains usually have no real MX
```

- Created in the last 30 days + imitates a brand = MALICIOUS with high confidence
- Privacy-protected registrar + new domain + certificate issued the same day = phishing kit
- A valid TLS certificate means **nothing**: Let's Encrypt is free and automatic.
  Padlock ≠ safe. Tell the user this if they mention "but it has the padlock".

---

## Step 5 — External lookup (with authorization)

Sending a hash/URL to an external service is an outward-facing action. **Ask first.**
- Submitting a URL to VirusTotal makes it public and may tip off the site's operator.
- Submitting a file publishes its content — never do it with a sample that may contain sensitive data.

Without an external lookup you can still deliver a solid verdict with steps 1-4 — just state
the scope ("local analysis, no external reputation lookup").

---

## Scam patterns by category

**Credential phishing** — cloned login page, form posting to another host,
urgency ("your account will be suspended in 24h"), new domain.

**Fake update / ClickFix** — page says the browser/Chrome/Flash needs an update, or
tells the user to paste a command into PowerShell/Win+R "to verify you are human".
**Any site asking you to paste a command into a terminal is an attack.** No exceptions.

**Fake CAPTCHA** — "prove you are human" followed by instructions to press Win+R and paste.
Same family as ClickFix.

**Fake tech support** — full-screen locked pop-up with a phone number and an audible alarm.
No real antivirus uses that format.

**Crypto/airdrop** — "connect your wallet to claim". Signing a `setApprovalForAll`
transaction drains the wallet. Never connect a wallet to an unverified site.

**Sextortion / e-mail quoting a leaked password** — the password came from an old public
breach. There is no infection. Do not pay. Change the password wherever it is still in use.

**Tampered invoice / bank transfer (e.g. boleto/PIX)** — attachment or link with bank details
different from the real vendor's. Always confirm through a separate channel, never via the
contact in the e-mail itself.

---

## URL verdict format

```
## Verdict
MALICIOUS — high confidence — scope: headers + static HTML, no JS rendering

## What it is
Phishing page cloning the <brand> login, hosted on a domain registered 4 days ago.

## Evidence
1. Real domain: secure-verify[.]ru (the brand only appears as a subdomain)
2. <form action="https://other-host[.]xyz/post.php"> with input type=password
3. Domain registration: 2026-08-25 (4 days)
4. Redirect chain: bit.ly → t[.]co → secure-verify[.]ru

## IoCs
- hxxps://login.microsoft.com.secure-verify[.]ru/auth
- other-host[.]xyz
- 203.0.113.44

## Immediate action
- Do not open. If already opened and a password was typed: change the password from ANOTHER
  device and sign out of all active sessions; enable MFA.
- Block the domain at DNS/firewall.

## Verification
- Confirm there is no unknown active session in the account's security panel.
```

Write malicious URLs and IPs **defanged** (`hxxp://`, `domain[.]com`) to avoid an
accidental click.
