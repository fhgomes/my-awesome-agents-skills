# Limpeza de Histórico do Git

**Operação destrutiva.** Reescreve os SHAs de todos os commits afetados e de todos os
descendentes, exige `push --force`, e quebra o clone de qualquer pessoa que já tenha o repo.

**Nunca rode sem confirmação explícita do usuário.**

---

## Antes de começar, entenda o limite

Reescrever histórico **não desfaz um vazamento que já foi público.**

Se o repo esteve público, mesmo por minutos:
- bots varrem o GitHub em tempo real e chaves de nuvem são exploradas em minutos
- forks, mirrors e clones locais de terceiros mantêm os commits antigos
- caches do GitHub podem servir o commit por SHA mesmo depois do force-push
- serviços de indexação e o Wayback Machine podem ter copiado

Então: **rotacione a credencial primeiro, sempre.** Reescrever o histórico é higiene,
não remediação. A remediação é a rotação.

Se o repo **sempre foi privado** e só você e a Marcele têm clone, a reescrita é
suficiente — e ainda assim rotacione se a chave for de produção.

---

## Passo 0 — Backup

```bash
git clone --mirror /caminho/do/repo /caminho/backup-repo.git
# ou simplesmente
cp -r repo repo-backup
```

Confirme que o backup abre antes de mexer no original.

---

## Opção A — `git filter-repo` (recomendada)

Não está instalada nesta máquina. Instalar:
```bash
pip install git-filter-repo
```

### Remover um arquivo de todo o histórico
```bash
cd repo
git filter-repo --invert-paths --path .env
git filter-repo --invert-paths --path config/secrets.yml --path deploy.pem
```

### Remover um diretório inteiro
```bash
git filter-repo --invert-paths --path config/private/
```

### Substituir o texto do segredo, preservando os arquivos
Útil quando o arquivo deve continuar existindo, mas sem o valor.

```bash
cat > /tmp/replacements.txt <<'EOF'
SenhaReal123==>***REMOVED***
AKIA_EXEMPLO_NAO_REAL==>***REMOVED***
sk_live_EXEMPLO_NAO_REAL==>***REMOVED***
EOF

git filter-repo --replace-text /tmp/replacements.txt
```

Depois **apague** `/tmp/replacements.txt` — ele contém os segredos em texto claro.

> `filter-repo` exige um clone limpo por padrão. Em repo com working tree sujo ele recusa;
> use `--force` só se souber que não vai perder trabalho não commitado.

---

## Opção B — BFG Repo-Cleaner

Também não instalado. Requer Java. Baixar o `.jar` do site oficial.

```bash
java -jar bfg.jar --delete-files .env repo.git
java -jar bfg.jar --replace-text replacements.txt repo.git

cd repo.git
git reflog expire --expire=now --all
git gc --prune=now --aggressive
```

BFG não mexe no commit mais recente (HEAD) — limpe o arquivo no working tree e commite
**antes** de rodar.

---

## Opção C — `git filter-branch` (só se não puder instalar nada)

Nativo do git, disponível aqui. É lento e o próprio git desaconselha, mas funciona.

```bash
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch .env" \
  --prune-empty --tag-name-filter cat -- --all

# limpar as referências que o filter-branch deixa para trás
rm -rf .git/refs/original/
git reflog expire --expire=now --all
git gc --prune=now --aggressive
```

Para várias entradas:
```bash
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch .env config/secrets.yml deploy.pem" \
  --prune-empty --tag-name-filter cat -- --all
```

---

## Passo final — publicar a reescrita

```bash
# conferir que sumiu ANTES de empurrar
git --no-pager log --all --oneline -- .env        # sem saída = removido
git --no-pager log -S'SenhaReal123' --all --oneline

# empurrar
git push origin --force --all
git push origin --force --tags
```

Se o GitHub ainda mostrar o commit antigo por URL/SHA, abra um ticket no suporte pedindo
garbage collection — só eles limpam o cache do lado do servidor.

---

## Passo crítico com a Marcele (repo compartilhado)

Depois do force-push, **quem não reescreveu precisa re-clonar**:

```bash
# ERRADO — recria os commits antigos e desfaz sua limpeza
git pull

# CERTO
cd ..
rm -rf projeto
git clone git@github.com:usuario/projeto.git
```

Combine antes: quem tiver trabalho não commitado deve salvar o patch primeiro.
```bash
git diff > /tmp/meu-trabalho.patch     # antes de deletar o clone
git apply /tmp/meu-trabalho.patch      # depois de re-clonar
```

Force-push com a outra pessoa dando `git pull` no meio é a receita para os commits
antigos voltarem e o segredo reaparecer.

---

## Checklist de encerramento

- [ ] Credencial **rotacionada** no provedor (feito antes de tudo)
- [ ] Verificado se a chave antiga foi usada por terceiro (logs do provedor)
- [ ] Backup do repo criado e testado
- [ ] Histórico reescrito e verificado (`git log -S` sem resultado)
- [ ] Force-push feito em todas as branches e tags
- [ ] Marcele avisada e re-clonou
- [ ] `.gitignore` corrigido
- [ ] `.env.example` versionado
- [ ] Pre-commit hook instalado (ver `prevention.md`)
- [ ] Scanner rodado de novo: `scan_secrets.py . --history` → limpo
