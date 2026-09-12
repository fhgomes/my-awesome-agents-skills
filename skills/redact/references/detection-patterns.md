# Detection Pattern Catalog

Each entry gives the format, why it matters, and the corresponding **false positive**.
The scanner (`scripts/scan_secrets.py`) already implements most of these; this reference
is for manual review and for interpreting the findings.

---

## Prefix-based secrets (high confidence)

These have a distinctive format and almost never produce false positives:

| Service | Format | Severity |
|---|---|---|
| AWS Access Key | `AKIA` / `ASIA` + 16 uppercase alphanumerics | critical |
| AWS Secret | 40 base64 chars next to `aws_secret_access_key` | critical |
| GitHub PAT (classic) | `ghp_` / `gho_` / `ghu_` / `ghs_` / `ghr_` + 36 | critical |
| GitHub PAT (fine-grained) | `github_pat_` + ~82 | critical |
| GitLab PAT | `glpat-` + 20 | critical |
| Slack | `xoxb-` / `xoxp-` / `xoxa-` / `xoxr-` / `xoxs-` | critical |
| Slack webhook | `https://hooks.slack.com/services/T.../B.../...` | high |
| Stripe live | `sk_live_` + 24+ | critical |
| Stripe test | `sk_test_` + 24+ | low (sandbox) |
| OpenAI | `sk-` or `sk-proj-` + 32+ | critical |
| Anthropic | `sk-ant-` + 20+ | critical |
| SendGrid | `SG.` + token + `.` + token | critical |
| Google API | `AIza` + 35 | high |
| Twilio | `SK` + 32 hex | high |
| npm | `//registry.npmjs.org/:_authToken=` | critical |

**Exception that matters:** `AKIAIOSFODNN7EXAMPLE` is the official example key from the
AWS documentation. It legitimately shows up in tutorials. It is still worth reporting
(it may be a copy-paste that became a real key), but with a note.

---

## Private keys and certificates

```
-----BEGIN RSA PRIVATE KEY-----
-----BEGIN OPENSSH PRIVATE KEY-----
-----BEGIN EC PRIVATE KEY-----
-----BEGIN PGP PRIVATE KEY BLOCK-----
-----BEGIN ENCRYPTED PRIVATE KEY-----
```

**False positive:** `-----BEGIN PUBLIC KEY-----` and `-----BEGIN CERTIFICATE-----` are
public by nature — not a leak. `ssh-rsa AAAA...` in `authorized_keys` or `.pub` is public too.

An **encrypted** private key is still a leak: the passphrase may be weak or sit
elsewhere in the repo.

---

## Connection strings

```
postgresql://user:password@host:5432/db
mysql://root:password@localhost/app
mongodb+srv://user:pass@cluster.mongodb.net
redis://:password@host:6379
amqp://user:pass@rabbit:5672
jdbc:postgresql://host:5432/db?user=app&password=secret
Server=x;Database=y;User Id=z;Password=secret;
DefaultEndpointsProtocol=https;AccountName=x;AccountKey=...
```

Also: any URL of the form `https://user:password@host`.

**False positive:** `postgresql://user:password@localhost` with literally the word
`password`, or an interpolated `${DB_PASSWORD}` — that is a template, not a secret.

---

## Generic hardcoded credential

The highest-volume pattern and the one with the most false positives:
```
password = "..."      senha: "..."       secret = '...'
api_key: "..."        token = "..."      client_secret = "..."
```

Filters the scanner applies before reporting:
- **Env var reference** → not a leak, it is the correct pattern:
  `process.env.X`, `os.environ[...]`, `System.getenv()`, `${VAR}`, `%VAR%`, `config.get(...)`
- **Placeholder** → `your-api-key`, `xxx`, `changeme`, `<INSERT>`, `example`, `dummy`, `TODO`
- **Low entropy** → `aaaaaaaa`, `11111111`, short dictionary word
- **Non-secret value** → `true`, `false`, `localhost`, `root`, `admin`, `null`
- **Test/doc path** → lowers the severity, but does not drop the finding

