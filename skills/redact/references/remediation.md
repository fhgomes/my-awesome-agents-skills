# Remediação — Tirando o Segredo do Código

Ordem que nunca muda: **rotacionar → externalizar → limpar histórico → prevenir.**

Rotacionar primeiro porque, enquanto a chave antiga for válida, todo o resto é cosmético.

---

## 1. Rotacionar (antes de qualquer commit)

| Serviço | Onde revogar/rotacionar |
|---|---|
| AWS | IAM → Users → Security credentials → desativar e criar nova access key |
| GCP | IAM → Service Accounts → Keys → deletar e gerar nova |
| Azure | Storage account → Access keys → Rotate; App registrations → Certificates & secrets |
| GitHub | Settings → Developer settings → PAT → Revoke; e Deploy keys do repo |
| GitLab | Settings → Access Tokens → Revoke |
| Stripe | Developers → API keys → Roll key (a antiga para na hora) |
| OpenAI / Anthropic | Painel de API keys → revogar e criar nova |
| Slack | App config → OAuth & Permissions → Revoke / Regenerate |
| SendGrid / Twilio | API keys → delete + create |
| Banco de dados | `ALTER USER app_user WITH PASSWORD '...'` e atualizar quem consome |
| Chave SSH | Gerar novo par, trocar em `authorized_keys`, remover a antiga |
| JWT signing secret | Trocar o secret — invalida todos os tokens emitidos, planeje a virada |

Depois de rotacionar, **verifique o uso da chave antiga** (CloudTrail, logs de acesso do
provedor). Uso vindo de IP desconhecido = já foi explorada, vira incidente.

---

## 2. Externalizar por stack

### Spring Boot

`application.properties`:
```properties
# ERRADO
spring.datasource.password=SenhaReal123

# CERTO — obrigatória, quebra o boot se faltar
spring.datasource.password=${DB_PASSWORD}

# CERTO — com default só para dev local (nunca use default em prod)
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

Fornecendo os valores:
```bash
export DB_PASSWORD='...'
java -jar app.jar

# ou por argumento (aparece em `ps` — evite em máquina compartilhada)
java -jar app.jar --spring.datasource.password="$DB_PASSWORD"

# ou perfil separado, com o arquivo fora do git
java -jar app.jar --spring.profiles.active=prod
```

`application-prod.properties` deve estar no `.gitignore`. Versione
`application-prod.properties.example` com as chaves vazias.

### Node

```js
// ERRADO
const stripe = require('stripe')('sk_live_51H8xQz...');

// CERTO
const key = process.env.STRIPE_KEY;
if (!key) throw new Error('STRIPE_KEY não definida');
const stripe = require('stripe')(key);
```

Com dotenv em desenvolvimento (nunca em produção — lá as vars vêm do orquestrador):
```js
if (process.env.NODE_ENV !== 'production') require('dotenv').config();
```

### Python

```python
import os

# obrigatória — falha alto e cedo
DB_PASSWORD = os.environ["DB_PASSWORD"]

# opcional com default
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# validação explícita no startup
required = ["DB_PASSWORD", "STRIPE_KEY"]
missing = [k for k in required if not os.getenv(k)]
if missing:
    raise RuntimeError(f"Variáveis ausentes: {', '.join(missing)}")
```

### Docker / Docker Compose

```yaml
# ERRADO — valor literal, vai pro git
services:
  api:
    environment:
      - DB_PASSWORD=SenhaReal123

# CERTO — arquivo fora do git
services:
  api:
    env_file:
      - .env
    environment:
      - DB_HOST=db          # não-sensível pode ficar
```

Nunca ponha secret em `ARG`/`ENV` do Dockerfile — fica gravado nas camadas da imagem e
`docker history` revela. Use build secrets:
```dockerfile
RUN --mount=type=secret,id=npmtoken \
    NPM_TOKEN=$(cat /run/secrets/npmtoken) npm ci
```

### CI/CD

- **GitHub Actions:** Settings → Secrets and variables → Actions. Uso: `${{ secrets.NOME }}`.
  Secret nunca aparece em log (o runner mascara), mas `echo` de valor derivado pode vazar.
- **GitLab CI:** Settings → CI/CD → Variables, marcar *Masked* e *Protected*.
- Nunca commitar `.github/workflows/*.yml` com token literal.

### Secret manager (quando o projeto crescer)

AWS Secrets Manager, GCP Secret Manager, Azure Key Vault, HashiCorp Vault, Doppler,
Infisical. Vantagem sobre `.env`: rotação automática, auditoria de acesso, sem arquivo
em disco. Para projeto pequeno de dois devs, `.env` + gerenciador de senhas compartilhado
já resolve — não complique cedo demais.

---

## 3. `.env.example` — o contrato

Versionado, com as chaves e sem os valores. É como a outra pessoa sabe o que preencher.

```bash
# .env.example  (COMMITAR)
# Banco
DB_URL=jdbc:postgresql://localhost:5432/appdb
DB_USER=
DB_PASSWORD=

# Integrações
STRIPE_KEY=
OPENAI_API_KEY=

# Opcional
LOG_LEVEL=INFO
```

Gerar a partir de um `.env` existente, sem levar os valores:
```bash
sed -E 's/^([A-Za-z_][A-Za-z0-9_]*)=.*/\1=/' .env > .env.example
```

Documente no README: copiar `.env.example` para `.env` e preencher.

---

## 4. Parar de rastrear o arquivo

`.gitignore` **não** remove o que já está rastreado:

```bash
git rm --cached .env
git rm --cached -r config/secrets/     # diretório
echo '.env' >> .gitignore
git commit -m "chore: remove .env do versionamento"
```

Confirmar que saiu do índice mas continua em disco:
```bash
git ls-files | grep -i env      # não deve listar .env
ls -la .env                     # deve existir localmente
```

Isso resolve o **presente**. O histórico continua tendo o arquivo — ver
`history-rewrite.md`.

---

## 5. Verificação

```bash
# o segredo sumiu do working tree?
git --no-pager grep -n 'SenhaReal123' || echo "limpo no working tree"

# e do histórico?
git --no-pager log -S'SenhaReal123' --all --oneline || echo "limpo no historico"

# a app ainda sobe com a variável?
DB_PASSWORD='...' java -jar app.jar
```

Rodar o scanner de novo fecha o ciclo:
```bash
python3 scripts/scan_secrets.py . --history
```
