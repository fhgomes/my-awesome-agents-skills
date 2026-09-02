# Prevenção — Para não acontecer de novo

O objetivo é tornar o vazamento **impossível por acidente**, não depender de lembrar.

---

## 1. `.gitignore` completo

```gitignore
# Segredos e ambiente
.env
.env.*
!.env.example
!.env.template
*.local

# Chaves e certificados
*.pem
*.key
*.p12
*.pfx
*.jks
*.keystore
id_rsa
id_ed25519
*.ppk

# Credenciais de ferramentas
.npmrc
.pypirc
.netrc
.pgpass
credentials.json
service-account*.json
serviceAccount*.json
.aws/
kubeconfig
*.ovpn

# Terraform (state guarda secret em texto claro)
*.tfstate
*.tfstate.*
.terraform/
*.tfvars
!example.tfvars

# Config local de IDE que pode ter token
.vscode/settings.json
.idea/workspace.xml

# Dumps e bancos
*.sql
*.dump
*.sqlite
*.sqlite3
*.db

# Backups
*.bak
*.backup
*.old
*~

# SO
.DS_Store
Thumbs.db
```

Ajuste ao projeto — se o repo legitimamente versiona migrations `.sql`, troque a regra
por algo mais específico (`dumps/*.sql`).

**Lembre:** `.gitignore` só afeta arquivos ainda não rastreados. Para os já rastreados,
`git rm --cached` (ver `remediation.md`).

---

## 2. Pre-commit hook

Bloqueia o commit antes do segredo entrar no histórico. Funciona sem instalar nada.

Crie `.git/hooks/pre-commit`:

```bash
#!/usr/bin/env bash
# Bloqueia commit com segredo aparente. Bypass consciente: git commit --no-verify
set -uo pipefail

STAGED=$(git diff --cached --name-only --diff-filter=ACM)
[ -z "$STAGED" ] && exit 0

FAIL=0

# 1) arquivos que nunca devem ser commitados
for f in $STAGED; do
  case "$f" in
    .env|.env.*|*.pem|*.key|*.p12|*.pfx|*.jks|id_rsa|id_ed25519|*.tfstate|.npmrc|.pgpass)
      case "$f" in
        .env.example|.env.template|.env.sample) ;;
        *) echo "BLOQUEADO: $f nao deve ser versionado"; FAIL=1 ;;
      esac
      ;;
  esac
done

# 2) padroes de segredo no conteudo staged
PATTERNS='(AKIA|ASIA)[A-Z0-9]{16}|gh[pousr]_[A-Za-z0-9]{36}|glpat-[A-Za-z0-9_-]{20}|xox[baprs]-[A-Za-z0-9-]{10}|sk_live_[A-Za-z0-9]{20}|sk-ant-[A-Za-z0-9_-]{20}|AIza[A-Za-z0-9_-]{35}|-----BEGIN [A-Z ]*PRIVATE KEY-----|(password|senha|secret|api[_-]?key)[[:space:]]*[:=][[:space:]]*["'"'"'][^"'"'"'${]{8,}["'"'"']'

if git diff --cached -U0 | grep -nEi "$PATTERNS" >/dev/null 2>&1; then
  echo "BLOQUEADO: possivel segredo no diff:"
  git diff --cached -U0 | grep -nEi "$PATTERNS" | sed 's/^/  /' | head -10
  FAIL=1
fi

if [ "$FAIL" -ne 0 ]; then
  echo
  echo "Corrija, ou use 'git commit --no-verify' se for falso positivo."
  exit 1
fi
exit 0
```

```bash
chmod +x .git/hooks/pre-commit
```

Hooks em `.git/hooks/` **não são versionados** — cada pessoa instala o seu. Para
compartilhar com a Marcele, versione em `.githooks/` e aponte o git para lá:

```bash
mkdir -p .githooks && mv .git/hooks/pre-commit .githooks/
chmod +x .githooks/pre-commit
git config core.hooksPath .githooks
git add .githooks && git commit -m "chore: hook de pre-commit contra secrets"
```

Cada pessoa roda uma vez após clonar:
```bash
git config core.hooksPath .githooks
```

---

## 3. Proteções do lado do GitHub

Repo público (grátis) e privado (planos pagos):
- **Settings → Code security → Secret scanning:** ligar. O GitHub detecta e, com
  *push protection*, bloqueia o push que contém segredo conhecido.
- **Push protection:** ativar. É a rede de segurança que pega o que o hook local não pegou.
- **Dependabot alerts:** para vulnerabilidade em dependência.

Secret scanning do GitHub cobre formatos de provedores parceiros (AWS, Stripe, etc.) —
não pega senha genérica nem dado pessoal. Não substitui a auditoria.

---

## 4. Higiene contínua

- **Segredo compartilhado entre vocês dois:** gerenciador de senhas (Bitwarden, 1Password)
  ou secret manager. Nunca WhatsApp, Slack, e-mail ou print.
- **Um segredo por ambiente:** dev, staging e prod com credenciais diferentes. Vazamento
  de dev não derruba prod.
- **Rotação periódica** de chaves de produção, mesmo sem incidente.
- **Menor privilégio:** a chave que o app usa não precisa ser admin. Chave de leitura
  vazada faz muito menos estrago.
- **Dado de teste é dado FAKE.** Nunca copiar dump de produção para fixture. Use faker
  para gerar CPF, nome, e-mail. Um CPF real numa fixture é vazamento de dado pessoal
  com implicação de LGPD.

---

## 5. Checklist antes de tornar um repo público

- [ ] `scan_secrets.py . --history` sem achado crítico/alto
- [ ] Histórico varrido, não só o working tree
- [ ] Nenhum `.env`, `.pem`, `.key`, `credentials.json` rastreado
- [ ] `.gitignore` cobre segredos, chaves, dumps, backups
- [ ] `.env.example` versionado, com chaves vazias
- [ ] Nenhum IP interno, hostname de produção ou endpoint privado no código
- [ ] Fixtures usam dado fake, não dado de cliente real
- [ ] README não tem screenshot com token, e-mail ou dado pessoal
- [ ] Issues, PRs e mensagens de commit revisados (também ficam públicos)
- [ ] Wiki e releases do repo revisados
- [ ] Credenciais que já estiveram commitadas foram **rotacionadas**
- [ ] Secret scanning + push protection ligados no GitHub
- [ ] Licença definida (não é segurança, mas é o momento de decidir)

Mensagem de commit e título de issue vazam com o mesmo alcance do código —
`git log --all --grep='senha'` costuma render surpresa.
