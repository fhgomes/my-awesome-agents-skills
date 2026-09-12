# Incident Response — Possibly Compromised Host

Applies when the user says: "I already ran it", "I think I caught a virus", "Defender flagged it",
"weird stuff is showing up", "my account was stolen".

Priority: **contain → preserve → scope → credentials → eradicate**. In that order.

---

## First 15 minutes

### 1. Contain
- Disconnect from the network (Wi-Fi off / cable out).
- **Do not power off** the machine if active ransomware is suspected or forensics may be
  needed — RAM holds keys and evidence. Power off only if encryption is in progress.
- Do not run a "cleanup" yet. Cleaning before understanding erases the scope evidence.

### 2. Preserve
```powershell
Get-FileHash "C:\path\sample.exe" -Algorithm SHA256
Copy-Item "C:\path\sample.exe" "$env:USERPROFILE\Desktop\quarantine\sample.exe.bin" -Force
```
Renaming to `.bin` prevents an accidental double-click. Note: time of the run, what the user
clicked, where it came from, what appeared on screen.

### 3. What Defender has already seen
```powershell
Get-MpThreatDetection | Sort-Object InitialDetectionTime -Descending |
  Select-Object InitialDetectionTime,ThreatID,Resources,ActionSuccess | Format-List

Get-MpThreat | Select-Object ThreatName,SeverityID,DidThreatExecute,Resources | Format-List
```
`DidThreatExecute = True` changes everything: it is no longer a "suspicious file", it is a compromise.

---

## Scope — what actually ran

### Processes and origin
```powershell
Get-CimInstance Win32_Process |
  Select-Object ProcessId,ParentProcessId,Name,ExecutablePath,CommandLine |
  Where-Object { $_.ExecutablePath -match '\\Temp\\|\\AppData\\|\\Downloads\\|\\Public\\|\\ProgramData\\' } |
  Format-List
```
The parent-child chain tells the story: `winword.exe → powershell.exe` is macro execution.
`explorer.exe → wscript.exe` is a user who opened a `.vbs`.

### Network
```powershell
Get-NetTCPConnection -State Established | ForEach-Object {
  [PSCustomObject]@{
    Remote = "$($_.RemoteAddress):$($_.RemotePort)"
    PID    = $_.OwningProcess
    Proc   = (Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue).Name
  }
} | Sort-Object Proc | Format-Table -AutoSize
```
Look for: a user process talking to a raw IP on a high port, a persistent connection to an
unknown host, traffic to the Discord/Telegram API coming from a process that is not the app.

### PowerShell history (frequently forgotten by the attacker)
```powershell
Get-Content "$env:APPDATA\Microsoft\Windows\PowerShell\PSReadLine\ConsoleHost_history.txt" -Tail 80
```

### Relevant events
```powershell
# processes created in the last hour (requires process creation auditing enabled)
Get-WinEvent -FilterHashtable @{LogName='Security'; Id=4688; StartTime=(Get-Date).AddHours(-1)} -MaxEvents 60 -ErrorAction SilentlyContinue |
  Select-Object TimeCreated,@{n='Msg';e={$_.Message -split "`n" | Select-String 'New Process Name|Command Line'}}

# PowerShell script block logging
Get-WinEvent -FilterHashtable @{LogName='Microsoft-Windows-PowerShell/Operational'; Id=4104} -MaxEvents 40 -ErrorAction SilentlyContinue |
  Select-Object TimeCreated,Message | Format-List
```

### Recently created files in the usual places
```powershell
Get-ChildItem "$env:TEMP","$env:APPDATA","$env:LOCALAPPDATA","$env:ProgramData","$env:USERPROFILE\Downloads" -Recurse -File -ErrorAction SilentlyContinue |
  Where-Object { $_.LastWriteTime -gt (Get-Date).AddHours(-6) -and $_.Extension -match '^\.(exe|dll|ps1|bat|vbs|js|scr|lnk|jar|hta)$' } |
  Select-Object FullName,Length,LastWriteTime | Format-Table -AutoSize
```

---

## Persistence — enumerate before removing

```powershell
# Run keys
Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run',
                 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Run',
                 'HKCU:\Software\Microsoft\Windows\CurrentVersion\RunOnce',
                 'HKLM:\Software\Microsoft\Windows\CurrentVersion\RunOnce' -ErrorAction SilentlyContinue

# Startup folders
Get-ChildItem "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup",
              "$env:ProgramData\Microsoft\Windows\Start Menu\Programs\Startup" -ErrorAction SilentlyContinue