---

## Brazilian PII

| Data | Format | Validation |
|---|---|---|
| CPF (tax ID) | `999.999.999-99` or 11 digits | check digits (mod 11) |
| CNPJ (company ID) | `99.999.999/9999-99` | check digits |
| RG (identity card) | varies by state, 7-12 digits | no standard algorithm — needs the label |
| CNH (driver's license) | 11 digits | check digits |
| Voter registration | 12 digits | check digits |
| PIS/NIS (social security) | 11 digits | mod 11 |
| CEP (postal code) | `99999-999` | format only |
| Phone | `(99) 99999-9999` | format only |

The scanner validates CPF by check digit — this cuts false positives a lot, since a
random 11-digit sequence rarely passes.

**Common false positive:** `000.000.000-00` and `111.111.111-11` are invalid because of
repeated digits (the scanner already discards them). Faker-generated CPFs are statistically
valid and **will** show up — which is why path context matters: `tests/fixtures/` lowers
the severity, `customers.csv` in the root does not.

---

## PCI (card data)

Card number: 13-19 digits, **Luhn-validated**. Without Luhn, any long digit sequence
becomes a false positive.

Well-known gateway test cards (the scanner flags them with a note):
```
4242 4242 4242 4242   Stripe (4242 x4)
4111 1111 1111 1111   Visa test
5555 5555 5555 4444   Mastercard test
3782 822463 10005     Amex test
```

CVV (`cvv`, `cvc`, `security_code` + 3-4 digits) and an expiry date next to a card
number raise it to critical. **Storing CVV is forbidden by PCI-DSS**, even encrypted.

---

## PHI (health data)

No fixed format — depends on label and context:
- ICD-10 code (`A00` to `Z99`) associated with a person
- Medical record number
- Health-plan card number
- Exam result tied to a name/CPF
- Fields such as `diagnosis`, `medication`, `allergy`, `surgery` in a dataset with identifiers

PHI carries the heaviest regulatory weight. Any suspicion → treat as critical and
escalate for human review.

---

## Internal infra

| Pattern | Example |
|---|---|
| Private IP | `10.x.x.x`, `172.16-31.x.x`, `192.168.x.x` |
| Internal hostname | `db-prod.internal`, `srv01.local`, `app.corp` |
| Path revealing a username | `C:\Users\<name>\...`, `/home/<name>/...` |
| Private endpoint | admin URL, dashboard, `:8080/actuator`, `/phpmyadmin` |
| VPN / bastion | `.ovpn` config, jump host IP |

In isolation it is low-severity noise. **In aggregate**, it hands over the internal
network map — which is why the scanner reports it, even at medium/low level.

A path with a username is also mild PII: it exposes the real name of whoever developed it.

---

## Where personal data usually hides

Places a scan of `src/` alone does not reach:

- `tests/fixtures/`, `seeds/`, `mock/` — production dumps used as test data
- Sample `*.csv`, `*.xlsx`, `*.json` in the root
- `docs/` with screenshots showing real screen data
- Logs committed by accident (`app.log`, `debug.log`, `nohup.out`)
- Migrations with `INSERT`s of real data
- Code comments with customer data for debugging
- **Commit messages** (`git log --all --grep='cpf'`)
- **Issue/PR titles and bodies** — public together with the repo
- Wiki and releases
- `.har` network captures (contain headers with tokens and bodies with data)

---

## How to calibrate severity

Single question: **what does an attacker do with this in 5 minutes?**

- Live cloud key → creates resources, runs up costs, accesses data → **critical**
- GitHub write token → injects code, hijacks CI → **critical**
- PCI/PHI → regulatory and personal damage, irreversible → **critical**
- Production database password → full dump → **critical**
- Sandbox key → nothing beyond the test environment → **low**
- Isolated internal IP → needs another vector to be useful → **medium/low**
- The author's own e-mail in `package.json` → intentional → **do not report**
