# Triagem de URL, Domínio e Phishing

## Regra de navegação

- **Nunca** abrir URL suspeita no Chrome real do usuário (`mcp__claude-in-chrome__*`).
  Cookies de sessão, senhas salvas e perfil logado ficam expostos, e drive-by download
  cai direto na máquina.
- Se for realmente necessário renderizar, usar o Browser interno (`mcp__Claude_Browser__*`),
  que é isolado do perfil real.
- Preferência sempre: inspecionar por HTTP sem renderizar.
- **Nunca** canalizar resposta pra shell (`curl ... | bash`), nem baixar e executar.

---

## Passo 1 — Decompor a URL antes de tocar nela

```
https://login.microsoft.com.secure-verify[.]ru/auth?redirect=...
        └────── isca ──────┘└─ domínio real ─┘
```

O domínio real é sempre o que vem **imediatamente antes do TLD**. Tudo à esquerda é
subdomínio e pode dizer qualquer coisa.

Verifique:
- Domínio registrável real (eTLD+1) vs. marca alegada
- Homoglifos e typosquatting: `rnicrosoft` (rn≈m), `goog1e`, `paypaI` (I maiúsculo),
  `arnazon`, punycode `xn--`
- TLD que imita extensão de arquivo: `.zip`, `.mov`
- TLD de alto abuso quando combinado com marca conhecida: `.ru`, `.cn`, `.tk`, `.xyz`, `.top`, `.icu`
- Domínio hospedeiro genérico servindo marca: `*.web.app`, `*.pages.dev`, `*.workers.dev`,
  `*.r2.dev`, `*.blob.core.windows.net`, `*.ngrok-free.app`, `*.duckdns.org`
- Credencial embutida: `https://apple.com@evil.ru/` — o host é `evil.ru`
- Porta não padrão (`:8080`, `:4444`) num link que se diz de banco/empresa
- IP puro no lugar de domínio
- Encurtador (`bit.ly`, `t.co`, `is.gd`, `cutt.ly`, `tinyurl`) escondendo destino

---

## Passo 2 — Cabeçalhos e cadeia de redirect (sem baixar corpo)

```bash
curl -sSIL --max-time 15 -A 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)' 'URL' \
  | grep -iE '^HTTP/|^location:|^content-type:|^content-disposition:|^content-length:|^server:'
```

Ler:
- Cada `Location:` da cadeia — para onde o link realmente leva
- `Content-Type: application/octet-stream` ou `application/x-msdownload` num "link de página"
- `Content-Disposition: attachment; filename=...` — é download, não página
- Redirect que muda de domínio duas ou mais vezes até cair em host desconhecido
- Cloaking: resposta diferente para User-Agent de bot vs. browser (compare os dois)

```bash
# comparar comportamento por User-Agent (sinal de cloaking)
curl -sSI --max-time 10 -A 'curl/8' 'URL' | head -1
curl -sSI --max-time 10 -A 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)' 'URL' | head -1
```

---

## Passo 3 — Corpo como texto, limitado

```bash
curl -sS --max-time 20 --max-filesize 2000000 -A 'Mozilla/5.0' 'URL' > /tmp/page.html
file /tmp/page.html && wc -c /tmp/page.html
grep -oiE '<form[^>]*action="[^"]*"' /tmp/page.html | head
grep -oiE 'src="[^"]*"|href="[^"]*"' /tmp/page.html | sort -u | head -40
grep -icE 'atob\(|eval\(|fromCharCode|unescape\(|document\.write' /tmp/page.html
```

Sinais de alerta na página:
- `<form action=` apontando pra domínio diferente do da página, com campo `password`
- Página de login pixel-perfeita de marca conhecida num domínio que não é o da marca
- JS pesadamente ofuscado num site institucional simples
- `<iframe>` invisível carregando terceiro domínio
- Meta refresh imediato pra outro host
- Kit de phishing: pasta com `index.html` + `post.php` + logo da marca

---

## Passo 4 — Idade e reputação do domínio

Domínio registrado há poucos dias é o indicador isolado mais forte de phishing.

```bash
whois dominio.com 2>/dev/null | grep -iE 'creation|created|registrar|registrant|expiry'
```

(`whois` pode não existir no Git Bash — nesse caso use o WSL ou diga que não pôde verificar.)

```bash
nslookup dominio.com
nslookup -type=MX dominio.com     # domínio de phishing costuma não ter MX real
```

- Criado nos últimos 30 dias + imita marca = MALICIOUS com alta confiança
- Registrar com privacidade + domínio novo + certificado emitido no mesmo dia = kit de phishing
- Certificado TLS válido **não** significa nada: Let's Encrypt é gratuito e automático.
  Cadeado ≠ seguro. Diga isso ao usuário se ele mencionar "mas tem cadeado".

---

## Passo 5 — Consulta externa (com autorização)

Enviar hash/URL a serviço externo é ação outward-facing. **Pergunte antes.**
- Submeter uma URL ao VirusTotal a torna pública e pode alertar o operador do site.
- Submeter arquivo publica o conteúdo — nunca faça com amostra que possa ter dado sensível.

Sem consulta externa, ainda dá pra dar veredito sólido com os passos 1-4 — só declare o
escopo ("análise local, sem consulta a reputação externa").

---

## Padrões de golpe por categoria

**Phishing de credencial** — página de login clonada, form postando pra outro host,
urgência ("sua conta será suspensa em 24h"), domínio novo.

**Fake update / ClickFix** — página diz que o navegador/Chrome/Flash precisa atualizar, ou
manda o usuário colar um comando no PowerShell/Win+R "para verificar que é humano".
**Qualquer site pedindo pra colar comando no terminal é ataque.** Sem exceção.

**Fake CAPTCHA** — "prove que é humano" seguido de instrução pra apertar Win+R e colar.
Mesma família do ClickFix.

**Suporte técnico falso** — pop-up travado em tela cheia com número de telefone e alarme
sonoro. Nenhum antivírus real usa esse formato.

**Cripto/airdrop** — "conecte sua carteira para reivindicar". Assinar transação de
`setApprovalForAll` esvazia a carteira. Nunca conectar carteira em site não verificado.

**Sextortion / e-mail com senha vazada** — a senha veio de um vazamento público antigo.
Não há infecção. Não pagar. Trocar a senha onde ela ainda for usada.

**Boleto / PIX adulterado** — anexo ou link com dados bancários diferentes do fornecedor
real. Confirmar sempre por canal separado, nunca pelo contato do próprio e-mail.

---

## Formato do veredito de URL

```
## Veredito
MALICIOUS — confiança alta — escopo: headers + HTML estático, sem renderização de JS

## O que é
Página de phishing clonando o login do <marca>, hospedada em domínio registrado há 4 dias.

## Evidências
1. Domínio real: secure-verify[.]ru (marca aparece só como subdomínio)
2. <form action="https://outro-host[.]xyz/post.php"> com input type=password
3. Registro do domínio: 2026-08-25 (4 dias)
4. Redirect chain: bit.ly → t[.]co → secure-verify[.]ru

## IoCs
- hxxps://login.microsoft.com.secure-verify[.]ru/auth
- outro-host[.]xyz
- 203.0.113.44

## Ação imediata
- Não abrir. Se já abriu e digitou senha: trocar a senha de OUTRO dispositivo e
  encerrar todas as sessões ativas; ativar MFA.
- Bloquear domínio no DNS/firewall.

## Verificação
- Confirmar que não há sessão ativa desconhecida no painel de segurança da conta.
```

Escreva URLs e IPs maliciosos **defangados** (`hxxp://`, `dominio[.]com`) para evitar
clique acidental.
