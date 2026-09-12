#!/usr/bin/env python3
"""
scan_tree.py - Static sweep of a folder/repo/PoC looking for malicious content.

Does NOT execute anything from the target tree. Only reads bytes and matches patterns.

Usage:
    python3 scan_tree.py <path> [--json] [--min-score N] [--max-bytes N]

Output: findings ranked by risk score, with file:line and the matched snippet.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
from collections import Counter

# ---------------------------------------------------------------- configuration

SKIP_DIRS = {
    ".git", ".svn", ".hg", "node_modules", "venv", ".venv", "env",
    "__pycache__", ".mypy_cache", ".pytest_cache", ".tox", "dist", "build",
    ".gradle", ".idea", ".vscode-test", "vendor", "target", ".next", ".nuxt",
}

TEXT_EXT = {
    ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".py", ".sh", ".bash", ".zsh",
    ".ps1", ".psm1", ".bat", ".cmd", ".vbs", ".php", ".rb", ".pl", ".lua",
    ".java", ".go", ".rs", ".c", ".cpp", ".h", ".cs", ".json", ".yml", ".yaml",
    ".toml", ".xml", ".html", ".htm", ".txt", ".md", ".cfg", ".ini", ".env",
    ".gradle", ".sql", ".r", ".ex", ".exs",
}

BINARY_EXT = {
    ".exe", ".dll", ".so", ".dylib", ".node", ".pyd", ".jar", ".class", ".pyc",
    ".wasm", ".bin", ".scr", ".sys", ".msi", ".apk", ".dex", ".o", ".a", ".lib",
}

AUTORUN_NAMES = {
    "package.json", "setup.py", "pyproject.toml", "makefile", "dockerfile",
    "build.gradle", "build.gradle.kts", "pom.xml", ".envrc", "conanfile.py",
    "binding.gyp", "gemfile", "rakefile", "cargo.toml", "meson.build",
}

# (name, regex, score, explanation)
RULES = [
    ("download_exec_ps",
     r"(?:IEX|Invoke-Expression)\s*\(?\s*(?:New-Object\s+Net\.WebClient|\(?\s*(?:iwr|irm|Invoke-(?:WebRequest|RestMethod)))",
     9, "Downloads and executes code from the network (PowerShell stager)"),
    ("download_pipe_shell",
     r"(?:curl|wget)\s+[^\n|;]{0,200}\|\s*(?:sudo\s+)?(?:ba)?sh\b",
     8, "Downloads and pipes straight into a shell"),
    ("ps_encoded",
     r"powershell(?:\.exe)?[^\n]{0,120}?\s-(?:e|en|enc|encoded|encodedcommand)\s",
     9, "PowerShell with a hidden base64 command"),
    ("ps_stealth_flags",
     r"-(?:w|windowstyle)\s+hidden|-nop\b|-ep\s+bypass|-executionpolicy\s+bypass",
     6, "Hidden / no-policy execution flags"),
    ("lolbin_download",
     r"\b(?:certutil\s+[^\n]{0,80}-urlcache|bitsadmin\s+/transfer|mshta\s+https?://|regsvr32\s+[^\n]{0,60}scrobj\.dll)",
     9, "LOLBin used to download/execute remotely"),
    ("reverse_shell",
     r"(?:/dev/tcp/\d|\bnc\s+(?:-[a-zA-Z]*e|-e)\s|\bbash\s+-i\s*>&|socat\s+[^\n]{0,60}EXEC:)",
     9, "Reverse shell"),
    ("proc_injection",
     r"(?:VirtualAllocEx|WriteProcessMemory|CreateRemoteThread|NtUnmapViewOfSection|QueueUserAPC)",
     7, "Process injection API"),
    ("av_evasion",
     r"(?:Add-MpPreference\s+-Exclusion|Set-MpPreference\s+-Disable|AmsiScanBuffer|amsiInitFailed|Defender.{0,20}(?:disable|exclusion))",
     9, "Attempt to blind/disable the antivirus"),
    ("ransom_destroy",
     r"(?:vssadmin(?:\.exe)?\s+delete\s+shadows|wmic\s+shadowcopy\s+delete|bcdedit[^\n]{0,60}recoveryenabled\s+no|wbadmin\s+delete\s+catalog)",
     10, "Backup/recovery destruction (ransomware)"),
    ("persistence",
     r"(?:schtasks(?:\.exe)?\s+/create|reg(?:\.exe)?\s+add[^\n]{0,80}CurrentVersion\\\\?Run|New-Service\b|sc(?:\.exe)?\s+create\s|crontab\s+-|/etc/cron\.|LD_PRELOAD|authorized_keys)",
     6, "Persistence mechanism"),
    ("dyn_exec",
     r"(?:\beval\s*\(|\bexec\s*\(|\bnew\s+Function\s*\(|\bassert\s*\(\s*\$_|\bsetTimeout\s*\(\s*[\"'])",
     4, "Dynamic code execution"),
    ("b64_decode_call",
     r"(?:FromBase64String|atob\s*\(|base64\s*\.?\s*b64decode|Buffer\.from\s*\([^,)]{1,40},\s*['\"]base64|base64\s+-d\b|base64\s+--decode)",
     4, "Base64 decoding"),
    ("b64_blob",
     r"['\"][A-Za-z0-9+/]{220,}={0,2}['\"]",
     5, "Long embedded base64 blob"),
    ("charcode_obf",
     r"(?:String\.fromCharCode\s*\((?:\s*\d+\s*,){8,}|(?:\[char\]\s*\d+\s*[+,]\s*){6,}|(?:chr\(\d+\)\s*\+\s*){6,})",
     6, "String assembled byte by byte (obfuscation)"),
    ("hexname_obf",
     r"_0x[0-9a-f]{4,6}\b",
     4, "Hex identifiers (javascript-obfuscator)"),
    ("webshell_php",
     r"(?:eval|assert|system|passthru|shell_exec|popen)\s*\(\s*\$_(?:POST|GET|REQUEST|COOKIE|SERVER)",
     10, "PHP webshell"),
    ("child_process",
     r"(?:require\s*\(\s*['\"]child_process['\"]|from\s+['\"]child_process['\"]|\bsubprocess\.(?:Popen|call|run|check_output)|\bos\.system\s*\()",
     3, "Executes a system command"),
    ("cred_theft",
     r"(?:Login\s?Data|Local\s?State|logins\.json|key4\.db|cookies\.sqlite|wallet\.dat|MetaMask|\.ssh[/\\\\]id_rsa|\.aws[/\\\\]credentials|\.git-credentials|\.npmrc|discord[/\\\\]Local\s?Storage|Telegram\s?Desktop[/\\\\]tdata)",
     8, "Access to credential/wallet files (infostealer)"),
    ("exfil_channel",
     r"(?:discord(?:app)?\.com/api/webhooks/|api\.telegram\.org/bot|pastebin\.com/raw|gist\.githubusercontent\.com/[^\s\"']{0,80}/raw)",
     8, "Typical exfiltration/C2 channel"),
    ("miner",
     r"(?:stratum\+(?:tcp|ssl)://|xmrig|nicehash|nanopool|--donate-level|randomx)",
     8, "Cryptominer"),
    ("dyndns_c2",
     r"\b[\w.-]+\.(?:duckdns\.org|no-ip\.(?:org|com|biz)|ngrok(?:-free)?\.(?:io|app)|serveo\.net|hopto\.org|zapto\.org)\b",
     7, "Dynamic domain typical of C2"),
    ("onion",
     r"\b[a-z2-7]{16,56}\.onion\b",
     7, "Tor address"),
    ("raw_ip_url",
     r"https?://(?:\d{1,3}\.){3}\d{1,3}(?::\d{2,5})?",
     5, "URL with a raw IP (no domain)"),
    ("env_dump",
     r"(?:JSON\.stringify\s*\(\s*process\.env|\bdict\s*\(\s*os\.environ|os\.environ\s*\)\s*\)|process\.env\s*\)\s*[,)])",
     7, "Serialization of the entire environment (secret exfil)"),
    ("temp_write_exec",
     r"(?:%TEMP%|\$env:TEMP|/tmp/\.[\w-]+|%APPDATA%)[^\n]{0,60}\.(?:exe|dll|ps1|bat|scr|vbs|jar)",
     6, "Writes an executable into a temp directory"),
]

COMPILED = [(n, re.compile(p, re.I), s, d) for n, p, s, d in RULES]

NPM_HOOKS = re.compile(r'"(preinstall|postinstall|install|prepare|prepublish)"\s*:', re.I)
LONG_LINE = 1200


# ---------------------------------------------------------------- utilities

def entropy(data: bytes) -> float:
    if not data:
        return 0.0
    counts = Counter(data)
    n = len(data)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())


def sha256(path: str, limit: int = 64 * 1024 * 1024) -> str:
    h = hashlib.sha256()
    try:
        with open(path, "rb") as fh:
            read = 0
            while read < limit:
                chunk = fh.read(1024 * 1024)
                if not chunk:
                    break
                h.update(chunk)
                read += len(chunk)
    except OSError:
        return "?"
    return h.hexdigest()


def is_probably_text(head: bytes) -> bool:
    if b"\x00" in head:
        return False
    if not head:
        return True
    printable = sum(1 for b in head if 32 <= b < 127 or b in (9, 10, 13))
    return printable / len(head) > 0.85


def suspicious_name(name: str) -> str | None:
    if "‮" in name:
        return "RLO character in the name (reversed extension)"
    parts = name.lower().split(".")
    if len(parts) >= 3:
        risky = {"exe", "scr", "bat", "cmd", "com", "pif", "vbs", "js", "jar", "lnk", "hta"}
        decoys = {"pdf", "doc", "docx", "xls", "xlsx", "jpg", "jpeg", "png", "txt", "mp4", "zip"}
        if parts[-1] in risky and parts[-2] in decoys:
            return f"Double extension: .{parts[-2]}.{parts[-1]}"
    return None


# ---------------------------------------------------------------- sweep

def scan_text_file(path: str, rel: str, max_bytes: int, out: list) -> None:
    try:
        with open(path, "rb") as fh:
            raw = fh.read(max_bytes)
    except OSError:
        return
    text = raw.decode("utf-8", "replace")
    lines = text.splitlines()

    for name, rx, score, desc in COMPILED:
        for m in rx.finditer(text):
            line_no = text.count("\n", 0, m.start()) + 1
            snippet = (lines[line_no - 1].strip() if line_no <= len(lines) else m.group(0))[:180]
            out.append({
                "file": rel, "line": line_no, "rule": name,
                "score": score, "desc": desc, "snippet": snippet,
            })
            break  # 1 finding per rule/file keeps the report from flooding

    base = os.path.basename(path).lower()
    if base == "package.json" and NPM_HOOKS.search(text):
        m = NPM_HOOKS.search(text)
        line_no = text.count("\n", 0, m.start()) + 1
        out.append({
            "file": rel, "line": line_no, "rule": "npm_install_hook", "score": 7,
            "desc": "npm install hook executes code on 'npm install'",
            "snippet": lines[line_no - 1].strip()[:180] if line_no <= len(lines) else "",
        })

    ext = os.path.splitext(path)[1].lower()
    if ext in {".js", ".mjs", ".cjs", ".ts", ".py", ".sh", ".ps1", ".php", ".rb"}:
        for i, ln in enumerate(lines, 1):
            if len(ln) > LONG_LINE:
                out.append({
                    "file": rel, "line": i, "rule": "long_line", "score": 5,
                    "desc": f"Line of {len(ln)} chars (possible inline payload)",
                    "snippet": ln[:120] + "...",
                })
                break


def scan_binary_file(path: str, rel: str, size: int, out: list) -> None:
    try:
        with open(path, "rb") as fh:
            sample = fh.read(1024 * 1024)
    except OSError:
        return
    ent = entropy(sample)
    ext = os.path.splitext(path)[1].lower()

    out.append({
        "file": rel, "line": 0, "rule": "binary_present", "score": 5,
        "desc": f"Binary in the tree ({size} bytes, entropy {ent:.2f})",
        "snippet": f"sha256={sha256(path)[:32]}...",
    })
    if ent > 7.4 and ext in {".exe", ".dll", ".so", ".node", ".pyd", ".bin"}:
        out.append({
            "file": rel, "line": 0, "rule": "high_entropy", "score": 3,
            "desc": f"Entropy {ent:.2f} - packed/encrypted, static analysis limited",
            "snippet": "",
        })

    # ASCII strings from the binary, run through the same rules
    text = "".join(chr(b) if 32 <= b < 127 else "\n" for b in sample)
    for name, rx, score, desc in COMPILED:
        m = rx.search(text)
        if m:
            out.append({
                "file": rel, "line": 0, "rule": f"str:{name}",
                "score": max(score - 1, 1), "desc": f"[strings] {desc}",
                "snippet": m.group(0)[:160],
            })


def walk(root: str, max_bytes: int) -> tuple[list, int]:
    findings: list = []
    count = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".git")]
        for fn in filenames:
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root).replace("\\", "/")
            try:
                size = os.path.getsize(full)
            except OSError:
                continue
            count += 1

            warn = suspicious_name(fn)
            if warn:
                findings.append({"file": rel, "line": 0, "rule": "suspicious_name",
                                 "score": 9, "desc": warn, "snippet": fn})

            if fn.lower() in AUTORUN_NAMES:
                findings.append({"file": rel, "line": 0, "rule": "autorun_file", "score": 2,
                                 "desc": "File with an auto-execution trigger - review by hand",
                                 "snippet": fn})

            ext = os.path.splitext(fn)[1].lower()
            if ext in BINARY_EXT:
                scan_binary_file(full, rel, size, findings)
                continue
            if size > 20 * 1024 * 1024:
                continue
            if ext in TEXT_EXT:
                scan_text_file(full, rel, max_bytes, findings)
                continue
            try:
                with open(full, "rb") as fh:
                    head = fh.read(4096)
            except OSError:
                continue
            if is_probably_text(head):
                scan_text_file(full, rel, max_bytes, findings)
            elif size > 0:
                scan_binary_file(full, rel, size, findings)
    return findings, count


# ---------------------------------------------------------------- report

def main() -> int:
    ap = argparse.ArgumentParser(description="Static sweep for malicious content")
    ap.add_argument("path")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--min-score", type=int, default=1)
    ap.add_argument("--max-bytes", type=int, default=2 * 1024 * 1024,
                    help="bytes read per text file (default 2MB)")
    args = ap.parse_args()

    root = os.path.abspath(args.path)
    if not os.path.exists(root):
        print(f"error: path does not exist: {root}", file=sys.stderr)
        return 2

    if os.path.isfile(root):
        findings: list = []
        base = os.path.basename(root)
        ext = os.path.splitext(base)[1].lower()
        size = os.path.getsize(root)
        warn = suspicious_name(base)
        if warn:
            findings.append({"file": base, "line": 0, "rule": "suspicious_name",
                             "score": 9, "desc": warn, "snippet": base})
        if ext in BINARY_EXT:
            scan_binary_file(root, base, size, findings)
        else:
            scan_text_file(root, base, args.max_bytes, findings)
        total = 1
    else:
        findings, total = walk(root, args.max_bytes)

    findings = [f for f in findings if f["score"] >= args.min_score]
    findings.sort(key=lambda f: (-f["score"], f["file"], f["line"]))

    if args.json:
        print(json.dumps({"root": root, "files_scanned": total, "findings": findings},
                         indent=2, ensure_ascii=False))
        return 0

    print(f"target : {root}")
    print(f"files scanned: {total}")
    print(f"findings: {len(findings)}\n")

    if not findings:
        print("No suspicious pattern found in the analyzed scope.")
        print("WARNING: absence of findings does not prove it is clean - only that these rules did not match.")
        return 0

    for f in findings:
        loc = f"{f['file']}:{f['line']}" if f["line"] else f["file"]
        print(f"[{f['score']:>2}] {f['rule']:<22} {loc}")
        print(f"     {f['desc']}")
        if f["snippet"]:
            print(f"     > {f['snippet']}")
        print()

    top = max(f["score"] for f in findings)
    print("-" * 60)
    if top >= 9:
        print("TRIAGE: high-severity indicators. Treat as hostile until proven otherwise.")
    elif top >= 6:
        print("TRIAGE: relevant indicators. Review each finding by hand before any execution.")
    else:
        print("TRIAGE: weak signals. May be false positives - confirm in context.")
    print("These rules are heuristics. The final verdict belongs to the human/agent analysis.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
