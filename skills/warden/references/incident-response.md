# Resposta a Incidente — Host Possivelmente Comprometido

Aplica quando o usuário diz: "já executei", "acho que peguei vírus", "o Defender acusou",
"tá aparecendo coisa estranha", "roubaram minha conta".

Prioridade: **conter → preservar → escopo → credenciais → erradicar**. Nessa ordem.

---

## Primeiros 15 minutos

### 1. Conter
- Desconectar da rede (Wi-Fi off / cabo fora).
- **Não desligar** a máquina se houver suspeita de ransomware ativo ou necessidade de
  perícia — a RAM tem chave e evidência. Desligue apenas se a criptografia estiver em curso.
- Não rodar "limpeza" ainda. Limpar antes de entender apaga a evidência do escopo.

### 2. Preservar
```powershell
Get-FileHash "C:\caminho\amostra.exe" -Algorithm SHA256
Copy-Item "C:\caminho\amostra.exe" "$env:USERPROFILE\Desktop\quarentena\amostra.exe.bin" -Force
```
Renomear com `.bin` evita duplo-clique acidental. Anotar: horário do run, o que o usuário
clicou, de onde veio, o que apareceu na tela.

### 3. O que o Defender já viu
```powershell
Get-MpThreatDetection | Sort-Object InitialDetectionTime -Descending |
  Select-Object InitialDetectionTime,ThreatID,Resources,ActionSuccess | Format-List

Get-MpThreat | Select-Object ThreatName,SeverityID,DidThreatExecute,Resources | Format-List
```
`DidThreatExecute = True` muda tudo: não é mais "arquivo suspeito", é comprometimento.

---

## Escopo — o que realmente rodou

### Processos e origem
```powershell
Get-CimInstance Win32_Process |
  Select-Object ProcessId,ParentProcessId,Name,ExecutablePath,CommandLine |
  Where-Object { $_.ExecutablePath -match '\\Temp\\|\\AppData\\|\\Downloads\\|\\Public\\|\\ProgramData\\' } |
  Format-List
```
Cadeia parent-child conta a história: `winword.exe → powershell.exe` é execução de macro.
`explorer.exe → wscript.exe` é usuário que abriu um `.vbs`.

### Rede
```powershell
Get-NetTCPConnection -State Established | ForEach-Object {
  [PSCustomObject]@{
    Remote = "$($_.RemoteAddress):$($_.RemotePort)"
    PID    = $_.OwningProcess
    Proc   = (Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue).Name
  }
} | Sort-Object Proc | Format-Table -AutoSize
```
Procure: processo de usuário falando com IP cru em porta alta, conexão persistente pra
host desconhecido, tráfego pra Discord/Telegram API vindo de processo que não é o app.

### Histórico do PowerShell (frequentemente esquecido pelo atacante)
```powershell
Get-Content "$env:APPDATA\Microsoft\Windows\PowerShell\PSReadLine\ConsoleHost_history.txt" -Tail 80
```

### Eventos relevantes
```powershell
# processos criados na última hora (requer auditoria de criação de processo habilitada)
Get-WinEvent -FilterHashtable @{LogName='Security'; Id=4688; StartTime=(Get-Date).AddHours(-1)} -MaxEvents 60 -ErrorAction SilentlyContinue |
  Select-Object TimeCreated,@{n='Msg';e={$_.Message -split "`n" | Select-String 'New Process Name|Command Line'}}

# PowerShell script block logging
Get-WinEvent -FilterHashtable @{LogName='Microsoft-Windows-PowerShell/Operational'; Id=4104} -MaxEvents 40 -ErrorAction SilentlyContinue |
  Select-Object TimeCreated,Message | Format-List
```

### Arquivos recém-criados nos lugares de sempre
```powershell
Get-ChildItem "$env:TEMP","$env:APPDATA","$env:LOCALAPPDATA","$env:ProgramData","$env:USERPROFILE\Downloads" -Recurse -File -ErrorAction SilentlyContinue |
  Where-Object { $_.LastWriteTime -gt (Get-Date).AddHours(-6) -and $_.Extension -match '^\.(exe|dll|ps1|bat|vbs|js|scr|lnk|jar|hta)$' } |
  Select-Object FullName,Length,LastWriteTime | Format-Table -AutoSize
```

---

## Persistência — enumerar antes de remover

```powershell
# Run keys
Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run',
                 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Run',
                 'HKCU:\Software\Microsoft\Windows\CurrentVersion\RunOnce',
                 'HKLM:\Software\Microsoft\Windows\CurrentVersion\RunOnce' -ErrorAction SilentlyContinue

# Startup folders
Get-ChildItem "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup",
              "$env:ProgramData\Microsoft\Windows\Start Menu\Programs\Startup" -ErrorAction SilentlyContinue

# Tarefas agendadas criadas recentemente
Get-ScheduledTask | Where-Object { $_.Date -gt (Get-Date).AddDays(-14) } |
  Select-Object TaskName,TaskPath,Date,@{n='Action';e={$_.Actions.Execute}} | Format-Table -AutoSize

