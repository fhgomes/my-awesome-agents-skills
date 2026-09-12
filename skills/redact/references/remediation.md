# Remediation — Getting the Secret Out of the Code

Order that never changes: **rotate → externalize → clean history → prevent.**

Rotate first because, as long as the old key is valid, everything else is cosmetic.

---

## 1. Rotate (before any commit)

| Service | Where to revoke/rotate |
|---|---|
| AWS | IAM → Users → Security credentials → deactivate and create a new access key |
| GCP | IAM → Service Accounts → Keys → delete and generate a new one |
| Azure | Storage account → Access keys → Rotate; App registrations → Certificates & secrets |
| GitHub | Settings → Developer settings → PAT → Revoke; plus the repo's Deploy keys |
| GitLab | Settings → Access Tokens → Revoke |
| Stripe | Developers → API keys → Roll key (the old one stops immediately) |
| OpenAI / Anthropic | API keys dashboard → revoke and create a new one |
| Slack | App config → OAuth & Permissions → Revoke / Regenerate |
| SendGrid / Twilio | API keys → delete + create |
| Database | `ALTER USER app_user WITH PASSWORD '...'` and update every consumer |
| SSH key | Generate a new pair, swap it in `authorized_keys`, remove the old one |
| JWT signing secret | Change the secret — invalidates every issued token, plan the cutover |

After rotating, **check the old key's usage** (CloudTrail, the provider's access logs).
Usage from an unknown IP = it was already exploited, it becomes an incident.

---

## 2. Externalize per stack

### Spring Boot

`application.properties`:
```properties
# WRONG
spring.datasource.password=RealPassword123

# RIGHT — required, boot fails if missing
spring.datasource.password=${DB_PASSWORD}

# RIGHT — with a default only for local dev (never use a default in prod)
spring.datasource.password=${DB_PASSWORD:dev-only-local}
```

`application.yml`:
```yaml
spring:
  datasource:
    url: ${DB_URL}
    username: ${DB_USER}
    password: ${DB_PASSWORD}
```

Supplying the values:
```bash
export DB_PASSWORD='...'
java -jar app.jar

# or by argument (shows up in `ps` — avoid on shared machines)
java -jar app.jar --spring.datasource.password="$DB_PASSWORD"

# or a separate profile, with the file kept out of git
java -jar app.jar --spring.profiles.active=prod
```

`application-prod.properties` must be in `.gitignore`. Version
`application-prod.properties.example` with the keys left empty.

### Node

```js
// WRONG
const stripe = require('stripe')('sk_live_51H8xQz...');

// RIGHT
const key = process.env.STRIPE_KEY;
if (!key) throw new Error('STRIPE_KEY is not set');
const stripe = require('stripe')(key);
```

With dotenv in development (never in production — there the vars come from the orchestrator):
```js
if (process.env.NODE_ENV !== 'production') require('dotenv').config();
```

### Python

```python
import os

# required — fails loudly and early
DB_PASSWORD = os.environ["DB_PASSWORD"]

# optional with a default
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# explicit validation at startup
required = ["DB_PASSWORD", "STRIPE_KEY"]
missing = [k for k in required if not os.getenv(k)]
if missing:
    raise RuntimeError(f"Missing variables: {', '.join(missing)}")
```

### Docker / Docker Compose

```yaml
# WRONG — literal value, goes into git
services:
  api:
    environment:
      - DB_PASSWORD=RealPassword123

# RIGHT — file kept out of git
services:
  api:
    env_file:
      - .env
    environment:
      - DB_HOST=db          # non-sensitive values can stay
```

Never put a secret in a Dockerfile `ARG`/`ENV` — it is baked into the image layers and
`docker history` reveals it. Use build secrets:
```dockerfile
RUN --mount=type=secret,id=npmtoken \
    NPM_TOKEN=$(cat /run/secrets/npmtoken) npm ci
```

### CI/CD

- **GitHub Actions:** Settings → Secrets and variables → Actions. Usage: `${{ secrets.NAME }}`.
  A secret never shows up in logs (the runner masks it), but an `echo` of a derived value can leak.
- **GitLab CI:** Settings → CI/CD → Variables, mark *Masked* and *Protected*.
- Never commit `.github/workflows/*.yml` with a literal token.

### Secret manager (when the project grows)

AWS Secrets Manager, GCP Secret Manager, Azure Key Vault, HashiCorp Vault, Doppler,
Infisical. Advantages over `.env`: automatic rotation, access auditing, no file on disk.
For a small project with a couple of developers, `.env` + a shared password manager is
enough — do not over-engineer too early.

---

## 3. `.env.example` — the contract

Versioned, with the keys and without the values. It is how the other person knows what to fill in.

```bash
# .env.example  (COMMIT THIS)
# Database
DB_URL=jdbc:postgresql://localhost:5432/appdb
DB_USER=
DB_PASSWORD=

# Integrations
STRIPE_KEY=
OPENAI_API_KEY=

# Optional
LOG_LEVEL=INFO
```

Generate it from an existing `.env`, without carrying the values over:
```bash
sed -E 's/^([A-Za-z_][A-Za-z0-9_]*)=.*/\1=/' .env > .env.example
```

Document in the README: copy `.env.example` to `.env` and fill it in.

---

## 4. Stop tracking the file

`.gitignore` does **not** remove what is already tracked:

```bash
git rm --cached .env
git rm --cached -r config/secrets/     # directory
echo '.env' >> .gitignore
git commit -m "chore: stop tracking .env"
```

Confirm it left the index but is still on disk:
```bash
git ls-files | grep -i env      # must not list .env
ls -la .env                     # must still exist locally
```

This fixes the **present**. History still has the file — see `history-rewrite.md`.

---

## 5. Verification

```bash
# is the secret gone from the working tree?
git --no-pager grep -n 'RealPassword123' || echo "clean in working tree"

# and from history?
git --no-pager log -S'RealPassword123' --all --oneline || echo "clean in history"

# does the app still start with the variable?
DB_PASSWORD='...' java -jar app.jar
```

Running the scanner again closes the loop:
```bash
python3 scripts/scan_secrets.py . --history
```
