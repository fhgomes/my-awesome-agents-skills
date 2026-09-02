# Catálogo de Padrões de Detecção

Cada entrada traz o formato, por que importa, e o **falso positivo** correspondente.
O scanner (`scripts/scan_secrets.py`) já implementa a maioria; esta referência serve
para revisão manual e para interpretar os achados.

---

## Segredos por prefixo (alta confiança)

Estes têm formato próprio e quase não dão falso positivo:

| Serviço | Formato | Severidade |
|---|---|---|
| AWS Access Key | `AKIA` / `ASIA` + 16 alfanuméricos maiúsculos | crítico |
| AWS Secret | 40 chars base64 junto de `aws_secret_access_key` | crítico |
| GitHub PAT (clássico) | `ghp_` / `gho_` / `ghu_` / `ghs_` / `ghr_` + 36 | crítico |
| GitHub PAT (fine-grained) | `github_pat_` + ~82 | crítico |
| GitLab PAT | `glpat-` + 20 | crítico |
| Slack | `xoxb-` / `xoxp-` / `xoxa-` / `xoxr-` / `xoxs-` | crítico |
| Slack webhook | `https://hooks.slack.com/services/T.../B.../...` | alto |
| Stripe live | `sk_live_` + 24+ | crítico |
| Stripe test | `sk_test_` + 24+ | baixo (sandbox) |
| OpenAI | `sk-` ou `sk-proj-` + 32+ | crítico |
| Anthropic | `sk-ant-` + 20+ | crítico |
| SendGrid | `SG.` + token + `.` + token | crítico |
| Google API | `AIza` + 35 | alto |
| Twilio | `SK` + 32 hex | alto |
| npm | `//registry.npmjs.org/:_authToken=` | crítico |

**Exceção que importa:** `AKIAIOSFODNN7EXAMPLE` é a chave de exemplo oficial da
documentação da AWS. Aparece em tutoriais legitimamente. Continua valendo reportar
(pode ser copy-paste que virou chave real), mas com nota.

---

## Chaves privadas e certificados

```
-----BEGIN RSA PRIVATE KEY-----
-----BEGIN OPENSSH PRIVATE KEY-----
-----BEGIN EC PRIVATE KEY-----
-----BEGIN PGP PRIVATE KEY BLOCK-----
-----BEGIN ENCRYPTED PRIVATE KEY-----
```

**Falso positivo:** `-----BEGIN PUBLIC KEY-----` e `-----BEGIN CERTIFICATE-----` são
públicos por natureza — não são vazamento. `ssh-rsa AAAA...` em `authorized_keys` ou
`.pub` também é público.

Chave privada **encriptada** ainda é vazamento: a passphrase pode ser fraca ou estar
em outro lugar do repo.

---

## Connection strings

```
postgresql://usuario:senha@host:5432/db
mysql://root:senha@localhost/app
mongodb+srv://user:pass@cluster.mongodb.net
redis://:senha@host:6379
amqp://user:pass@rabbit:5672
jdbc:postgresql://host:5432/db?user=app&password=senha
Server=x;Database=y;User Id=z;Password=senha;
DefaultEndpointsProtocol=https;AccountName=x;AccountKey=...
```

Também: qualquer URL `https://user:senha@host`.

**Falso positivo:** `postgresql://user:password@localhost` com literalmente a palavra
`password`, ou `${DB_PASSWORD}` interpolado — é template, não segredo.

---

## Credencial hardcoded genérica

O padrão de maior volume e de mais falso positivo:
```
password = "..."      senha: "..."       secret = '...'
api_key: "..."        token = "..."      client_secret = "..."
```

Filtros que o scanner aplica antes de reportar:
- **Referência a env var** → não é vazamento, é o padrão correto:
  `process.env.X`, `os.environ[...]`, `System.getenv()`, `${VAR}`, `%VAR%`, `config.get(...)`
- **Placeholder** → `your-api-key`, `xxx`, `changeme`, `<INSERT>`, `example`, `dummy`, `TODO`
- **Entropia baixa** → `aaaaaaaa`, `11111111`, palavra de dicionário curta
- **Valor não-segredo** → `true`, `false`, `localhost`, `root`, `admin`, `null`
- **Caminho de teste/doc** → rebaixa a severidade, mas não elimina

---

## PII brasileira

