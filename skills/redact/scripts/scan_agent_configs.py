#!/usr/bin/env python3
"""
scan_agent_configs.py - audit AI coding-agent config files for secrets.

Why a separate scanner: approving a command with "Yes, and don't ask again" in
Claude Code saves that approval in .claude/settings.local.json as a
permissions.allow rule, often the exact command line. A password typed inline
(PGPASSWORD=... psql, mysql -p..., curl -u user:pass, -H "Authorization: ...")
is then stored in plain text, in a shape that provider-format scanners do not
recognize. Claude Code keeps the file out of git only through the machine's
GLOBAL git excludes, so another clone, CI, `git add -f` or a Docker `COPY .`
ships it.

What it does, for every directory tree given (nested repos included):
  - finds agent config files: Claude Code, Cursor, VS Code, Gemini CLI, Codex,
    Devin, Continue, Aider, SpecStory (see AGENT_FILES below)
  - parses JSON/TOML (permission lists, MCP env/headers/args, env blocks) and
    scans the text formats line by line
  - flags inline credentials in command lines + provider-format tokens
  - per git repo: is the file tracked, was it ever in history (and which
    secrets old versions held), is it ignored by the PROJECT .gitignore or only
    by the global excludes, was it committed by/with Claude
  - Dockerfiles that COPY/ADD the whole context without a .dockerignore that
    excludes the agent files

OUTPUT NEVER CONTAINS A SECRET VALUE. A finding = file, JSON path or line,
rule, and a masked preview: the first 2 characters (only for values of 8+
characters) and the length. No snippets, no hashes. Names of env vars and
headers are printed; they are not secrets.

Exit code: 0 = nothing found, 1 = findings, 2 = usage error.
Standard library only. Sends nothing anywhere.

Usage:
    python3 scan_agent_configs.py <dir> [<dir> ...]
    python3 scan_agent_configs.py <dir> --json
    python3 scan_agent_configs.py <dir> --no-history        # skip git history
    python3 scan_agent_configs.py <dir> --no-transcripts    # skip *.jsonl logs
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from collections import Counter, defaultdict

try:
    import tomllib  # Python 3.11+
except ImportError:  # pragma: no cover
    tomllib = None

SEVERITY_ORDER = {"critical": 4, "high": 3, "medium": 2, "low": 1}

# Never walked. Agent dirs (.claude, .cursor, ...) are deliberately NOT here.
SKIP_DIRS = {
    ".git", ".svn", ".hg", "node_modules", "venv", ".venv", "__pycache__",
    ".mypy_cache", ".pytest_cache", ".tox", ".gradle", ".idea", ".next", ".nuxt",
    ".terraform", "target", "dist", "build", "coverage", ".cache", "site-packages",
}

# Inside a .claude/ dir: authored content (covered by scan_secrets.py) and caches.
SKIP_UNDER_CLAUDE = {"plugins", "skills", "commands", "agents", "output-styles",
                     "workflows", "themes", "cache", "statsig", "shell-snapshots",
                     "image-cache", "usage-data", "paste-cache", "file-history",
                     "todos", "plans", "debug", "tasks", "session-env", "sessions"}

# (regex on the "/"-joined path, kind, label)
# kind: json | toml | text | transcript | auto (by extension) | name-only
AGENT_FILES = [
    (r"(^|/)\.claude/settings\.local\.json$", "json",
     "Claude Code project-local settings (stores 'don't ask again' approvals)"),
    (r"(^|/)\.claude/settings\.json$", "json",
     "Claude Code settings (shared project file, or ~/.claude/settings.json)"),
    (r"(^|/)\.mcp\.json$", "json", "Project MCP servers (Claude Code; VS Code native format)"),
    (r"(^|/)\.claude\.json(\.[^/]*)?$", "json",
     "~/.claude.json or a backup of it (account, per-project MCP servers, state)"),
    (r"(^|/)\.claude/\.credentials\.json$", "name-only", "Claude Code login credentials file"),
    (r"(^|/)\.claude/projects/.+\.jsonl(\.[^/]*)?$", "transcript",
     "Claude Code session transcript (tool calls and output, plain text)"),
    (r"(^|/)\.claude/history\.jsonl$", "transcript",
     "Claude Code prompt history (typed prompts and ! shell commands)"),
    (r"(^|/)\.claude/(agent-memory|projects/[^/]+/memory)/.+\.md$", "text",
     "Claude Code memory notes"),
    (r"(^|/)\.claude/rules/.+\.md$", "text", "Claude Code rules"),
    (r"(^|/)CLAUDE(\.local)?\.md$", "text", "CLAUDE.md / CLAUDE.local.md"),
    (r"(^|/)\.cursor/mcp\.json$", "json", "Cursor MCP servers"),
    (r"(^|/)\.vscode/mcp\.json$", "json", "VS Code MCP servers"),
    (r"(^|/)\.gemini/settings\.json$", "json", "Gemini CLI settings (mcpServers, tools.allowed)"),
    (r"(^|/)\.codex/config\.toml$", "toml", "Codex config (mcp_servers)"),
    (r"(^|/)\.codex/rules/[^/]+\.rules$", "text", "Codex approved-command rules"),
    (r"(^|/)\.codex/history\.jsonl$", "transcript", "Codex history"),
    (r"(^|/)\.devin/config\.local\.json$", "json",
     "Devin project-local config (gitignored overrides: permissions, hooks)"),
    (r"(^|/)\.devin/config\.json$", "json",
     "Devin project settings (permissions, hooks, read_config_from)"),
    (r"(^|/)\.devin/mcp_config\.local\.json$", "json",
     "Devin project-local MCP servers (gitignored)"),
    (r"(^|/)\.devin/mcp_config\.json$", "json", "Devin project MCP servers"),
    (r"(^|/)\.devin/hooks\.v1\.json$", "json",
     "Devin lifecycle hooks (shell commands on agent events)"),
    (r"(^|/)\.devin-plugin/plugin\.json$", "json",
     "Devin plugin manifest (can declare MCP servers and hooks)"),
    (r"(^|/)devin/mcp_config\.json$", "json",
     "Devin user MCP servers (~/.config/devin or %APPDATA%/devin)"),
    (r"(^|/)devin/config\.json$", "json",
     "Devin user settings (~/.config/devin or %APPDATA%/devin)"),
    (r"(^|/)\.continue/mcpServers/[^/]+\.(ya?ml|json)$", "auto", "Continue MCP server"),
    (r"(^|/)\.continue/config\.(ya?ml|json)$", "auto", "Continue config"),
    (r"(^|/)\.aider\.conf\.ya?ml$", "text", "Aider config (may hold API keys)"),
    (r"(^|/)\.aider\.(chat\.history\.md|input\.history)$", "text", "Aider history"),
    (r"(^|/)\.specstory/.+\.md$", "text", "SpecStory saved agent chat"),
]
AGENT_RX = [(re.compile(rx), kind, label) for rx, kind, label in AGENT_FILES]

# Personal files: never meant to leave the machine.
LOCAL_ONLY = re.compile(r"(^|/)(\.claude/settings\.local\.json|\.claude\.json(\.[^/]*)?|"
                        r"\.claude/\.credentials\.json|CLAUDE\.local\.md|"
                        r"\.claude/projects/.+|\.claude/history\.jsonl|"
                        r"\.devin/config\.local\.json|\.devin/mcp_config\.local\.json|"
                        r"\.codex/history\.jsonl|\.aider\.(chat\.history\.md|input\.history))$")

# ------------------------------------------------------------------ rules
# Inline credentials in command lines. Group "v" = secret, "n" = name (printed).
_V = r"(?P<v>'[^']*'|\"[^\"]*\"|[^\s'\"|;&]+)"
_SECRET_NAME = (r"[A-Za-z0-9_]*(?:PASS(?:WORD|WD)?|PWD|TOKEN|SECRET|API_?KEY|APIKEY|"
                r"ACCESS_KEY|PRIVATE_KEY|AUTH(?!OR)|CREDENTIALS?|DSN|DATABASE_URL|"
                r"CONN(?:ECTION)?_?STR(?:ING)?)[A-Za-z0-9_]*")
INLINE_RULES = [
    ("env_assign", re.compile(
        r"(?:^|[\s;&|(`'\"])(?:export\s+|set\s+|env\s+)?(?P<n>" + _SECRET_NAME + r")=" + _V, re.I),
     "high", "Secret in a VAR=value assignment or export (PGPASSWORD=... psql, export X_TOKEN=...)"),
    ("mysql_p", re.compile(
        r"\b(?:mysql|mysqldump|mysqladmin|mariadb|mariadb-dump)\b[^\n]*?\s-p"
        r"(?P<v>'[^']+'|\"[^\"]+\"|[^\s'\"-][^\s'\"]*)"),
     "high", "MySQL/MariaDB password glued to -p"),
    ("password_flag", re.compile(
        r"(?i)(?<![\w-])--(?P<n>password|passwd|pass|pwd|token|api[-_]?key|apikey|secret|"
        r"client[-_]secret|access[-_]token|auth[-_]token|private[-_]key|secret[-_]key|"
        r"bearer|basic[-_]auth|sas[-_]token|webhook[-_]secret)(?:=|\s+)" + _V),
     "high", "Credential passed as a command-line flag (--password, --token, --api-key ...)"),
    ("curl_user", re.compile(
        r"\b(?:curl|wget|http|https|xh)\b[^\n]*?\s(?:-u\s*|--user[=\s]+|--http-user[=\s]+)"
        r"['\"]?(?P<n>[^\s'\":]+):(?P<v>[^\s'\"]+)"),
     "high", "user:password passed to curl/wget -u"),
    ("auth_header", re.compile(
        r"(?i)(?:-H|--header)[=\s]*(?P<q>['\"])\s*(?P<n>[A-Za-z0-9-]+)\s*:\s*(?P<v>[^'\"\n]*)(?P=q)"),
     "high", "Credential in an HTTP header on the command line (-H \"Authorization: ...\")"),
    ("auth_header", re.compile(
        r"(?i)(?:-H|--header)[=\s]*(?P<n>[A-Za-z0-9-]+):(?P<v>[^\s'\"]+)"),
     "high", "Credential in an HTTP header on the command line (-H \"Authorization: ...\")"),
    ("url_userinfo", re.compile(
        r"\b[a-z][a-z0-9+.\-]*://(?P<n>[^\s:@/'\"]*):(?P<v>[^\s@'\"/]+)@[^\s'\"]"),
     "high", "user:password embedded in a URL / connection string"),
    ("url_query_token", re.compile(
        r"(?i)[?&](?P<n>access_token|token|api_?key|apikey|key|secret|password|pwd|"
        r"sig|signature|auth|client_secret)=(?P<v>[^&\s'\"#)]+)"),
     "high", "Credential in a URL query string"),
    ("k8s_literal", re.compile(r"--from-literal=(?P<n>[^=\s]+)=" + _V),
     "high", "Secret value in kubectl create secret --from-literal"),
    ("dsn_password", re.compile(
        r"(?i)(?<![A-Za-z0-9_\-])(?P<n>password|pwd)\s*=\s*(?P<v>[^\s;'\"&)]+)"),
     "high", "password= in a DSN / connection string"),
    ("aws_configure", re.compile(
        r"\baws\s+configure\s+set\s+(?:[\w.]+\.)?(?P<n>aws_secret_access_key|aws_session_token)\s+" + _V),
     "critical", "AWS secret passed to `aws configure set`"),
    ("openssl_pass", re.compile(r"-pass(?:in|out)?\s+pass:(?P<v>[^\s'\"]+)"),
     "high", "Password in openssl -pass pass:..."),
    ("npm_authtoken", re.compile(r":(?P<n>_auth(?:Token)?)(?:\s*=\s*|\s+)" + _V),
     "high", "npm registry auth token"),
    ("sudo_echo", re.compile(
        r"\becho\s+(?P<v>'[^']+'|\"[^\"]+\"|[^\s|]+)\s*\|\s*sudo\s+(?:-\w+\s+)*-S\b"),
     "high", "sudo password piped through echo"),
]

# Tools whose SHORT flag takes the password. Handled separately so that, e.g.,
# `redis-cli -p 6379 -a secret` does not stop at the port.
SHORT_FLAG_TOOLS = [
    (re.compile(r"\bsshpass\b"), ("-p",), "sshpass -p password"),
    (re.compile(r"\b(?:docker|podman|nerdctl)\s+login\b|\bhelm\s+registry\s+login\b"), ("-p",),
     "registry login -p password"),
    (re.compile(r"\bredis-cli\b"), ("-a",), "redis-cli -a password"),
    (re.compile(r"\b(?:mongosh|mongo|mongodump|mongorestore|mongoexport|mongoimport)\b"), ("-p",),
     "mongo -p password"),
    (re.compile(r"\bsqlcmd\b|\bbcp\b"), ("-P",), "sqlcmd -P password"),
    (re.compile(r"\bldap(?:search|add|modify|delete|passwd|whoami)\b"), ("-w",), "ldap* -w password"),
    (re.compile(r"\bsmbclient\b"), ("-U",), "smbclient -U user%password"),
]
_SEGMENT_END = re.compile(r"&&|\|\||;|\|(?!\|)|\n")

# key: value / KEY=value lines in YAML / TOML / dotenv-ish text
KV_LINE = re.compile(
    r"^\s*(?:export\s+)?['\"]?(?P<n>[A-Za-z0-9_.\-]+)['\"]?\s*[:=]\s*(?P<v>'[^']*'|\"[^\"]*\"|[^\s#]+)")
SENSITIVE_KEY = re.compile(
    r"(?i)(pass(word|wd)?$|^pwd$|_pwd$|secret|token|api[_-]?key|apikey|access[_-]?key|"
    r"private[_-]?key|auth(?!or)|credential|cookie|dsn$|database_url|conn(ection)?[_-]?str)")
SENSITIVE_HEADER = re.compile(
    r"(?i)^(authorization|proxy-authorization|cookie|"
    r"x-[a-z0-9-]*(api|auth|token|key|secret|session)[a-z0-9-]*|"
    r"api-?key|apikey|private-token|x-token|token)$")
# keys whose value is a command / path that FETCHES a secret: the correct pattern
HELPER_KEYS = {"apiKeyHelper", "headersHelper", "awsAuthRefresh", "awsCredentialExport",
               "otelHeadersHelper", "bearer_token_env_var", "env_key", "envFile",
               "env_http_headers"}

# A reference, not a literal: the CORRECT pattern.
REFERENCE = re.compile(
    r"^(\$\{?[A-Za-z_][A-Za-z0-9_]*\}?|\$\(|\$\{env:|\$\{input:|\$\{\{|%[A-Za-z_]+%|"
    r"<[^>]*>|\{\{|op://|vault:|aws:secretsmanager|arn:aws:secretsmanager|"
    r"\*+$|~?/|\./|\.\./|@)")
PLACEHOLDER = re.compile(
    r"(?i)^(x{3,}|\*{3,}|\.{3}|…|changeme|change[_-]?me|placeholder|example|sample|dummy|"
    r"your[_-].*|my[_-]?(password|token|key|secret)|redacted|null|none|true|false|undefined|"
    r"password|passwd|pass|secret|token|apikey|api[_-]?key|stdin|-|todo|tbd|fixme|"
    r"test|testing|foo|bar|baz|bearer|basic|\[.*\]|\{.*\})$")
PLACEHOLDER_ANY = re.compile(r"(?i)(example|changeme|placeholder|x{5,}|redacted|dummy|[<>]|\{\{)")


# ------------------------------------------------------------------ masking

VENDORED_PLUGIN = re.compile(
    r"(^|/)(\.codex|codex-home)/\.tmp/plugins[^/]*/"
    r"|(^|/)\.claude/plugins/(cache|marketplaces)/")


def preview(value: str) -> str:
    """The ONLY representation of a secret that ever reaches the output."""
    n = len(value)
    if n >= 8:
        return f"{value[:2]}… (len={n})"
    return f"… (len={n})"


def clean_value(raw: str) -> str:
    v = (raw or "").strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"":
        v = v[1:-1]
    v = v.strip().strip("\\")
    # permission-rule syntax around the value: Bash(cmd:*)  Bash(cmd *)
    for suffix in (":*)", ":*", "*)", ")", "*", "\\"):
        if v.endswith(suffix) and len(v) > len(suffix):
            v = v[: -len(suffix)]
    return v.strip().strip("'\"")


def is_literal_secret(v: str, min_len: int = 4) -> bool:
    if len(v) < min_len:
        return False
    if REFERENCE.search(v) or "${" in v or "$(" in v:
        return False
    if PLACEHOLDER.search(v) or PLACEHOLDER_ANY.search(v):
        return False
    if len(set(v)) <= 2:
        return False
    if re.fullmatch(r"\d{1,6}", v):          # ports, timeouts, uids
        return False
    if "*" in v:                              # permission wildcard, not a value
        return False
    # a date or timestamp under a key that merely contains "token"
    # (claudeCodeFirstTokenDate, tokenExpiresAt) is not a credential
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}([T ][\d:.]+(Z|[+-]\d{2}:?\d{2})?)?", v):
        return False
    return True


def secretish(v: str) -> bool:
    """For generic key/value matches: a config word ('enabled') is not a secret."""
    return len(v) >= 16 or (re.search(r"\d", v) and re.search(r"[A-Za-z]", v)) \
        or bool(re.search(r"[^A-Za-z0-9]", v))


# ------------------------------------------------------------------ provider rules
# Provider-format tokens (AKIA..., ghp_..., sk-ant-...) come from the sibling
# scan_secrets.py so there is one catalog.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True      # do not leave __pycache__ inside the skill folder
try:
    import scan_secrets as _ss  # noqa: E402
    PROVIDER_RULES = [(rid, re.compile(rx), sev, desc, grp)
                      for rid, rx, sev, desc, grp in _ss.SECRET_RULES
                      if rid not in {"hardcoded_password_prop", "conn_string_pwd",
                                     "url_basic_auth", "hardcoded_password"}]
    # most specific first: sk-ant- must win over the generic sk- rule
    PROVIDER_RULES.sort(key=lambda r: r[0] != "anthropic_key")
except Exception:  # pragma: no cover - still works without the sibling
    _ss = None
    PROVIDER_RULES = []


def _short_flag_hits(s: str, emit) -> None:
    for tool_rx, flags, desc in SHORT_FLAG_TOOLS:
        for tm in tool_rx.finditer(s):
            end = _SEGMENT_END.search(s, tm.end())
            seg = s[tm.end(): end.start() if end else len(s)]
            toks = re.findall(r"'[^']*'|\"[^\"]*\"|\S+", seg)
            for i, t in enumerate(toks):
                val = None
                for f in flags:
                    if t == f and i + 1 < len(toks):
                        val = toks[i + 1]
                    elif t.startswith(f) and len(t) > len(f) and not t.startswith("--"):
                        val = t[len(f):].lstrip("=")
                if val is None:
                    continue
                v = clean_value(val)
                if flags == ("-U",):
                    if "%" not in v:
                        continue
                    v = v.split("%", 1)[1]
                if v.startswith("-") or not is_literal_secret(v):
                    continue
                emit("short_pass_flag", "high", "Password after a short flag (" + desc + ")",
                     t if len(t) <= 3 else t[:2], v)


def scan_string(s: str, emit) -> None:
    """Run every rule over one string (a permission rule, an arg list, a line)."""
    if not s or len(s) < 6:
        return
    seen: set = set()

    def once(rid, sev, desc, name, v):
        if v in seen:
            return
        seen.add(v)
        emit(rid, sev, desc, name, v)

    for rid, rx, sev, desc in INLINE_RULES:
        for m in rx.finditer(s):
            name = m.groupdict().get("n") or ""
            v = clean_value(m.group("v"))
            if rid == "auth_header":
                if not SENSITIVE_HEADER.match(name):
                    continue
                v = re.sub(r"(?i)^(bearer|basic|token|bot|apikey|key)\s+", "", v).strip()
            if rid == "env_assign":
                if re.fullmatch(r"(?i).*_(FILE|PATH|DIR)|.*_HELPER", name) or "://" in v:
                    continue          # path to a secret / URL (url_userinfo handles those)
            if rid == "password_flag" and re.match(r"(?i)(id|src|source|env|type|target)=", v):
                continue              # docker build --secret id=...,src=...
            if rid == "url_userinfo" and v.lower() in {"password", "pass", "secret"}:
                continue
            if rid == "dsn_password" and "://" in v and "@" not in v:
                continue
            if rid == "curl_user" and re.fullmatch(r"\d+", name):
                continue              # -u 1000:1000 (uid:gid)
            if not is_literal_secret(v):
                continue
            once(rid, sev, desc, name, v)
    _short_flag_hits(s, once)
    for rid, rx, sev, desc, grp in PROVIDER_RULES:
        for m in rx.finditer(s):
            v = m.group(grp) if grp and m.lastindex and grp <= m.lastindex else m.group(0)
            if _ss is not None:
                keep, _ = _ss.validate(rid, v, "agent-config.json", "")
                if not keep:
                    continue
            if grp == 0:              # structural match (private key block, SA json)
                once(rid, sev, desc, "", "")
                continue
            v = clean_value(v)
            if is_literal_secret(v, 8):
                once(rid, sev, desc, "", v)


# ------------------------------------------------------------------ structured walk

def _child(path: str, k) -> str:
    k = str(k)
    if re.fullmatch(r"[A-Za-z0-9_\-]+", k):
        return f"{path}.{k}" if path else k
    return f"{path}[{json.dumps(k)}]"


def _last_key(path: str) -> str:
    m = re.search(r"(?:^|\.)([A-Za-z0-9_\-]+)$", path)
    return m.group(1) if m else ""


def walk_json(node, path: str, emit_at) -> None:
    """Visit every string leaf. Key-aware checks for env / headers blocks."""
    if isinstance(node, dict):
        parent = _last_key(path)
        for k, val in node.items():
            sub = _child(path, k)
            if not isinstance(val, str):
                walk_json(val, sub, emit_at)
                continue
            lit = clean_value(val)
            if k in HELPER_KEYS:
                walk_string(val, sub, emit_at)
                continue
            if parent in {"env", "environment", "headers", "http_headers"}:
                is_header = parent in {"headers", "http_headers"}
                sensitive = SENSITIVE_HEADER.match(k) if is_header else SENSITIVE_KEY.search(k)
                if is_header:
                    lit = re.sub(r"(?i)^(bearer|basic|token|bot)\s+", "", lit).strip()
                plain_url = "://" in lit and "@" not in lit
                if sensitive and not plain_url and is_literal_secret(lit):
                    kind = "header" if is_header else "env"
                    emit_at(sub, "literal_in_" + kind, "high",
                            f"Literal secret in an MCP/settings {kind} block "
                            "(use a ${VAR} / input / secret reference)", k, lit)
                    continue
            elif SENSITIVE_KEY.search(k) and is_literal_secret(lit, 6) and secretish(lit) \
                    and " " not in lit and len(lit) < 300 and "://" not in lit:
                emit_at(sub, "literal_secret_key", "high",
                        "Literal value under a secret-looking key", k, lit)
                continue
            walk_string(val, sub, emit_at)
    elif isinstance(node, list):
        # args lists: scan the joined command too, so "--token", "abc" pairs match
        if node and all(isinstance(x, str) for x in node) and _last_key(path) in {"args", "command"}:
            walk_string(" ".join(shlex.quote(x) for x in node), path, emit_at)
            return
        for i, val in enumerate(node):
            sub = f"{path}[{i}]"
            if isinstance(val, str):
                walk_string(val, sub, emit_at)
            else:
                walk_json(val, sub, emit_at)


def walk_string(s: str, path: str, emit_at) -> None:
    scan_string(s, lambda rid, sev, desc, name, v: emit_at(path, rid, sev, desc, name, v))


def analyze_content(text: str, kind: str, relpath: str, max_per_rule: int = 50):
    """Raw hits: (location, rule, severity, desc, name, value). Values stay in memory."""
    hits: list = []

    def emit_at(loc, rid, sev, desc, name, v):
        hits.append((loc, rid, sev, desc, name, v))

    if kind == "auto":
        kind = "json" if relpath.endswith(".json") else "text"
    if kind == "json":
        try:
            walk_json(json.loads(text), "", emit_at)
            return hits
        except ValueError:
            kind = "text"
    if kind == "toml":
        if tomllib is not None:
            try:
                walk_json(tomllib.loads(text), "", emit_at)
                return hits
            except Exception:
                pass
        kind = "text"
    if kind == "transcript":
        per_rule: Counter = Counter()
        for i, line in enumerate(text.splitlines(), 1):
            line_hits: list = []
            try:
                walk_json(json.loads(line), "", lambda *a: line_hits.append(a))
            except ValueError:
                scan_string(line, lambda rid, sev, desc, name, v:
                            line_hits.append(("", rid, sev, desc, name, v)))
            seen_line = set()
            for _, rid, sev, desc, name, v in line_hits:
                if (rid, v) in seen_line:
                    continue
                seen_line.add((rid, v))
                per_rule[rid] += 1
                if per_rule[rid] <= max_per_rule:
                    hits.append((f"line {i}", rid, sev, desc, name, v))
        for rid, n in per_rule.items():
            if n > max_per_rule:
                hits.append(("-", "more_hits", "medium",
                             f"{n - max_per_rule} more '{rid}' match(es) not listed", rid, ""))
        return hits
    is_rules = relpath.endswith(".rules")
    for i, line in enumerate(text.splitlines(), 1):
        if is_rules:   # prefix_rule(pattern=["curl", "-H", "..."]) -> join the tokens
            toks = re.findall(r"\"((?:[^\"\\]|\\.)*)\"|'((?:[^'\\]|\\.)*)'", line)
            if toks:
                line = " ".join(shlex.quote(a or b) for a, b in toks)
        before = len(hits)
        scan_string(line, lambda rid, sev, desc, name, v:
                    hits.append((f"line {i}", rid, sev, desc, name, v)))
        if len(hits) == before:
            m = KV_LINE.match(line)
            if m and SENSITIVE_KEY.search(m.group("n")) and m.group("n") not in HELPER_KEYS:
                v = clean_value(m.group("v"))
                if is_literal_secret(v, 6) and secretish(v) and "://" not in v:
                    hits.append((f"line {i}", "literal_secret_key", "high",
                                 "Literal value under a secret-looking key", m.group("n"), v))
    return hits


# ------------------------------------------------------------------ git helpers

def git(repo: str, *args: str, timeout: int = 60, binary: bool = False):
    try:
        r = subprocess.run(["git", "--no-pager", "-C", repo, *args],
                           capture_output=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    return r.stdout if binary else r.stdout.decode("utf-8", "replace")


def find_repo_root(path: str, cache: dict):
    d = os.path.dirname(os.path.abspath(path))
    chain = []
    root = None
    while True:
        if d in cache:
            root = cache[d]
            break
        if os.path.exists(os.path.join(d, ".git")):
            root = d
            break
        chain.append(d)
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    for c in chain:
        cache[c] = root
    return root


def ignore_state(repo: str, rel: str):
    """('project' | 'project-untracked' | 'repo-local' | 'global' | 'none', source)."""
    out = git(repo, "check-ignore", "-v", "--no-index", "--", rel)
    if not out:
        return "none", ""
    meta = out.splitlines()[0].split("\t", 1)[0]
    parts = meta.rsplit(":", 2)
    if len(parts) != 3:
        return "none", ""
    source, _lineno, pattern = parts
    if pattern.startswith("!"):
        return "none", source
    src_abs = os.path.normpath(source if os.path.isabs(source) else os.path.join(repo, source))
    if src_abs.startswith(os.path.join(repo, ".git") + os.sep):
        return "repo-local", ".git/info/exclude"
    if src_abs.startswith(repo + os.sep) and os.path.basename(src_abs) == ".gitignore":
        rel_src = os.path.relpath(src_abs, repo)
        tracked = git(repo, "ls-files", "--error-unmatch", "--", rel_src) is not None
        return ("project" if tracked else "project-untracked"), rel_src
    return "global", "global excludes"


def claude_commits(repo: str, rel: str) -> int:
    """Commits touching the file whose author is Claude or that carry a Claude co-author trailer."""
    out = git(repo, "log", "--all", "--format=%ae%x00%b%x1e", "--", rel) or ""
    n = 0
    for rec in out.split("\x1e"):
        if not rec.strip():
            continue
        email, _, body = rec.strip().partition("\x00")
        if email.strip().lower() == "noreply@anthropic.com" or \
                re.search(r"(?im)^co-authored-by:.*(claude|noreply@anthropic\.com)", body):
            n += 1
    return n


# ------------------------------------------------------------------ dockerignore

def _dockerignore_rx(pattern: str):
    p = pattern.strip().lstrip("/")
    if p not in ("", "."):
        p = os.path.normpath(p)
    out, i = "", 0
    while i < len(p):
        if p.startswith("**", i):
            out += ".*"
            i += 2
            if i < len(p) and p[i] == "/":
                out += "/?"
                i += 1
            continue
        c = p[i]
        out += {"*": "[^/]*", "?": "[^/]"}.get(c, re.escape(c))
        i += 1
    return re.compile(r"^" + out + r"(/.*)?$")   # a directory pattern covers its contents


def dockerignore_excludes(path_in_context: str, patterns: list) -> bool:
    excluded = False
    for raw in patterns:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        neg = line.startswith("!")
        if _dockerignore_rx(line[1:] if neg else line).match(path_in_context):
            excluded = not neg
    return excluded


COPY_ALL = re.compile(
    r"(?im)^\s*(?:COPY|ADD)\s+(?:--(?!from)[\w-]+(?:=\S+)?\s+)*(?:\.|\./|\./\.)\s+\S|"
    r"^\s*(?:COPY|ADD)\s+(?:--(?!from)[\w-]+(?:=\S+)?\s+)*\[\s*\"\.\/?\"")
DOCKERFILE_NAME = re.compile(r"(?i)^(dockerfile|containerfile)(\..+)?$|\.(dockerfile|containerfile)$")


# ------------------------------------------------------------------ audit

class Audit:
    def __init__(self, args):
        self.args = args
        self.findings: list = []
        self.files: list = []
        self.repos: set = set()
        self.checked: set = set()
        self.docker: list = []
        self.repo_cache: dict = {}
        self._seen: set = set()
        self._by_value: dict = {}     # (file, rule, name, value) -> finding; memory only
        self.base = "/"

    def add(self, sev, rule, desc, file, loc, name="", value=None, source="worktree", note=""):
        key = (file, loc, rule, name, source.split(":")[0], value)
        if key in self._seen:
            return None
        self._seen.add(key)
        if VENDORED_PLUGIN.search(str(file)):
            # a plugin cache cloned by the agent itself (Codex / Claude Code marketplaces):
            # whatever it ships is the vendor's, e.g. a public OAuth client_secret. One clone
            # per agent home would otherwise bury the real findings under identical criticals.
            sev = "low"
            note = (note + "; " if note else "") + "vendored third-party plugin, not your credential"
        f = {"severity": sev, "rule": rule, "desc": desc, "file": file, "location": loc,
             "name": name, "preview": preview(value) if value else "", "source": source,
             "note": note}
        self.findings.append(f)
        if value and source == "worktree":
            self._by_value[(file, rule, name, value)] = f
        return f

    def rel(self, path):
        return os.path.relpath(path, self.base)

    @staticmethod
    def classify(path: str):
        p = path.replace("\\", "/")
        for rx, kind, label in AGENT_RX:
            if rx.search(p):
                return kind, label
        return None

    def walk(self, root: str):
        self.base = root
        r0 = find_repo_root(os.path.join(root, "x"), self.repo_cache)
        if r0:
            self.repos.add(r0)
        for dirpath, dirnames, filenames in os.walk(root):
            if ".git" in dirnames or ".git" in filenames:
                self.repos.add(dirpath)
                self.repo_cache[dirpath] = dirpath
            in_claude = os.path.basename(dirpath) == ".claude"
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and
                           not (in_claude and d in SKIP_UNDER_CLAUDE) and
                           not (in_claude and d == "projects" and self.args.no_transcripts)]
            for fn in filenames:
                full = os.path.join(dirpath, fn)
                if DOCKERFILE_NAME.search(fn):
                    self.check_dockerfile(full)
                c = self.classify(full)
                if not c:
                    continue
                kind, label = c
                if kind == "transcript" and self.args.no_transcripts:
                    continue
                self.scan_worktree_file(full, kind, label)
        for repo in sorted(self.repos - self.checked):
            self.checked.add(repo)
            self.check_repo(repo)

    # ---- worktree file
    def scan_worktree_file(self, full: str, kind: str, label: str):
        relp = self.rel(full)
        repo = find_repo_root(full, self.repo_cache)
        st = {"file": relp, "label": label, "repo": self.rel(repo) if repo else None,
              "exists": True, "tracked": None, "history_commits": 0,
              "ignored_by": None, "claude_commits": 0, "secrets": 0}
        if repo:
            in_repo = os.path.relpath(full, repo)
            st["tracked"] = git(repo, "ls-files", "--error-unmatch", "--", in_repo) is not None
            st["history_commits"] = len((git(repo, "log", "--all", "--format=%h", "--", in_repo)
                                         or "").split())
            st["ignored_by"], _ = ignore_state(repo, in_repo)
            if st["history_commits"]:
                st["claude_commits"] = claude_commits(repo, in_repo)
        self.files.append(st)

        if kind == "name-only":
            sev = "critical" if st["tracked"] or st["history_commits"] else "medium"
            self.add(sev, "credentials_file", label, relp, "-", note=self.state_note(st))
            return
        limit = self.args.max_transcript_bytes if kind == "transcript" else self.args.max_bytes
        try:
            size = os.path.getsize(full)
            with open(full, "rb") as fh:
                raw = fh.read(limit)
        except OSError:
            return
        trunc = "; file truncated to the scan limit" if size > limit else ""
        for loc, rid, sev, desc, name, v in analyze_content(raw.decode("utf-8", "replace"), kind, relp):
            if rid != "more_hits":
                st["secrets"] += 1
            self.add(self.escalate(sev, st), rid, desc, relp, loc or "-", name, v,
                     note=self.state_note(st) + trunc)

    @staticmethod
    def escalate(sev, st):
        if st.get("tracked"):
            return "critical"
        if st.get("ignored_by") in ("project", "repo-local", "global"):
            # still a plaintext secret at rest: Docker COPY, backups, sync tools, `git add -f`
            return "high" if sev == "critical" else "medium"
        return sev

    @staticmethod
    def state_note(st):
        bits = []
        if st.get("repo") is None:
            return "not inside a git repo"
        if st.get("tracked"):
            bits.append("TRACKED by git")
        if st.get("history_commits"):
            bits.append(f"path in history ({st['history_commits']} commit(s))")
        if not st.get("tracked") and st.get("exists", True):
            bits.append({"project": "ignored by project .gitignore",
                         "project-untracked": "ignored only by an UNTRACKED .gitignore",
                         "repo-local": "ignored only by .git/info/exclude (not shared)",
                         "global": "ignored ONLY by the machine's global excludes",
                         }.get(st.get("ignored_by") or "none", "NOT ignored"))
        if not st.get("exists", True):
            bits.append("deleted from the tree, still in history")
        if st.get("claude_commits"):
            bits.append(f"{st['claude_commits']} commit(s) by/with Claude")
        return "; ".join(bits)

    # ---- per repo: .gitignore hygiene + history
    def check_repo(self, repo: str):
        if git(repo, "rev-parse", "--git-dir") is None:
            return
        relrepo = self.rel(repo)
        names = "" if self.args.no_history else \
            (git(repo, "log", "--all", "--format=", "--name-only", timeout=180) or "")
        agent_hist = sorted({n.strip() for n in names.splitlines()
                             if n.strip() and self.classify(n.strip())})
        uses_claude = os.path.isdir(os.path.join(repo, ".claude")) or \
            any(p.endswith(".claude/settings.local.json") for p in agent_hist)
        uses_devin = os.path.isdir(os.path.join(repo, ".devin")) or \
            any(p in (".devin/config.local.json", ".devin/mcp_config.local.json")
                for p in agent_hist)

        if uses_claude:
            state, _ = ignore_state(repo, ".claude/settings.local.json")
            if state != "project":
                what = {"global": "only the machine's global excludes ignore it",
                        "repo-local": "only .git/info/exclude ignores it (not shared)",
                        "project-untracked": "the .gitignore that covers it is not tracked",
                        }.get(state, "nothing ignores it")
                self.add("medium", "gitignore_missing_local_settings",
                         "Project .gitignore does not cover .claude/settings.local.json "
                         f"({what}); another clone, CI or `git add -f` will commit it",
                         os.path.normpath(os.path.join(relrepo, ".gitignore")), "-")

        if uses_devin:
            for local in (".devin/config.local.json", ".devin/mcp_config.local.json"):
                state, _ = ignore_state(repo, local)
                if state != "project":
                    what = {"global": "only the machine's global excludes ignore it",
                            "repo-local": "only .git/info/exclude ignores it (not shared)",
                            "project-untracked": "the .gitignore that covers it is not tracked",
                            }.get(state, "nothing ignores it")
                    self.add("medium", "gitignore_missing_local_settings",
                             f"Project .gitignore does not cover {local} "
                             f"({what}); another clone, CI or `git add -f` will commit it",
                             os.path.normpath(os.path.join(relrepo, ".gitignore")), "-")

        for p in agent_hist:
            kind, label = self.classify(p)
            if kind == "transcript" and self.args.no_transcripts:
                continue
            full = os.path.join(repo, p)
            relp = self.rel(full)
            revs = (git(repo, "log", "--all", "--format=%H", "--", p) or "").split()
            if not revs:
                continue
            exists = os.path.exists(full)
            st = None
            if not exists:
                st = {"file": relp, "label": label, "repo": relrepo, "exists": False,
                      "tracked": False, "history_commits": len(revs), "ignored_by": None,
                      "claude_commits": claude_commits(repo, p), "secrets": 0}
                self.files.append(st)
            if kind == "name-only":
                self.add("critical", "credentials_file", label + " (in git history)", relp, "-",
                         source=f"history:{revs[-1][:8]}", note=f"in {len(revs)} commit(s)")
                continue
            limit = self.args.max_transcript_bytes if kind == "transcript" else self.args.max_bytes
            per_value: dict = {}
            for rev in revs[: self.args.max_revs]:
                blob = git(repo, "show", f"{rev}:{p}", binary=True, timeout=30)
                if blob is None:
                    continue    # the commit that deleted it
                for loc, rid, sev, desc, name, v in analyze_content(
                        blob[:limit].decode("utf-8", "replace"), kind, p):
                    if rid == "more_hits":
                        continue
                    per_value.setdefault((rid, name, v), [loc, desc, []])[2].append(rev[:8])
            for (rid, name, v), (loc, desc, commits) in per_value.items():
                hist_note = f"committed: {len(commits)} version(s) in history, oldest {commits[-1]}"
                wt = self._by_value.get((relp, rid, name, v))
                if wt is not None:     # same secret is in the tree too: one finding, escalated
                    wt["severity"] = "critical"
                    wt["note"] = (wt["note"] + "; " + hist_note).strip("; ")
                    continue
                note = hist_note + ("" if exists else "; file deleted from the tree")
                self.add("critical", rid, desc, relp, loc, name, v,
                         source=f"history:{commits[-1]}", note=note)
            if st is not None:
                st["secrets"] = len(per_value)

    # ---- Dockerfile without a protective .dockerignore
    def check_dockerfile(self, full: str):
        try:
            with open(full, "r", encoding="utf-8", errors="replace") as fh:
                content = fh.read(512 * 1024)
        except OSError:
            return
        if not COPY_ALL.search(content):
            return
        ctx = os.path.dirname(full)
        di = next((c for c in (full + ".dockerignore", os.path.join(ctx, ".dockerignore"))
                   if os.path.isfile(c)), None)
        private = []
        for dirpath, dirnames, filenames in os.walk(ctx):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fn in filenames:
                r = os.path.relpath(os.path.join(dirpath, fn), ctx).replace("\\", "/")
                if LOCAL_ONLY.search(r):
                    private.append(r)
            if len(private) > 50:
                break
        relf = self.rel(full)
        entry = {"dockerfile": relf, "dockerignore": self.rel(di) if di else None,
                 "context_assumed": self.rel(ctx), "would_ship": []}
        if di is None:
            entry["would_ship"] = private
            self.add("high" if private else "medium", "docker_copy_no_dockerignore",
                     "COPY/ADD of the whole build context and no .dockerignore: .claude/ and "
                     "every gitignored file go into the image (COPY ignores .gitignore)", relf, "-",
                     note=(f"{len(private)} personal agent file(s) in the context now"
                           if private else "no personal agent file in the context right now")
                     + "; context assumed = the Dockerfile's directory")
        else:
            with open(di, "r", encoding="utf-8", errors="replace") as fh:
                pats = fh.read().splitlines()
            probe = private or [".claude/settings.local.json"]
            leaked = [p for p in probe if not dockerignore_excludes(p, pats)]
            if leaked:
                entry["would_ship"] = leaked if private else []
                self.add("high" if private else "medium", "dockerignore_misses_agent_files",
                         ".dockerignore does not exclude the personal agent files "
                         "(add .claude/ and the other agent dirs)", self.rel(di), "-",
                         note="would ship: " + ", ".join(leaked[:5]) + (" ..." if len(leaked) > 5 else ""))
        self.docker.append(entry)


# ------------------------------------------------------------------ report

def main() -> int:
    ap = argparse.ArgumentParser(
        description="Audit AI coding-agent config files for secrets (values are never printed)")
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-history", action="store_true", help="do not read git history")
    ap.add_argument("--no-transcripts", action="store_true",
                    help="skip session transcripts / prompt history (*.jsonl)")
    ap.add_argument("--max-revs", type=int, default=200,
                    help="max historical versions read per agent file (default 200)")
    ap.add_argument("--max-bytes", type=int, default=2 * 1024 * 1024)
    ap.add_argument("--max-transcript-bytes", type=int, default=50 * 1024 * 1024)
    ap.add_argument("--severity", choices=list(SEVERITY_ORDER), default="low")
    args = ap.parse_args()

    roots = []
    for p in args.paths:
        a = os.path.abspath(os.path.expanduser(p))
        if not os.path.isdir(a):
            print(f"error: not a directory: {a}", file=sys.stderr)
            return 2
        roots.append(a)

    audit = Audit(args)
    for r in roots:
        audit.walk(r)

    floor = SEVERITY_ORDER[args.severity]
    findings = [f for f in audit.findings if SEVERITY_ORDER[f["severity"]] >= floor]
    def natural(s):
        return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", s)]
    findings.sort(key=lambda f: (-SEVERITY_ORDER[f["severity"]], f["file"], natural(f["location"])))
    counts = Counter(f["severity"] for f in findings)

    if args.json:
        print(json.dumps({"roots": roots, "repos": len(audit.repos), "agent_files": audit.files,
                          "docker": audit.docker, "counts": dict(counts), "findings": findings},
                         indent=2, ensure_ascii=False))
        return 1 if findings else 0

    print(f"roots   : {', '.join(roots)}")
    print(f"repos   : {len(audit.repos)}   agent files: {len(audit.files)}   "
          f"Dockerfiles copying the whole context: {len(audit.docker)}")
    print(f"history : {'skipped (--no-history)' if args.no_history else 'scanned'}   "
          f"transcripts: {'skipped' if args.no_transcripts else 'scanned'}")
    print(f"findings: {len(findings)}  [critical={counts['critical']} high={counts['high']} "
          f"medium={counts['medium']} low={counts['low']}]")
    print("values are never printed: preview = first 2 chars (values of 8+ chars only) + length\n")

    if audit.files:
        print("=" * 70 + "\nAGENT CONFIG FILES\n" + "=" * 70)
        for st in sorted(audit.files, key=lambda s: s["file"]):
            where = "worktree" if st["exists"] else "HISTORY ONLY"
            print(f"  {st['file']}  [{where}]  matches: {st['secrets']}")
            print(f"    {st['label']}")
            print(f"    state: {Audit.state_note(st)}")
        print()

    by_sev = defaultdict(list)
    for f in findings:
        by_sev[f["severity"]].append(f)
    for sev in ("critical", "high", "medium", "low"):
        group = by_sev.get(sev)
        if not group:
            continue
        print("=" * 70 + f"\n{sev.upper()} ({len(group)})\n" + "=" * 70)
        for f in group:
            src = "" if f["source"] == "worktree" else f"  [{f['source']}]"
            print(f"  {f['rule']}: {f['desc']}{src}")
            print(f"    {f['file']}" + ("" if f["location"] in ("", "-") else f"  @ {f['location']}"))
            if f["name"] or f["preview"]:
                print("    " + (f"name: {f['name']}   " if f["name"] else "")
                      + (f"value: {f['preview']}" if f["preview"] else ""))
            if f["note"]:
                print(f"    note : {f['note']}")
            print()

    if not findings:
        print("No findings. Scope: agent config files + Dockerfiles under the given roots.")
        print("Run scan_secrets.py --history for the rest of the repository.")
        return 0
    print("=" * 70)
    print("NEXT: (1) ROTATE every credential listed (history, forks and images keep copies),")
    print("(2) rewrite the rules without the secret, (3) add the agent local files")
    print("(.claude/settings.local.json, .devin/*.local.json) to the project .gitignore")
    print("AND .dockerignore, (4) clean history / rebuild images.")
    print("See references/agent-config-leaks.md.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
