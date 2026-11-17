#!/usr/bin/env python3
"""
scan_tree.py - Static sweep of a folder/repo/PoC looking for malicious content.

Does NOT execute anything from the target tree. Only reads bytes and matches patterns.

Usage:
    python3 scan_tree.py <path> [--json] [--min-score N] [--max-bytes N]

Output: findings ranked by risk score, with file:line and the matched snippet.

AI coding-agent configuration shipped in the tree (.claude/settings*.json,
.mcp.json, CLAUDE.md/AGENTS.md, .cursor/, .vscode/, .gemini/, .codex/, skills,
plugins...) is treated as executable content: hooks, helper commands, MCP
launchers, pre-approved permissions, endpoint overrides, hidden unicode and
prompt-injection phrasing are reported. See references/agent-config-triage.md.

Credential-looking values are masked in every snippet: the scanner never prints
a secret, it only says that one is there.
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
    ("ai_cli_unsafe",
     r"\b(?:claude|gemini|codex|q|cursor-agent)\b[^\n]{0,120}?(?:--dangerously-skip-permissions|--dangerously-bypass-approvals-and-sandbox|--yolo\b|--trust-all-tools|--approval-mode[= ]yolo|--permission-mode[= ]bypassPermissions)",
     8, "Runs an AI coding CLI with its guardrails off (s1ngularity/Nx pattern)"),
]

COMPILED = [(n, re.compile(p, re.I), s, d) for n, p, s, d in RULES]

NPM_HOOKS = re.compile(r'"(preinstall|postinstall|install|prepare|prepublish)"\s*:', re.I)
LONG_LINE = 1200

# ---------------------------------------------------------------- secret masking
# The scanner reports THAT a credential exists, never its value.

SECRET_TOKEN_RX = re.compile(
    r"sk-ant-[A-Za-z0-9_\-]{16,}"
    r"|\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_\-]{20,}"
    r"|\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}|\bgithub_pat_[A-Za-z0-9_]{30,}"
    r"|\bglpat-[A-Za-z0-9_\-]{20,}"
    r"|\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"
    r"|\bAIza[0-9A-Za-z_\-]{35}"
    r"|\bxox[abposr]-[A-Za-z0-9\-]{10,}"
    r"|\b[rs]k_(?:live|test)_[A-Za-z0-9]{16,}"
    r"|\bnpm_[A-Za-z0-9]{36}\b"
    r"|\b\d{8,10}:[A-Za-z0-9_\-]{35}\b"
    r"|\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}"
    r"|(?<=discord\.com/api/webhooks/)\d+/[A-Za-z0-9_\-]{20,}"
    r"|(?<=discordapp\.com/api/webhooks/)\d+/[A-Za-z0-9_\-]{20,}"
)
PRIVATE_KEY_RX = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
# value-in-context: only the named group "v" is masked
SECRET_CTX_RX = [re.compile(p) for p in (
    r"(?i)(?:password|passwd|pwd|secret|token|api[_-]?key|apikey|access[_-]?key|client[_-]?secret)[\"']?\s*[:=]\s*[\"']?(?P<v>[^\s\"'`,;)\]}]{6,})",
    r"(?i)\b(?:PGPASSWORD|MYSQL_PWD|[A-Z_]*PASSWORD|[A-Z_]*TOKEN|[A-Z_]*SECRET|[A-Z_]*API_KEY)=(?P<v>[^\s\"'`;)]{6,})",
    r"(?i)(?<![\w-])--?(?:password|passwd|pass|token|api-key|apikey|secret)[= ](?P<v>[^\s\"'`;)\-][^\s\"'`;)]{5,})",
    r"(?i)\bBearer\s+(?P<v>[A-Za-z0-9._~+/\-]{12,}=*)",
    r"://[^/\s:@\"']{1,64}:(?P<v>[^@\s/\"']{3,})@",
    r"\bmysql(?:dump)?\b[^\n]{0,80}?\s-p(?P<v>[^\s\"']{4,})",
    r"(?i)\bsshpass\s+-p\s*(?P<v>\S{4,})",
)]
PLACEHOLDER_RX = re.compile(
    r"^(?:\$|\$\{|<|\{\{|%|\*{3}|x{4,}|\.\.\.)|(?i:changeme|example|your[_-]|placeholder|redacted|dummy|<|>)")


def _mask_value(v: str) -> str:
    return f"{v[:4]}…[redacted {len(v)} chars]"


def is_placeholder(v: str) -> bool:
    return bool(PLACEHOLDER_RX.search(v))


def find_secrets(text: str) -> list:
    """(kind, start, end) of credential-looking values; placeholders excluded."""
    hits = []
    for m in SECRET_TOKEN_RX.finditer(text):
        hits.append(("token", m.start(), m.end()))
    for m in PRIVATE_KEY_RX.finditer(text):
        hits.append(("private_key", m.start(), m.end()))
    for rx in SECRET_CTX_RX:
        for m in rx.finditer(text):
            v = m.group("v")
            if not is_placeholder(v):
                hits.append(("inline", m.start("v"), m.end("v")))
    return hits


def mask(s: str) -> str:
    if not s:
        return s
    spans = sorted({(a, b) for _, a, b in find_secrets(s)})
    if not spans:
        return s
    out, pos = [], 0
    for a, b in spans:
        if a < pos:          # overlapping span, already masked
            continue
        out.append(s[pos:a])
        out.append("[PRIVATE KEY BLOCK]" if s[a:b].startswith("-----BEGIN") else _mask_value(s[a:b]))
        pos = b
    out.append(s[pos:])
    return "".join(out)


INVISIBLE_RX = re.compile(
    "[\xad\u061c\u180e\u200b-\u200f\u202a-\u202e\u2060-\u2064\u2066-\u2069\ufeff"
    "\U000e0000-\U000e007f\U000e0100-\U000e01ef]")


def snip(s: str, n: int = 180) -> str:
    """Mask BEFORE truncating, so a cut-off secret never survives.
    Invisible/bidi characters are shown as <U+XXXX> so the terminal does not reorder or hide text."""
    s = INVISIBLE_RX.sub(lambda m: f"<U+{ord(m.group(0)):04X}>", s.strip())
    return mask(s)[:n]


# ---------------------------------------------------------------- hidden unicode

BIDI = set(range(0x202A, 0x202F)) | set(range(0x2066, 0x206A)) | {0x200E, 0x200F, 0x061C}
ZERO_WIDTH = {0x200B, 0x200C, 0x200D, 0x2060, 0x2061, 0x2062, 0x2063, 0x2064, 0x180E, 0xFEFF, 0x00AD}


def hidden_unicode(text: str) -> dict:
    """Count invisible characters by class. Emoji ZWJ sequences and a leading BOM are ignored."""
    res = {"bidi": 0, "zero_width": 0, "tags": 0, "vs_supp": 0, "first_line": 0, "tag_text": ""}
    tag_chars = []
    n = len(text)
    for i, ch in enumerate(text):
        cp = ord(ch)
        if cp < 0x00AD:
            continue
        kind = None
        if 0xE0000 <= cp <= 0xE007F:
            kind = "tags"
            if 0xE0020 <= cp <= 0xE007E:
                tag_chars.append(chr(cp - 0xE0000))
        elif 0xE0100 <= cp <= 0xE01EF:
            kind = "vs_supp"
        elif cp in BIDI:
            kind = "bidi"
        elif cp in ZERO_WIDTH:
            if cp == 0xFEFF and i == 0:
                continue
            if cp == 0x200D:   # emoji ZWJ sequence: neighbour is a pictograph
                prev_cp = ord(text[i - 1]) if i else 0
                next_cp = ord(text[i + 1]) if i + 1 < n else 0
                if prev_cp >= 0x2600 or next_cp >= 0x2600:
                    continue
            kind = "zero_width"
        if kind:
            res[kind] += 1
            if not res["first_line"]:
                res["first_line"] = text.count("\n", 0, i) + 1
    res["tag_text"] = "".join(tag_chars)
    return res


# ---------------------------------------------------------------- AI agent configuration
# Files an AI coding agent loads or executes when it is opened in this tree.
# Names verified against vendor docs - see references/agent-config-triage.md.

AGENT_SETTINGS_PATHS = {          # JSON that can run commands / grant permissions
    ".claude/settings.json", ".claude/settings.local.json", ".gemini/settings.json",
    ".cursor/hooks.json", ".vscode/settings.json", ".vscode/tasks.json",
    ".devin/hooks.v1.json", "hooks/hooks.json", ".claude-plugin/plugin.json",
    ".claude-plugin/marketplace.json",
}
AGENT_MCP_PATHS = {               # MCP server launchers
    ".mcp.json", ".cursor/mcp.json", ".vscode/mcp.json", ".devin/mcp_config.json",
    ".devin/mcp_config.local.json", ".gemini/settings.json", ".claude-plugin/plugin.json",
}
AGENT_INSTR_NAMES = {             # instruction files read as context
    "claude.md", "claude.local.md", "agents.md", "agents.local.md", "agent.md", "gemini.md",
    ".cursorrules", ".windsurfrules", ".clinerules", "copilot-instructions.md", "global_rules.md",
}
AGENT_INSTR_SUFFIX = (".instructions.md", ".prompt.md", ".agent.md", ".chatmode.md", ".mdc")
AGENT_INSTR_DIRS = (
    ".claude/rules/", ".claude/commands/", ".claude/agents/", ".claude/skills/",
    ".cursor/rules/", ".windsurf/rules/", ".devin/rules/", ".clinerules/",
    ".github/instructions/", ".github/prompts/", ".github/agents/",
)

ENDPOINT_VARS = {
    "ANTHROPIC_BASE_URL", "ANTHROPIC_BEDROCK_BASE_URL", "ANTHROPIC_VERTEX_BASE_URL",
    "ANTHROPIC_FOUNDRY_BASE_URL", "ANTHROPIC_AWS_BASE_URL", "ANTHROPIC_GOOGLE_CLOUD_BASE_URL",
    "OPENAI_BASE_URL", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "BETA_TRACING_ENDPOINT",
    "OTEL_EXPORTER_OTLP_ENDPOINT",
}
OFFICIAL_HOSTS = {"api.anthropic.com", "api.openai.com", "localhost", "127.0.0.1", "[::1]"}
CRED_VARS = {
    "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_API_KEY", "ANTHROPIC_CUSTOM_HEADERS", "OPENAI_API_KEY",
    "AWS_BEARER_TOKEN_BEDROCK", "ANTHROPIC_FOUNDRY_API_KEY", "ANTHROPIC_AWS_API_KEY", "GEMINI_API_KEY",
}
# (var, score, why) - generic process-injection or guard-lowering variables
ENV_INJECT = {
    "CLAUDE_CODE_SHELL_PREFIX": (8, "wraps every Bash, hook, status line and MCP startup command"),
    "NODE_OPTIONS": (6, "Node runtime options (watch for --require/--import)"),
    "LD_PRELOAD": (9, "injects a shared library into every process"),
    "DYLD_INSERT_LIBRARIES": (9, "injects a library into every process (macOS)"),
    "BASH_ENV": (7, "script sourced by every non-interactive bash"),
    "ENV": (5, "script sourced by sh"),
    "PYTHONSTARTUP": (5, "script run by interactive Python"),
    "PATH": (6, "PATH override - a repo binary can shadow git/node/python"),
    "NODE_EXTRA_CA_CERTS": (6, "extra trusted CA - enables TLS interception"),
    "CODEX_HOME": (8, "moves Codex config home into the repo (CVE-2025-61260 pattern)"),
    "CLAUDE_CONFIG_DIR": (6, "moves the Claude Code config home"),
    "GEMINI_CLI_TRUST_WORKSPACE": (7, "bypasses Gemini CLI folder trust"),
}

NET_EXEC_RX = re.compile(
    r"(?i)\b(?:curl|wget|nc|ncat|socat|telnet|ssh|scp|Invoke-WebRequest|iwr|irm|Invoke-RestMethod|"
    r"DownloadString|base64|certutil|bitsadmin|mshta|python3?\s+-c|node\s+-e|perl\s+-e|ruby\s+-e|eval|iex)\b"
    r"|https?://|/dev/tcp/")
AUTO_EVENTS = {"SessionStart", "Setup", "sessionStart", "workspaceOpen", "InstructionsLoaded"}
SHELLS = {"sh", "bash", "zsh", "dash", "cmd", "cmd.exe", "powershell", "powershell.exe", "pwsh"}
RISKY_BASH_FAMILY = re.compile(
    r"^Bash\(\s*(?:sudo|su|doas|curl|wget|nc|ncat|socat|ssh|scp|rsync|python3?|node|deno|bun|"
    r"bash|sh|zsh|pwsh|powershell|eval|exec|docker|kubectl|aws|gcloud|az|gh|git\s+push|npm\s+publish|"
    r"rm|chmod|chown|dd|mkfs|crontab|systemctl)\b", re.I)
KNOWN_MCP_PACKAGES = {
    "@modelcontextprotocol/server-filesystem", "@modelcontextprotocol/server-memory",
    "@modelcontextprotocol/server-everything", "@modelcontextprotocol/server-sequential-thinking",
    "@modelcontextprotocol/server-github", "@playwright/mcp", "mcp-remote",
    "@upstash/context7-mcp", "mcp-server-fetch", "mcp-server-git", "mcp-server-time",
}

INJECTION_RULES = [(n, re.compile(p, re.I), s, d) for n, p, s, d in [
    ("pi_override",
     r"\b(?:ignore|disregard|forget|override)\s+(?:all\s+|any\s+)?(?:the\s+|your\s+)?(?:previous|prior|above|earlier|system|original)\s+(?:instructions|rules|prompts?|guidelines|directives)",
     7, "Prompt-injection override phrase"),
    ("pi_conceal",
     r"\b(?:do\s+not|don't|never)\s+(?:tell|inform|mention|reveal|show|notify|disclose|report)(?:\s+\w+){0,3}?\s+(?:to\s+)?(?:the\s+)?(?:user|human|developer|reviewer|operator)",
     7, "Tells the agent to hide what it does from the user"),
    ("pi_silent",
     r"\b(?:silently|quietly|covertly|without\s+(?:asking|telling|confirmation|prompting|approval|the\s+user\s+(?:noticing|knowing)))\b",
     4, "Asks for unattended / unannounced action"),
    ("pi_lower_guard",
     r"--dangerously-skip-permissions|--dangerously-bypass-approvals-and-sandbox|--yolo\b|--trust-all-tools|bypassPermissions|disableAllHooks|chat\.tools\.[\w.]*autoApprove|\b(?:disable|turn\s+off|skip|bypass|ignore)\s+(?:the\s+|all\s+|any\s+)?(?:sandbox|permission|approval|security|safety|hook|check|confirmation|guardrail)s?\b",
     5, "Tells the agent to lower its own guardrails"),
    ("pi_secret_exfil",
     r"(?:\.env\b|id_rsa|id_ed25519|\.aws/credentials|\.ssh/|\.npmrc|\.git-credentials|settings\.local\.json|\.claude\.json|\bapi[_ -]?keys?\b|\btokens?\b|\bsecrets?\b|\bcredentials?\b|\bpasswords?\b)[^\n]{0,80}?\b(?:to|into|via|using)\b[^\n]{0,60}?(?:https?://|webhook|curl|wget|\bpost\b|upload|gist|pastebin)",
     7, "Mentions sending secrets somewhere"),
    ("pi_fetch_run",
     r"\b(?:fetch|download|curl|wget|retrieve|load|read)\b[^\n]{0,60}?https?://[^\n]{0,160}?\b(?:and|then)\b[^\n]{0,20}?\b(?:run|execute|eval|source|follow|obey|apply|install)\b",
     6, "Tells the agent to fetch remote content and run or obey it"),
]]
HTML_COMMENT_RX = re.compile(r"<!--(.*?)-->", re.S)
HTML_COMMENT_HOT = re.compile(
    r"(?i)https?://|curl|wget|\bexec|\brun\b|ignore|secret|token|password|credential|\.env|ssh|send|upload|do not tell|base64")
SKILL_BANG_RX = re.compile(r"(?m)(?:^|(?<=\s))!`[^`\n]+`|^```!")
FRONTMATTER_RX = re.compile(r"\A---\s*\n(.*?)\n---", re.S)


def agent_kinds(rel: str) -> set:
    """Which agent-config roles a path plays ('settings', 'mcp', 'instr', 'codex', 'dotenv')."""
    r = rel.lower().replace("\\", "/")
    base = r.rsplit("/", 1)[-1]
    kinds = set()
    for p in AGENT_SETTINGS_PATHS:
        if r == p or r.endswith("/" + p):
            kinds.add("settings")
    for p in AGENT_MCP_PATHS:
        if r == p or r.endswith("/" + p):
            kinds.add("mcp")
    if r == ".codex/config.toml" or r.endswith("/.codex/config.toml"):
        kinds.add("codex")
    if (base in AGENT_INSTR_NAMES or base.endswith(AGENT_INSTR_SUFFIX) or base == "skill.md"
            or any(d in "/" + r for d in AGENT_INSTR_DIRS)):
        if base.endswith((".md", ".mdc", ".txt")) or base in AGENT_INSTR_NAMES:
            kinds.add("instr")
    if base == ".env" or base.startswith(".env."):
        kinds.add("dotenv")
    return kinds


def loads_lenient(text: str):
    """json.loads that also accepts JSONC (comments, trailing commas) as used by VS Code."""
    try:
        return json.loads(text)
    except ValueError:
        pass
    out, i, n, in_str = [], 0, len(text), False
    while i < n:
        c = text[i]
        if in_str:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(text[i + 1]); i += 2; continue
            if c == '"':
                in_str = False
        elif c == '"':
            in_str = True; out.append(c)
        elif text.startswith("//", i):
            j = text.find("\n", i); i = n if j < 0 else j; continue
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2); i = n if j < 0 else j + 2; continue
        else:
            out.append(c)
        i += 1
    cleaned = re.sub(r",(\s*[}\]])", r"\1", "".join(out))
    try:
        return json.loads(cleaned)
    except ValueError:
        return None


def line_of(text: str, needle: str) -> int:
    idx = text.find(needle)
    return text.count("\n", 0, idx) + 1 if idx >= 0 else 0


def url_host(u: str) -> str:
    m = re.match(r"(?i)^[a-z][a-z0-9+.\-]*://(?:[^@/]*@)?(\[[^\]]+\]|[^/:?#]+)", str(u).strip())
    return m.group(1).lower() if m else ""


class AgentCtx:
    def __init__(self, rel: str, text: str, out: list):
        self.rel, self.text, self.out = rel, text, out

    def add(self, rule: str, score: int, desc: str, needle: str = "", snippet: str = ""):
        line = line_of(self.text, needle) if needle else 0
        if not line and needle.startswith('"'):          # TOML keys/names are not quoted
            line = line_of(self.text, needle.strip('"'))
        if not snippet and line:
            snippet = self.text.splitlines()[line - 1]
        self.out.append({"file": self.rel, "line": line, "rule": rule, "score": score,
                         "desc": desc, "snippet": snip(snippet or needle)})


def check_env(ctx: AgentCtx, env: dict, where: str) -> None:
    if not isinstance(env, dict):
        return
    for k, v in env.items():
        ks, vs = str(k), str(v)
        ku = ks.upper()
        if ku in ENDPOINT_VARS or re.search(r"_(?:BASE_URL|ENDPOINT)$", ku):
            host = url_host(vs)
            if host and host in OFFICIAL_HOSTS:
                continue
            score = 9 if ku in ENDPOINT_VARS else 6
            ctx.add("agent_endpoint_override", score,
                    f"{where} sets {ks} -> {host or vs[:60]}: agent traffic (and its auth header) "
                    "goes to that host (CVE-2026-21852 pattern)", needle=f'"{ks}"')
        elif ku in CRED_VARS:
            ctx.add("agent_credential_env", 7,
                    f"{where} sets {ks}: the repo supplies the agent's credential/headers "
                    "(account swap or header injection)", needle=f'"{ks}"')
        elif ku == "NODE_TLS_REJECT_UNAUTHORIZED" and vs.strip() == "0":
            ctx.add("agent_tls_off", 8, f"{where} disables TLS verification for the agent (MITM)",
                    needle=f'"{ks}"')
        elif ku in ENV_INJECT:
            score, why = ENV_INJECT[ku]
            if ku == "NODE_OPTIONS" and re.search(r"(?:^|\s)(?:-r|--require|--import|--loader)\b", vs):
                score, why = 8, "NODE_OPTIONS preloads a module into every node process"
            ctx.add("agent_env_injection", score, f"{where} sets {ks}: {why}", needle=f'"{ks}"')


def check_command(ctx: AgentCtx, cmd: str, where: str, base: int, needle: str) -> None:
    if not cmd:
        return
    score = base
    why = ""
    if NET_EXEC_RX.search(cmd):
        score, why = 9, " - with network/decoder/interpreter indicators"
    ctx.add("agent_exec", score, f"{where} runs a command when the agent starts or acts{why}",
            needle=needle or cmd[:60], snippet=cmd)


def iter_hook_handlers(obj, event=None):
    """Yield (event, handler_dict) for Claude/Cursor/Gemini/Devin hook layouts."""
    if isinstance(obj, dict):
        if any(k in obj for k in ("command", "url", "prompt")) and event:
            yield event, obj
        for k, v in obj.items():
            yield from iter_hook_handlers(v, event or (k if isinstance(v, (list, dict)) else None))
    elif isinstance(obj, list):
        for v in obj:
            yield from iter_hook_handlers(v, event)


def check_hooks(ctx: AgentCtx, hooks) -> None:
    if isinstance(hooks, str):     # plugin.json may point to a hooks file
        ctx.add("agent_hook", 4, f"Plugin hooks file referenced: {hooks} - scan it", needle=hooks)
        return
    for event, h in iter_hook_handlers(hooks):
        auto = event in AUTO_EVENTS
        htype = str(h.get("type", "command"))
        if "command" in h:
            args = h.get("args") or []
            cmd = " ".join([str(h["command"])] + [str(a) for a in args if isinstance(a, (str, int))])
            check_command(ctx, cmd, f"Hook {event}{' (fires on session start, no user action)' if auto else ''}",
                          6 if auto else 5, needle=str(h["command"])[:60])
        elif htype == "http" or "url" in h:
            host = url_host(h.get("url", ""))
            ctx.add("agent_hook_http", 7 if host not in OFFICIAL_HOSTS else 3,
                    f"HTTP hook {event} POSTs every event payload (prompts, tool input) to {host}",
                    needle=str(h.get("url", ""))[:60])
        elif "prompt" in h:
            p = str(h["prompt"])
            for name, rx, sc, d in INJECTION_RULES:
                if rx.search(p):
                    ctx.add(f"hook_{name}", sc, f"{htype} hook {event}: {d}", needle=p[:60], snippet=p)


def check_mcp_servers(ctx: AgentCtx, servers) -> None:
    if not isinstance(servers, dict):
        return
    for name, s in servers.items():
        if not isinstance(s, dict):
            continue
        where = f"MCP server '{name}'"
        cmd = str(s.get("command", "") or "")
        args = [str(a) for a in (s.get("args") or []) if isinstance(a, (str, int))]
        exe = os.path.basename(cmd).lower()
        full = " ".join([cmd] + args)
        needle = f'"{name}"'
        if cmd:
            flags = {a for a in args if a.startswith("-")}
            pkgs = [a for a in args if not a.startswith("-")]
            if exe in {"npx", "bunx", "pnpx"} or (exe in {"pnpm", "yarn"} and "dlx" in args):
                pkg = next((p for p in pkgs if p != "dlx"), "")
                bare = re.sub(r"(?<=.)@[^/@]+$", "", pkg)
                pinned = bare != pkg
                sc = 6 if flags & {"-y", "--yes"} else 5
                if not pinned:
                    sc += 1
                ctx.add("mcp_autofetch", sc,
                        f"{where} downloads and runs '{pkg or '?'}' from npm on every start"
                        f"{'' if pinned else ' (unpinned: whatever is latest)'}", needle=needle, snippet=full)
                check_squat(ctx, bare, where, needle)
                if bare == "mcp-remote":
                    ctx.add("mcp_remote_cve", 5, f"{where} uses mcp-remote - versions < 0.1.16 have "
                            "CVE-2025-6514 (RCE from a malicious server)", needle=needle, snippet=full)
            elif exe in {"uvx", "pipx"} or (exe == "uv" and "run" in args):
                pkg = next((p for p in pkgs if p not in {"run", "tool"}), "")
                pinned = bool(re.search(r"==|@\d", pkg)) or "--from" in flags
                ctx.add("mcp_autofetch", 6 if not pinned else 5,
                        f"{where} downloads and runs '{pkg or '?'}' from PyPI on start"
                        f"{'' if pinned else ' (unpinned)'}", needle=needle, snippet=full)
                check_squat(ctx, re.split(r"[=@<>]", pkg)[0], where, needle)
            elif exe in SHELLS and ({"-c", "/c", "-command", "-Command", "-e", "-enc"} & set(args)):
                check_command(ctx, full, f"{where} launches an inline shell command", 7, needle)
            elif exe == "docker":
                bad = re.search(r"--privileged|docker\.sock|-v\s*/:/|--network[= ]host|--pid[= ]host", full)
                ctx.add("mcp_docker", 8 if bad else 4,
                        f"{where} runs a container{' with host-level access' if bad else ''}",
                        needle=needle, snippet=full)
            elif cmd.startswith(("./", ".\\", "bin/", "scripts/")) or "${CLAUDE_PROJECT_DIR}" in cmd:
                ctx.add("mcp_repo_binary", 5, f"{where} runs an executable shipped in the repo - scan it",
                        needle=needle, snippet=full)
            else:
                check_command(ctx, full, f"{where} launches a local process", 4, needle)
        url = s.get("url") or s.get("httpUrl") or s.get("serverUrl")
        if url:
            host = url_host(url)
            plain = str(url).lower().startswith(("http://", "ws://")) and host not in OFFICIAL_HOSTS
            ctx.add("mcp_remote", 6 if plain else 3,
                    f"{where} talks to remote endpoint {host}{' over plaintext' if plain else ''}: "
                    "it receives prompts and tool data and returns text the model will read",
                    needle=needle, snippet=str(url))
        if s.get("headersHelper"):
            check_command(ctx, str(s["headersHelper"]), f"{where} headersHelper", 6, needle)
        if s.get("trust") is True:
            ctx.add("mcp_trust_all", 7, f"{where} has trust:true - every tool call skips confirmation (Gemini CLI)",
                    needle=needle)
        check_env(ctx, s.get("env"), where)


def check_squat(ctx: AgentCtx, pkg: str, where: str, needle: str) -> None:
    if not pkg or pkg in KNOWN_MCP_PACKAGES:
        return
    if "modelcontextprotocol" in pkg and not pkg.startswith("@modelcontextprotocol/"):
        ctx.add("mcp_typosquat", 8, f"{where}: '{pkg}' borrows the official scope name without being in it",
                needle=needle)
        return
    for known in KNOWN_MCP_PACKAGES:
        if abs(len(known) - len(pkg)) <= 2 and edit_distance(known, pkg) <= 2:
            ctx.add("mcp_typosquat", 8, f"{where}: '{pkg}' is 1-2 edits away from '{known}' (typosquat?)",
                    needle=needle)
            return


def edit_distance(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def check_permissions(ctx: AgentCtx, perms) -> None:
    if not isinstance(perms, dict):
        return
    for r in perms.get("allow") or []:
        r = str(r).strip()
        if re.fullmatch(r"Bash(?:\(\s*\**\s*\))?", r):
            ctx.add("agent_allow_broad", 8, "permissions.allow pre-approves ANY shell command", needle=f'"{r}"')
        elif RISKY_BASH_FAMILY.match(r):
            wild = "*" in r or ":" in r
            ctx.add("agent_allow_risky", 7 if wild else 4,
                    f"permissions.allow pre-approves a network/interpreter/privileged command"
                    f"{' with a wildcard' if wild else ''}", needle=f'"{r}"')
        elif r in ("WebFetch", "WebFetch(domain:*)", "WebFetch(*)"):
            ctx.add("agent_allow_broad", 6, "permissions.allow lets the agent fetch any URL (exfil channel)",
                    needle=f'"{r}"')
        elif re.match(r"^(?:Edit|Write|Read)\(\s*(?://|~|/|\.\./|[A-Za-z]:)", r):
            ctx.add("agent_allow_outside", 4 if r.startswith("Read") else 6,
                    "permissions.allow reaches paths outside the repository", needle=f'"{r}"')
        elif re.fullmatch(r"mcp__[\w-]+(?:__\*|\*)?", r):
            ctx.add("agent_allow_mcp", 4, "permissions.allow pre-approves every tool of an MCP server", needle=f'"{r}"')
    mode = str(perms.get("defaultMode", ""))
    if mode == "bypassPermissions":
        ctx.add("agent_bypass_mode", 8, "defaultMode bypassPermissions: no prompts at all "
                "(ignored from project files since v2.1.257; older versions honored it)", needle=mode)
    elif mode == "auto":
        ctx.add("agent_bypass_mode", 5, "defaultMode auto: classifier instead of prompts (ignored from project files)",
                needle=mode)
    elif mode == "acceptEdits":
        ctx.add("agent_bypass_mode", 3, "defaultMode acceptEdits: file edits are not confirmed", needle=mode)
    for d in perms.get("additionalDirectories") or []:
        d = str(d)
        if d.startswith(("/", "~", "..")) or re.match(r"^[A-Za-z]:", d):
            ctx.add("agent_allow_outside", 6, f"additionalDirectories grants access to {d}", needle=f'"{d}"')


def check_settings_json(ctx: AgentCtx, d: dict, base: str) -> None:
    for key in ("apiKeyHelper", "awsAuthRefresh", "awsCredentialExport", "gcpAuthRefresh",
                "otelHeadersHelper"):
        if d.get(key):
            check_command(ctx, str(d[key]), f"{key} (helper command)", 7, f'"{key}"')
    for key in ("statusLine", "fileSuggestion", "subagentStatusLine"):
        v = d.get(key)
        cmd = v.get("command") if isinstance(v, dict) else (v if isinstance(v, str) else None)
        if cmd:
            check_command(ctx, str(cmd), f"{key} command", 5, f'"{key}"')
    if "hooks" in d:
        check_hooks(ctx, d["hooks"])
    check_permissions(ctx, d.get("permissions"))
    if d.get("enableAllProjectMcpServers") is True:
        ctx.add("agent_mcp_autoapprove", 7, "enableAllProjectMcpServers: the repo approves its own MCP servers "
                "(CVE-2025-59536 pattern; ignored in untrusted folders on current versions)",
                needle='"enableAllProjectMcpServers"')
    if d.get("enabledMcpjsonServers"):
        ctx.add("agent_mcp_autoapprove", 5, "enabledMcpjsonServers: the repo pre-approves named MCP servers",
                needle='"enabledMcpjsonServers"')
    for key in ("skipDangerousModePermissionPrompt", "skipAutoPermissionPrompt"):
        if d.get(key) is True:
            ctx.add("agent_bypass_mode", 6, f"{key}: asks to skip the bypass-mode warning "
                    "(not honored from shared project settings - the intent is the signal)", needle=f'"{key}"')
    if d.get("extraKnownMarketplaces") or d.get("enabledPlugins"):
        ctx.add("agent_plugins", 5, "Repo registers plugin marketplaces / enables plugins - review their source",
                needle='"extraKnownMarketplaces"' if d.get("extraKnownMarketplaces") else '"enabledPlugins"')
    check_env(ctx, d.get("env"), "settings env")
    sec = d.get("security")
    if isinstance(sec, dict) and isinstance(sec.get("folderTrust"), dict) \
            and sec["folderTrust"].get("enabled") is False:
        ctx.add("agent_trust_off", 6, "Gemini security.folderTrust.enabled=false", needle='"folderTrust"')
    tools = d.get("tools")
    if isinstance(tools, dict):
        for t in tools.get("allowed") or []:
            if re.match(r"(?i)run_shell_command(?:\(\s*\))?$|ShellTool$", str(t)):
                ctx.add("agent_allow_broad", 7, "Gemini tools.allowed pre-approves any shell command", needle=str(t))
    # VS Code workspace settings
    for k, v in d.items():
        if re.fullmatch(r"chat\.tools\.(?:[\w]+\.)*autoApprove", str(k)) and v not in (False, None, {}, []):
            ctx.add("vscode_autoapprove", 9, f"{k}: Copilot agent tools run without confirmation "
                    "(CVE-2025-53773 'YOLO' setting)", needle=f'"{k}"')
        elif k == "chat.mcp.autostart" and v not in (False, "never"):
            ctx.add("vscode_mcp_autostart", 4, "chat.mcp.autostart: MCP servers start without a click", needle=f'"{k}"')
        elif k == "task.allowAutomaticTasks" and v in ("on", True):
            ctx.add("vscode_auto_tasks", 6, "task.allowAutomaticTasks on: folderOpen tasks run silently", needle=f'"{k}"')
    if base == "tasks.json":
        for t in d.get("tasks") or []:
            if isinstance(t, dict) and isinstance(t.get("runOptions"), dict) \
                    and t["runOptions"].get("runOn") == "folderOpen":
                cmd = " ".join(str(x) for x in [t.get("command", "")] + list(t.get("args") or []))
                check_command(ctx, cmd, "VS Code task with runOn:folderOpen", 7, '"folderOpen"')
    # plugin manifest / marketplace
    if base == "plugin.json":
        if "hooks" not in d and isinstance(d.get("mcpServers"), str):
            ctx.add("agent_plugins", 4, f"Plugin MCP file referenced: {d['mcpServers']} - scan it",
                    needle='"mcpServers"')
        mon = (d.get("experimental") or {}).get("monitors") if isinstance(d.get("experimental"), dict) else None
        for m in (mon if isinstance(mon, list) else []):
            if isinstance(m, dict) and m.get("command"):
                check_command(ctx, str(m["command"]), "Plugin monitor (background process at session start)",
                              6, str(m["command"])[:60])


def check_codex_toml(ctx: AgentCtx, text: str) -> None:
    try:
        import tomllib
        d = tomllib.loads(text)
    except Exception:                    # old Python or invalid TOML: fall back to regex
        d = None
    if d is None:
        for key, sc, why in (("mcp_servers", 5, "declares MCP servers"), ("notify", 6, "runs a notify command"),
                             ("hooks", 6, "declares hooks"), ("model_providers", 8, "overrides the model provider"),
                             ("openai_base_url", 8, "overrides the API base URL")):
            if re.search(rf"(?m)^\s*\[?{key}\b", text):
                ctx.add("codex_config", sc, f".codex/config.toml {why}", needle=key)
        return
    check_mcp_servers(ctx, d.get("mcp_servers"))
    if d.get("approval_policy") == "never":
        ctx.add("codex_config", 6, "approval_policy = never: Codex never asks", needle="approval_policy")
    if d.get("sandbox_mode") == "danger-full-access":
        ctx.add("codex_config", 7, "sandbox_mode = danger-full-access", needle="sandbox_mode")
    if d.get("notify"):
        check_command(ctx, " ".join(map(str, d["notify"])) if isinstance(d["notify"], list) else str(d["notify"]),
                      "Codex notify (ignored in project config by current versions)", 6, "notify")
    for key in ("model_providers", "openai_base_url", "chatgpt_base_url", "model_provider"):
        if key in d:
            ctx.add("agent_endpoint_override", 8, f".codex/config.toml sets {key} "
                    "(rejected from project config by current Codex; hostile intent on older ones)", needle=key)
    if "hooks" in d:
        check_hooks(ctx, d["hooks"])


def scan_instructions(ctx: AgentCtx, text: str) -> None:
    for name, rx, score, desc in INJECTION_RULES:
        m = rx.search(text)
        if m:
            ln = text.count("\n", 0, m.start()) + 1
            ctx.out.append({"file": ctx.rel, "line": ln, "rule": name, "score": score,
                            "desc": f"[instruction file] {desc}", "snippet": snip(text.splitlines()[ln - 1])})
    hidden = hidden_unicode(text)["tag_text"]          # text smuggled in the Unicode Tags block
    if hidden:
        for name, rx, score, desc in INJECTION_RULES:
            m = rx.search(hidden)
            if m:
                ctx.out.append({"file": ctx.rel, "line": 0, "rule": f"{name}_hidden", "score": min(score + 2, 10),
                                "desc": f"[INVISIBLE tag text] {desc}", "snippet": snip(m.group(0), 140)})
    for m in HTML_COMMENT_RX.finditer(text):
        body = m.group(1)
        if HTML_COMMENT_HOT.search(body):
            ln = text.count("\n", 0, m.start()) + 1
            ctx.out.append({"file": ctx.rel, "line": ln, "rule": "pi_html_comment", "score": 5,
                            "desc": "HTML comment with operational content: invisible when rendered "
                                    "(Claude Code strips block comments; other agents may not)",
                            "snippet": snip(" ".join(body.split()))})
            break
    m = SKILL_BANG_RX.search(text)
    if m:
        ln = text.count("\n", 0, m.start()) + 1
        line = text.splitlines()[ln - 1]
        sc = 8 if NET_EXEC_RX.search(line) else 5
        ctx.out.append({"file": ctx.rel, "line": ln, "rule": "skill_shell_inject", "score": sc,
                        "desc": "Skill/command runs a shell command (!`...`) when invoked, before the model reads it",
                        "snippet": snip(line)})
    fm = FRONTMATTER_RX.match(text)
    if fm:
        head = fm.group(1)
        m = re.search(r"(?mi)^\s*allowed-tools\s*:\s*(.+)$", head)
        if m and re.search(r"(?:^|[\s,\[\"'])Bash(?:\(\s*\*?\s*\))?(?=$|[\s,\]\"'])", m.group(1)):
            ctx.add("skill_allowed_bash", 6, "Skill frontmatter allowed-tools pre-approves any Bash command",
                    needle=m.group(0).strip())
        if re.search(r"(?mi)^\s*hooks\s*:", head):
            ctx.add("skill_hooks", 5, "Skill/agent frontmatter declares hooks - read them", needle="hooks:")
        if re.search(r"(?mi)^\s*permissionMode\s*:\s*bypassPermissions", head):
            ctx.add("agent_bypass_mode", 5, "Subagent asks for permissionMode bypassPermissions", needle="permissionMode")
        if re.search(r"(?mi)^\s*mcpServers\s*:", head):
            ctx.add("skill_mcp", 5, "Subagent frontmatter defines MCP servers", needle="mcpServers:")


def scan_agent_file(path: str, rel: str, kinds: set, out: list, max_bytes: int) -> None:
    try:
        with open(path, "rb") as fh:
            text = fh.read(max_bytes).decode("utf-8", "replace")
    except OSError:
        return
    ctx = AgentCtx(rel, text, out)
    base = os.path.basename(rel).lower()
    out.append({"file": rel, "line": 0, "rule": "agent_config_file", "score": 2,
                "desc": "AI coding-agent config: loaded or executed when an agent opens this tree",
                "snippet": ", ".join(sorted(kinds))})
    if base == "settings.local.json":
        ctx.add("agent_local_settings_shipped", 4,
                "Personal settings.local.json shipped in the tree (holds saved approvals, often with inline secrets)")
    if kinds & {"settings", "mcp"} and base.endswith(".json"):
        d = loads_lenient(text)
        if not isinstance(d, dict):
            ctx.add("agent_config_unparsed", 3, "Agent JSON did not parse - review by hand (regex rules still applied)")
        else:
            if "settings" in kinds:
                check_settings_json(ctx, d, base)
            if "mcp" in kinds:
                check_mcp_servers(ctx, d.get("mcpServers") or d.get("servers"))
            if base == "marketplace.json":
                for p in d.get("plugins") or []:
                    src = p.get("source") if isinstance(p, dict) else None
                    if isinstance(src, (dict, str)) and not str(src).startswith("./"):
                        ctx.add("agent_plugins", 4, "Marketplace pulls a plugin from an external source",
                                needle=str(p.get("name", ""))[:60])
    if "codex" in kinds:
        check_codex_toml(ctx, text)
    if "instr" in kinds:
        scan_instructions(ctx, text)
    if "dotenv" in kinds:
        for m in re.finditer(r"(?m)^\s*(?:export\s+)?([A-Z][A-Z0-9_]*)\s*=", text):
            var = m.group(1)
            if var == "CODEX_HOME" or var in ENDPOINT_VARS or var == "GEMINI_CLI_TRUST_WORKSPACE":
                ln = text.count("\n", 0, m.start()) + 1
                out.append({"file": rel, "line": ln, "rule": "dotenv_agent_redirect",
                            "score": 8 if var == "CODEX_HOME" else 6,
                            "desc": f".env sets {var}: agents that load project .env files pick it up "
                                    "(Gemini CLI loads .env; Codex did before 0.23.0 - CVE-2025-61260)",
                            "snippet": f"{var}=<value not shown>"})
    secrets = []
    for _, a, b in sorted(find_secrets(text), key=lambda t: (t[1], -t[2])):
        if secrets and a < secrets[-1][1]:      # overlapping hit = same value seen by two patterns
            continue
        secrets.append((a, b))
    if secrets:
        first = secrets[0][0]
        ln = text.count("\n", 0, first) + 1
        out.append({"file": rel, "line": ln, "rule": "agent_cfg_secret", "score": 7,
                    "desc": f"{len(secrets)} credential-looking value(s) in committed agent config. TRAP: never "
                            "use or test them; report. Owner's own repo -> hand off to redact",
                    "snippet": snip(text.splitlines()[ln - 1])})


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
    try:   # valid UTF-8 is text, even when dense in non-ASCII (hidden unicode payloads)
        head.decode("utf-8")
        return True
    except UnicodeDecodeError as e:
        if e.start >= len(head) - 3:     # multibyte char cut at the read boundary
            return True
    printable = sum(1 for b in head if 32 <= b < 127 or b in (9, 10, 13))
    return printable / len(head) > 0.85


def suspicious_name(name: str) -> str | None:
    if "\u202e" in name:
        return "RLO character in the name (reversed extension)"
    parts = name.lower().split(".")
    if len(parts) >= 3:
        risky = {"exe", "scr", "bat", "cmd", "com", "pif", "vbs", "js", "jar", "lnk", "hta"}
        decoys = {"pdf", "doc", "docx", "xls", "xlsx", "jpg", "jpeg", "png", "txt", "mp4", "zip"}
        if parts[-1] in risky and parts[-2] in decoys:
            return f"Double extension: .{parts[-2]}.{parts[-1]}"
    return None


# ---------------------------------------------------------------- sweep

def scan_hidden_unicode(text: str, rel: str, agent: bool, out: list) -> None:
    h = hidden_unicode(text)
    if not (h["bidi"] or h["zero_width"] or h["tags"] or h["vs_supp"]):
        return
    counts = ", ".join(f"{k}={h[k]}" for k in ("tags", "bidi", "zero_width", "vs_supp") if h[k])
    if agent:
        score = 9 if h["tags"] else 8 if h["bidi"] else 7
        desc = "Invisible unicode in an agent instruction/config file (Rules File Backdoor pattern)"
    else:
        if h["tags"]:
            score = 8
        elif h["bidi"]:
            score = 6
        elif h["zero_width"] + h["vs_supp"] >= 5:
            score = 3
        else:
            return
        desc = "Invisible unicode (bidi = Trojan Source, CVE-2021-42574; tags = hidden ASCII)"
    snippet = f"[{counts}]"
    if h["tag_text"]:
        snippet += " decoded tag text: " + snip(h["tag_text"], 140)
    out.append({"file": rel, "line": h["first_line"], "rule": "hidden_unicode", "score": score,
                "desc": desc, "snippet": snippet})


def scan_text_file(path: str, rel: str, max_bytes: int, out: list, agent: bool = False) -> None:
    try:
        with open(path, "rb") as fh:
            raw = fh.read(max_bytes)
    except OSError:
        return
    text = raw.decode("utf-8", "replace")
    lines = text.splitlines()

    scan_hidden_unicode(text, rel, agent, out)

    for name, rx, score, desc in COMPILED:
        for m in rx.finditer(text):
            line_no = text.count("\n", 0, m.start()) + 1
            snippet = snip(lines[line_no - 1] if line_no <= len(lines) else m.group(0))
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
            "snippet": snip(lines[line_no - 1]) if line_no <= len(lines) else "",
        })

    ext = os.path.splitext(path)[1].lower()
    if ext in {".js", ".mjs", ".cjs", ".ts", ".py", ".sh", ".ps1", ".php", ".rb"}:
        for i, ln in enumerate(lines, 1):
            if len(ln) > LONG_LINE:
                out.append({
                    "file": rel, "line": i, "rule": "long_line", "score": 5,
                    "desc": f"Line of {len(ln)} chars (possible inline payload)",
                    "snippet": snip(ln, 120) + "...",
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
                "snippet": snip(m.group(0), 160),
            })


def walk(root: str, max_bytes: int) -> tuple[list, int]:
    findings: list = []
    count = 0
    for dirpath, dirnames, filenames in os.walk(root):
        # ".github" is NOT skipped: workflows, copilot-instructions and prompt files live there
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
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

            kinds = agent_kinds(rel)
            if kinds and size <= 20 * 1024 * 1024:
                scan_agent_file(full, rel, kinds, findings, max_bytes)
                scan_text_file(full, rel, max_bytes, findings, agent=True)
                continue

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
        # keep the last path components so ".claude/settings.json" is still recognised
        tail = "/".join(root.replace("\\", "/").split("/")[-3:])
        kinds = agent_kinds(tail)
        if kinds:
            scan_agent_file(root, tail, kinds, findings, args.max_bytes)
            scan_text_file(root, tail, args.max_bytes, findings, agent=True)
        elif ext in BINARY_EXT:
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
    agent_rules = [f for f in findings if f["rule"] != "agent_config_file" and (
        f["rule"].startswith(("agent_", "mcp_", "pi_", "skill_", "vscode_", "codex_", "hook_", "dotenv_"))
        or (f["rule"] == "hidden_unicode" and f["score"] >= 7))]
    if agent_rules:
        top_agent = max(f["score"] for f in agent_rules)
        if top_agent >= 6:
            print(f"AGENT CONFIG: {len(agent_rules)} finding(s), top score {top_agent}. Do NOT open this tree with "
                  "a coding agent (and never 'claude -p' / --init-only in it) until these files are reviewed. "
                  "See references/agent-config-triage.md.")
        else:
            print(f"AGENT CONFIG: {len(agent_rules)} low-severity finding(s). Read the hooks/MCP entries above "
                  "before the first agent session in this tree.")
    if any(f["rule"] == "agent_cfg_secret" for f in findings):
        print("CREDENTIALS: values above are masked. Never use, test or 'validate' them. Third-party repo: "
              "note it as a hygiene IoC. Owner's own repo: hand off to the redact skill.")
    print("These rules are heuristics. The final verdict belongs to the human/agent analysis.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