# Recently created scheduled tasks
Get-ScheduledTask | Where-Object { $_.Date -gt (Get-Date).AddDays(-14) } |
  Select-Object TaskName,TaskPath,Date,@{n='Action';e={$_.Actions.Execute}} | Format-Table -AutoSize

# Services with a binary outside System32
Get-CimInstance Win32_Service | Where-Object { $_.PathName -notmatch 'System32|Program Files' } |
  Select-Object Name,State,StartMode,PathName | Format-Table -AutoSize

# WMI event subscription (fileless persistence)
Get-CimInstance -Namespace root\Subscription -ClassName __EventFilter -ErrorAction SilentlyContinue
Get-CimInstance -Namespace root\Subscription -ClassName CommandLineEventConsumer -ErrorAction SilentlyContinue

# Exclusions planted in Defender (attacker blinding the defense)
Get-MpPreference | Select-Object -ExpandProperty ExclusionPath
Get-MpPreference | Select-Object -ExpandProperty ExclusionProcess
```

A Defender exclusion the user did not create is strong evidence of compromise.

---

## Credentials — the part that matters most

The most common commodity malware category today is the **infostealer**. Within seconds it
collects: passwords saved in the browser, session cookies (which bypass MFA), Discord tokens,
crypto wallets, SSH keys, `.env` files, AWS/gcloud credentials.

If execution succeeded, **assume every credential on that machine has leaked**.

Rotate **from another clean device**, in this order:
1. Primary e-mail (it is the recovery key for everything else) — password + **sign out of all sessions**
2. Password manager — master password
3. Financial and crypto accounts (move funds if there was a hot wallet on the machine)
4. GitHub/GitLab: password, revoke PATs and OAuth apps, replace the SSH key
5. Cloud: rotate AWS/GCP/Azure access keys, revoke service accounts
6. Social networks and Discord/Telegram — sign out of all sessions
7. Corporate VPN, server SSH keys (and review `authorized_keys` on the servers)

**Terminating sessions is as important as changing the password.** A stolen cookie keeps
working after the password change and does not prompt for MFA.

Changing a password *on the infected machine* is useless — the stealer captures the new one.

---

## Eradication

Full scan, now with remediation enabled:
```powershell
Update-MpSignature
Start-MpScan -ScanType FullScan
Get-MpThreatDetection | Sort-Object InitialDetectionTime -Descending | Select-Object -First 20
```

Offline scan (runs before Windows loads — catches what hides at runtime):
```powershell
Start-MpWDOScan   # reboots the machine
```

### When to reimage (be frank with the user)
A clean reinstall is the only reliable remediation when:
- The malware ran with administrator privileges
- There are signs of a rootkit/bootkit, or the AV cannot remove it
- Ransomware encrypted files
- The machine holds production, customer or crypto wallet credentials
- The scope cannot be determined with confidence

Do not promise "I cleaned it, it's safe" when the evidence does not support it. State what
was verified, what was not, and recommend reimaging when warranted.

After reimaging: restore **data**, never executables or installers from a backup taken before
the infection without verification.

---

## Ransomware — specifics

- **Do not pay** — it does not guarantee the key and it funds the operation.
- Do not rename or "fix" the encrypted files.
- Preserve: the ransom note + 2-3 encrypted files + the original versions if they exist in
  a backup — they help identify the family.
- Check whether a public decryptor exists (No More Ransom) for the identified family.
- Check shadow copies before they get deleted: `vssadmin list shadows`
- Isolate backups **immediately** — modern ransomware seeks out and encrypts network and
  cloud-synced backups.
- In a corporate environment holding personal data: there are legal notification deadlines
  (e.g. GDPR, LGPD). Point out that the obligation exists, without giving legal advice.

---

## Compromised Linux / VPS

```bash
# processes and network
ps auxf
ss -tunap | grep ESTAB
lsof -i -P -n 2>/dev/null | grep ESTABLISHED

# persistence
crontab -l; ls -la /etc/cron.*; cat /etc/crontab
systemctl list-units --type=service --state=running
ls -la /etc/systemd/system/ /root/.ssh/ ~/.ssh/
cat ~/.ssh/authorized_keys /root/.ssh/authorized_keys 2>/dev/null

# recent files and binaries in the wrong place
find /tmp /dev/shm /var/tmp -type f -mmin -240 -ls 2>/dev/null
find / -xdev -type f -perm -4000 -mmin -1440 -ls 2>/dev/null

# logins
last -20; lastb -20 2>/dev/null
grep -i 'accepted\|failed password' /var/log/auth.log | tail -40
```

An unknown SSH key in `authorized_keys` = backdoor. Remove it **and** rotate all keys,
**and** check the other servers that accept the same key.

For post-cleanup server hardening, hand over to the **sentinel** skill.