| Dado | Formato | Validação |
|---|---|---|
| CPF | `999.999.999-99` ou 11 dígitos | dígitos verificadores (mód. 11) |
| CNPJ | `99.999.999/9999-99` | dígitos verificadores |
| RG | varia por estado, 7-12 dígitos | sem algoritmo padrão — precisa do rótulo |
| CNH | 11 dígitos | dígitos verificadores |
| Título de eleitor | 12 dígitos | dígitos verificadores |
| PIS/NIS | 11 dígitos | mód. 11 |
| CEP | `99999-999` | só formato |
| Telefone | `(99) 99999-9999` | só formato |

O scanner valida CPF por dígito verificador — reduz muito o falso positivo, já que
sequência aleatória de 11 dígitos raramente passa.

**Falso positivo comum:** `000.000.000-00` e `111.111.111-11` são inválidos por dígitos
repetidos (o scanner já descarta). CPFs gerados por faker são estatisticamente válidos e
**vão** aparecer — por isso o contexto do caminho importa: `tests/fixtures/` rebaixa,
`clientes.csv` na raiz não.

---

## PCI (dados de cartão)

Número de cartão: 13-19 dígitos, **validado por Luhn**. Sem Luhn, qualquer sequência
longa vira falso positivo.

Cartões de teste conhecidos dos gateways (o scanner marca com nota):
```
4242 4242 4242 4242   Stripe (4242 x4)
4111 1111 1111 1111   Visa teste
5555 5555 5555 4444   Mastercard teste
3782 822463 10005     Amex teste
```

CVV (`cvv`, `cvc`, `security_code` + 3-4 dígitos) e validade acompanhando número de
cartão elevam para crítico. **Armazenar CVV é proibido pelo PCI-DSS**, mesmo criptografado.

---

## PHI (dados de saúde)

Sem formato fixo — depende de rótulo e contexto:
- CID-10 (`A00` a `Z99`) associado a pessoa
- Número de prontuário
- Carteirinha de plano de saúde
- Resultado de exame vinculado a nome/CPF
- Campos como `diagnostico`, `medicamento`, `alergia`, `cirurgia` em dataset com identificação

PHI tem o maior peso regulatório. Qualquer suspeita → tratar como crítico e escalar
para revisão humana.

---

## Infra interna

| Padrão | Exemplo |
|---|---|
| IP privado | `10.x.x.x`, `172.16-31.x.x`, `192.168.x.x` |
| Hostname interno | `db-prod.internal`, `srv01.local`, `app.corp` |
| Caminho revelando usuário | `C:\Users\fernando\...`, `/home/marcele/...` |
| Endpoint privado | URL de admin, painel, `:8080/actuator`, `/phpmyadmin` |
| VPN / bastion | config `.ovpn`, IP de jump host |

Isolado é ruído de baixa severidade. **Em conjunto**, entrega o mapa da rede interna —
por isso o scanner reporta, mesmo que em nível médio/baixo.

Caminho com nome de usuário também é PII leve: expõe o nome real de quem desenvolveu.

---

## Onde o dado pessoal costuma se esconder

Lugares que uma varredura só de `src/` não alcança:

- `tests/fixtures/`, `seeds/`, `mock/` — dump de produção usado como massa de teste
- `*.csv`, `*.xlsx`, `*.json` de exemplo na raiz
- `docs/` com screenshot mostrando dados de tela real
- Log commitado por acidente (`app.log`, `debug.log`, `nohup.out`)
- Migration com `INSERT` de dado real
- Comentário de código com dado de cliente para debug
- **Mensagem de commit** (`git log --all --grep='cpf'`)
- **Título e corpo de issue/PR** — públicos junto com o repo
- Wiki e releases
- `.har` de captura de rede (contém headers com token e corpo com dado)

---

## Como calibrar a severidade

Pergunta única: **o que um atacante faz com isso em 5 minutos?**

- Chave de nuvem viva → cria recursos, gera custo, acessa dados → **crítico**
- Token de escrita no GitHub → injeta código, sequestra CI → **crítico**
- PCI/PHI → dano regulatório e à pessoa, irreversível → **crítico**
- Senha de banco de produção → dump completo → **crítico**
- Key de sandbox → nada além do ambiente de teste → **baixo**
- IP interno isolado → precisa de outro vetor para valer → **médio/baixo**
- E-mail do próprio autor no `package.json` → é intencional → **não reportar**