# Serviços com binário fora de System32
Get-CimInstance Win32_Service | Where-Object { $_.PathName -notmatch 'System32|Program Files' } |
  Select-Object Name,State,StartMode,PathName | Format-Table -AutoSize

# WMI event subscription (persistência fileless)
Get-CimInstance -Namespace root\Subscription -ClassName __EventFilter -ErrorAction SilentlyContinue
Get-CimInstance -Namespace root\Subscription -ClassName CommandLineEventConsumer -ErrorAction SilentlyContinue

# Exclusões plantadas no Defender (atacante cegando a defesa)
Get-MpPreference | Select-Object -ExpandProperty ExclusionPath
Get-MpPreference | Select-Object -ExpandProperty ExclusionProcess
```

Exclusão do Defender que o usuário não criou é evidência forte de comprometimento.

---

## Credenciais — a parte que mais importa

A categoria de malware commodity mais comum hoje é **infostealer**. Em segundos ele
coleta: senhas salvas no browser, cookies de sessão (que burlam MFA), tokens do Discord,
carteiras cripto, chaves SSH, arquivos `.env`, credenciais de AWS/gcloud.

Se houve execução bem-sucedida, **assuma vazamento total das credenciais daquela máquina**.

Rotacione **a partir de outro dispositivo limpo**, nesta ordem:
1. E-mail principal (é a chave de recuperação de todo o resto) — senha + **encerrar todas as sessões**
2. Gerenciador de senhas — senha mestra
3. Contas financeiras e cripto (mover fundos se houver carteira quente na máquina)
4. GitHub/GitLab: senha, revogar PAT e OAuth apps, trocar chave SSH
5. Cloud: rotacionar access keys AWS/GCP/Azure, revogar service accounts
6. Redes sociais e Discord/Telegram — encerrar sessões
7. VPN corporativa, SSH keys de servidor (e revisar `authorized_keys` nos servidores)

**Encerrar sessões é tão importante quanto trocar a senha.** Cookie roubado continua
funcionando depois da troca de senha e não pede MFA.

Trocar senha *na máquina infectada* é inútil — o stealer captura a nova.

---

## Erradicação

Scan completo, agora com remediação ligada:
```powershell
Update-MpSignature
Start-MpScan -ScanType FullScan
Get-MpThreatDetection | Sort-Object InitialDetectionTime -Descending | Select-Object -First 20
```

Offline scan (roda antes do Windows carregar — pega o que se esconde em runtime):
```powershell
Start-MpWDOScan   # reinicia a máquina
```

### Quando reimagear (seja franco com o usuário)
Reinstalação limpa é a única remediação confiável quando:
- Malware executou com privilégio de administrador
- Há sinal de rootkit/bootkit, ou o AV não consegue remover
- Ransomware criptografou arquivos
- É máquina que guarda credencial de produção, cliente ou carteira cripto
- Não dá pra determinar o escopo com confiança

Não prometa "limpei, tá seguro" quando a evidência não sustenta. Diga o que foi
verificado, o que não foi, e recomende a reimagem quando for o caso.

Após reimagem: restaurar **dados**, nunca executáveis ou instaladores do backup anterior
à infecção sem verificação.

---

## Ransomware — específico

- **Não pagar** — não garante chave e financia a operação.
- Não renomear nem "consertar" os arquivos criptografados.
- Preservar: nota de resgate + 2-3 arquivos criptografados + as versões originais se
  existirem em backup — servem pra identificar a família.
- Verificar se há decryptor público (No More Ransom) pela família identificada.
- Verificar shadow copies antes que sejam apagadas: `vssadmin list shadows`
- Isolar backups **imediatamente** — ransomware moderno procura e criptografa backups
  em rede e nuvem sincronizada.
- Se for ambiente corporativo com dado pessoal: há prazo legal de notificação (LGPD,
  ANPD). Avise que existe essa obrigação, sem dar consultoria jurídica.

---

## Linux / VPS comprometida

```bash
# processos e rede
ps auxf
ss -tunap | grep ESTAB
lsof -i -P -n 2>/dev/null | grep ESTABLISHED

# persistência
crontab -l; ls -la /etc/cron.*; cat /etc/crontab
systemctl list-units --type=service --state=running
ls -la /etc/systemd/system/ /root/.ssh/ ~/.ssh/
cat ~/.ssh/authorized_keys /root/.ssh/authorized_keys 2>/dev/null

# arquivos recentes e binários em lugar errado
find /tmp /dev/shm /var/tmp -type f -mmin -240 -ls 2>/dev/null
find / -xdev -type f -perm -4000 -mmin -1440 -ls 2>/dev/null

# logins
last -20; lastb -20 2>/dev/null
grep -i 'accepted\|failed password' /var/log/auth.log | tail -40
```

Chave SSH desconhecida em `authorized_keys` = backdoor. Remover **e** rotacionar todas as
chaves, **e** verificar os outros servidores que aceitam a mesma chave.

Para hardening pós-limpeza do servidor, passe para o skill **sentinel**.
