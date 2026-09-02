#!/usr/bin/env python3
"""
scan_secrets.py - Auditoria de exposicao PRE-PUBLICACAO de repositorio.

Varre working tree e (com --history) o historico do git procurando:
  - segredos: API keys, tokens, senhas, chaves privadas, connection strings
  - dados pessoais: PII (CPF/CNPJ/RG/telefone/email), PCI (cartao, via Luhn), PHI
  - infra interna: IP privado, hostname interno, caminho revelando usuario
  - arquivos que nao deveriam estar versionados

Nao envia nada pra lugar nenhum. Segredos aparecem MASCARADOS na saida.

Uso:
    python3 scan_secrets.py <repo>
    python3 scan_secrets.py <repo> --history          # inclui historico do git
    python3 scan_secrets.py <repo> --json
    python3 scan_secrets.py <repo> --severity high    # so high/critical
    python3 scan_secrets.py <repo> --no-pii           # so segredos
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import sys
from collections import Counter

SEVERITY_ORDER = {"critical": 4, "high": 3, "medium": 2, "low": 1}

SKIP_DIRS = {
    ".git", ".svn", ".hg", "node_modules", "venv", ".venv", "env", "__pycache__",
    ".mypy_cache", ".pytest_cache", ".tox", "dist", "build", ".gradle", ".idea",
    "vendor", "target", ".next", ".nuxt", "coverage", ".terraform", "bin", "obj",
}

SKIP_EXT = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".webp", ".svg", ".pdf",
    ".mp4", ".mp3", ".wav", ".avi", ".mov", ".zip", ".gz", ".tar", ".7z", ".rar",
    ".woff", ".woff2", ".ttf", ".eot", ".otf", ".class", ".pyc", ".o", ".so",
    ".dll", ".exe", ".jar", ".wasm", ".min.js", ".map",
}

# Arquivos que ja sao um achado pelo simples fato de existirem versionados
DANGEROUS_FILES = [
    (r"(^|/)\.env(\.(local|dev|development|prod|production|staging|test))?$", "critical",
     "Arquivo .env versionado - normalmente contem todas as credenciais"),
    (r"(^|/)id_(rsa|dsa|ecdsa|ed25519)$", "critical", "Chave SSH privada"),
    (r"\.(pem|key|p12|pfx|jks|keystore|ppk)$", "critical", "Arquivo de chave/certificado privado"),
    (r"(^|/)\.pgpass$|(^|/)\.netrc$|(^|/)\.my\.cnf$", "critical", "Arquivo de credencial de acesso"),
    (r"(^|/)credentials(\.json|\.yml|\.yaml)?$", "critical", "Arquivo de credenciais"),
    (r"service[-_]?account.*\.json$", "critical", "Service account do GCP (contem chave privada)"),
    (r"\.tfstate(\.backup)?$", "critical", "Terraform state - armazena secrets em texto claro"),
    (r"(^|/)\.npmrc$|(^|/)\.pypirc$", "high", "Config de registry - costuma conter token"),
    (r"(^|/)secrets?\.(ya?ml|json|properties|toml)$", "high", "Arquivo de secrets"),
    (r"\.(ovpn|kubeconfig)$|(^|/)kubeconfig$", "high", "Config de acesso a rede/cluster"),
    (r"\.(sql|dump)$", "medium", "Dump de banco - verificar se contem dado real"),
    (r"\.(sqlite3?|db)$", "medium", "Banco de dados versionado - verificar conteudo"),
    (r"(^|/)\.htpasswd$", "high", "Hash de senha HTTP"),
    (r"(^|/)\.DS_Store$|(^|/)Thumbs\.db$", "low", "Arquivo de metadados do SO (ruido)"),
    (r"\.(bak|backup|old|orig)$|~$", "low", "Arquivo de backup - pode conter versao antiga com secret"),
]

# (id, regex, severidade, descricao, grupo_do_segredo)
SECRET_RULES = [
    ("aws_access_key", r"\b((?:AKIA|ASIA|ABIA|ACCA)[A-Z0-9]{16})\b", "critical",
     "AWS Access Key ID", 1),
    ("aws_secret", r"(?i)aws[_\-. ]?secret[_\-. ]?(?:access[_\-. ]?)?key\s*[:=]\s*['\"]?([A-Za-z0-9/+=]{40})['\"]?",
     "critical", "AWS Secret Access Key", 1),
    ("gcp_private_key", r'"type"\s*:\s*"service_account"', "critical",
     "Service account do GCP (JSON com chave privada)", 0),
    ("azure_conn", r"(?i)(DefaultEndpointsProtocol=https?;AccountName=[^;]+;AccountKey=[A-Za-z0-9+/=]{40,})",
     "critical", "Azure Storage connection string", 1),
    ("private_key_block", r"-----BEGIN (?:RSA |DSA |EC |OPENSSH |PGP |ENCRYPTED )?PRIVATE KEY-----",
     "critical", "Bloco de chave privada", 0),
    ("github_token", r"\b((?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36,})\b", "critical",
     "GitHub token", 1),
    ("github_pat_new", r"\b(github_pat_[A-Za-z0-9_]{60,})\b", "critical", "GitHub fine-grained PAT", 1),
    ("gitlab_pat", r"\b(glpat-[A-Za-z0-9_\-]{20,})\b", "critical", "GitLab personal access token", 1),
    ("slack_token", r"\b(xox[baprs]-[A-Za-z0-9\-]{10,})\b", "critical", "Slack token", 1),
    ("slack_webhook", r"(https://hooks\.slack\.com/services/T[A-Za-z0-9]+/B[A-Za-z0-9]+/[A-Za-z0-9]+)",
     "high", "Slack webhook URL", 1),
    ("stripe_live", r"\b(sk_live_[A-Za-z0-9]{20,})\b", "critical", "Stripe secret key (LIVE)", 1),
    ("stripe_test", r"\b(sk_test_[A-Za-z0-9]{20,})\b", "low", "Stripe test key (sandbox)", 1),
    ("openai_key", r"\b(sk-(?:proj-)?[A-Za-z0-9_\-]{32,})\b", "critical", "OpenAI API key", 1),
    ("anthropic_key", r"\b(sk-ant-[A-Za-z0-9_\-]{20,})\b", "critical", "Anthropic API key", 1),
    ("sendgrid", r"\b(SG\.[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{20,})\b", "critical", "SendGrid API key", 1),
    ("twilio", r"\b(SK[a-f0-9]{32})\b", "high", "Twilio API key", 1),
    ("google_api_key", r"\b(AIza[A-Za-z0-9_\-]{35})\b", "high", "Google API key", 1),
    ("firebase_url", r"(https://[a-z0-9\-]+\.firebaseio\.com)", "medium", "Firebase DB URL", 1),
    ("npm_token", r"(?i)//registry\.npmjs\.org/:_authToken\s*=\s*([A-Za-z0-9\-_]{20,})",
     "critical", "Token do npm registry", 1),
    ("jwt", r"\b(eyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,})\b",
     "high", "JWT (verificar se contem dado real / esta ativo)", 1),
    ("conn_string_pwd",
     r"(?i)\b((?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis|amqp|mssql|jdbc:[a-z]+)://[^\s:@/'\"]+:[^\s@'\"]{3,}@[^\s'\"<>]+)",
     "critical", "Connection string com senha embutida", 1),
    ("url_basic_auth", r"\b(https?://[^\s:@/'\"]+:[^\s@'\"]{3,}@[^\s'\"<>]+)", "high",
     "URL com credencial basic-auth", 1),
    ("hardcoded_password",
     r"(?i)\b(?:password|passwd|pwd|senha|secret|token|api[_\-]?key|apikey|access[_\-]?key|auth[_\-]?token|client[_\-]?secret)\b\s*[:=]\s*['\"]([^'\"\s${}<>]{6,80})['\"]",
     "high", "Credencial hardcoded", 1),
    # Config no estilo chave=valor (.properties/.yml/.ini/.env/.conf).
    # Aceita '#' DENTRO do valor (senha forte costuma ter) mas ignora
    # comentario de fim de linha precedido por espaco: "  # comentario".
    ("hardcoded_password_prop",
     r"(?im)^[ \t]*(?:[\w.\-]*\.)?(?:password|passwd|pwd|senha|secret|api[_\-]?key|apikey|client[_\-]?secret|access[_\-]?token|auth[_\-]?token)[ \t]*[:=][ \t]*"
     r"(?!\$\{|\$\(|%\(|<|\{\{|\$[A-Z_]+\b|['\"]?\s*$)"
     r"['\"]?([^\s'\"][^\r\n'\"]{4,80}?)['\"]?[ \t]*(?:[ \t]+[#;].*)?$",
     "high", "Credencial hardcoded em arquivo de config", 1),
    ("basic_auth_header", r"(?i)Authorization\s*[:=]\s*['\"]?Basic\s+([A-Za-z0-9+/=]{16,})", "high",
     "Header Basic auth com credencial", 1),
    ("bearer_header", r"(?i)Authorization\s*[:=]\s*['\"]?Bearer\s+([A-Za-z0-9._\-]{20,})", "high",
     "Header Bearer com token", 1),
]

# PII / PCI / PHI
PII_RULES = [
    ("cpf", r"\b(\d{3}\.\d{3}\.\d{3}-\d{2})\b", "high", "CPF (formatado)", 1),
    ("cpf_raw", r"(?<![\d.\-/])(\d{11})(?![\d.\-/])", "medium", "Possivel CPF (11 digitos)", 1),
    ("cnpj", r"\b(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})\b", "medium", "CNPJ", 1),
    ("rg", r"(?i)\brg\s*[:=]?\s*([\d.\-]{7,12})\b", "high", "RG", 1),
    ("cnh", r"(?i)\bcnh\s*[:=]?\s*(\d{9,11})\b", "high", "CNH", 1),
    ("titulo_eleitor", r"(?i)\bt[ií]tulo\s*(?:de\s*eleitor)?\s*[:=]?\s*(\d{12})\b", "high",
     "Titulo de eleitor", 1),
    ("credit_card", r"(?<![\d\-])((?:\d[ \-]?){13,19})(?![\d\-])", "critical",
     "Numero de cartao de credito (validado por Luhn)", 1),
    ("cvv", r"(?i)\b(?:cvv|cvc|cvv2|security[_\-\s]?code)\s*[:=]\s*['\"]?(\d{3,4})['\"]?", "critical",
     "CVV/CVC de cartao", 1),
    ("iban", r"\b([A-Z]{2}\d{2}[A-Z0-9]{11,30})\b", "high", "IBAN (conta bancaria)", 1),
    ("phone_br", r"(?<![\d])(\(?\d{2}\)?[\s\-]?9?\d{4}[\s\-]?\d{4})(?![\d])", "low",
     "Possivel telefone BR", 1),
    ("email", r"\b([A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,})\b", "low",
     "Endereco de e-mail", 1),
    ("cep_address", r"\b(\d{5}-\d{3})\b", "low", "CEP", 1),
    ("phi_terms",
     r"(?i)\b(?:cid[\-\s]?10\s*[:=]?\s*[A-Z]\d{2}|prontu[aá]rio\s*[:=]?\s*\d+|carteirinha\s*[:=]?\s*[\d.\-]+|diagn[oó]stico\s*[:=]\s*\w+)",
     "critical", "Possivel dado de saude (PHI)", 0),
]

INFRA_RULES = [
    ("private_ip", r"\b((?:10\.(?:\d{1,3}\.){2}\d{1,3})|(?:192\.168\.\d{1,3}\.\d{1,3})|(?:172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}))\b",
     "medium", "IP privado/interno", 1),
    ("internal_host", r"\b([a-z0-9\-]+\.(?:local|internal|intranet|corp|lan|home|priv))\b", "medium",
     "Hostname interno", 1),
    ("user_path", r"((?:[A-Z]:\\Users\\|/home/|/Users/)[A-Za-z0-9._\-]{2,40}[/\\])", "low",
     "Caminho absoluto revelando usuario do SO", 1),
    ("admin_port", r"\b(?:localhost|127\.0\.0\.1|0\.0\.0\.0)[:](\d{2,5})\b", "low",
     "Endpoint local com porta", 1),
]

PLACEHOLDER = re.compile(
    r"(?i)(your[_\-\s]?|my[_\-\s]?|the[_\-\s]?|insert[_\-\s]?|put[_\-\s]?|add[_\-\s]?)?"
    r"(x{3,}|y{3,}|z{3,}|a{4,}|0{4,}|1{4,}|123456|abcdef|changeme|change[_\-]?me|placeholder|"
    r"example|sample|dummy|fake|test[_\-]?key|test[_\-]?secret|todo|tbd|fixme|redacted|"
    r"<[^>]+>|\{\{[^}]+\}\}|\$\{[^}]+\}|%\([^)]+\)s|\.\.\.|nao[_\-]?definido|undefined|null|none)"
)

TEST_PATH = re.compile(
    r"(?i)(^|/)(tests?|spec|specs?|__tests__|fixtures?|mocks?|samples?|examples?|"
    r"testdata|test[_\-]data|demo|docs?)(/|$)|\.(test|spec)\.[a-z]+$|"
    r"(^|/)(\.env\.example|\.env\.sample|\.env\.template)$"
)

DOC_EXT = {".md", ".rst", ".txt", ".adoc"}

# Cartoes de teste publicos dos gateways (Stripe/Visa/MC/Amex/Discover).
# Montados por concatenacao de proposito: assim os digitos nao aparecem como
# literal continuo e o proprio scanner nao se acusa ao varrer este arquivo.
TEST_CARDS = {
    "4111" + "1111" + "1111" + "1111",
    "4242" + "4242" + "4242" + "4242",
    "5555" + "5555" + "5555" + "4444",
    "3782" + "82246" + "310005",
    "4000" + "0000" + "0000" + "0002",
    "6011" + "1111" + "1111" + "1117",
}

# Arquivos de configuracao chave=valor, onde a regra _prop faz sentido
CONFIG_EXT = {".properties", ".yml", ".yaml", ".ini", ".cfg", ".conf", ".toml",
              ".env", ".editorconfig", ".tfvars"}

# Leitura de variavel de ambiente = padrao CORRETO, nunca vazamento
ENV_REFERENCE = re.compile(
    r"(?i)(?:process\.env\b|os\.environ|os\.getenv|System\.getenv|ENV\[|"
    r"\$\{[A-Za-z_]|\$[A-Z_]{2,}\b|%[A-Z_]{2,}%|config\.get|dotenv|"
    r"secrets?\.[a-z]|vault:|aws:secretsmanager)"
)


# ------------------------------------------------------------------ utilitarios

def entropy(s: str) -> float:
    if not s:
        return 0.0
    c = Counter(s)
    n = len(s)
    return -sum((v / n) * math.log2(v / n) for v in c.values())


def mask(secret: str) -> str:
    """Mascara o segredo pra saida. NUNCA imprimir valor completo."""
    s = secret.strip()
    if not s:
        return ""
    if len(s) <= 8:
        return s[0] + "*" * (len(s) - 1)
    return f"{s[:4]}{'*' * 8}{s[-4:]}"


def mask_len(secret: str) -> str:
    """Versao com tamanho, para a linha 'valor:' do relatorio."""
    s = (secret or "").strip()
    return f"{mask(s)} (len={len(s)})" if s else ""


def luhn_ok(digits: str) -> bool:
    d = [int(c) for c in digits if c.isdigit()]
    if not 13 <= len(d) <= 19:
        return False
    total, alt = 0, False
    for n in reversed(d):
        if alt:
            n *= 2
            if n > 9:
                n -= 9
        total += n
        alt = not alt
    return total % 10 == 0


def cpf_ok(digits: str) -> bool:
    d = [int(c) for c in digits if c.isdigit()]
    if len(d) != 11 or len(set(d)) == 1:
        return False
    for size in (9, 10):
        s = sum(d[i] * ((size + 1) - i) for i in range(size))
        check = (s * 10) % 11
        check = 0 if check == 10 else check
        if check != d[size]:
            return False
    return True


def is_placeholder(value: str) -> bool:
    v = value.strip()
    if len(v) < 6:
        return True
    if PLACEHOLDER.search(v):
        return True
    if len(set(v)) <= 3:            # 'aaaaaaaa', '11111111'
        return True
    return False


def looks_random(value: str, min_entropy: float = 3.0) -> bool:
    """Segredo real costuma ter entropia alta. Palavra de dicionario, nao."""
    v = value.strip()
    if len(v) < 12:
        return True                  # curto demais pra julgar por entropia
    return entropy(v) >= min_entropy


# ------------------------------------------------------------------ validacao

def validate(rule_id: str, value: str, path: str, line_text: str) -> tuple[bool, str]:
    """Retorna (manter, nota). Filtra falso positivo obvio."""
    v = (value or "").strip()

    if rule_id in {"credit_card"}:
        digits = re.sub(r"[ \-]", "", v)
        if not luhn_ok(digits):
            return False, ""
        if digits in TEST_CARDS:
            return True, "cartao de TESTE conhecido do gateway"
        return True, "passou na validacao Luhn"

    if rule_id == "cpf_raw":
        if not cpf_ok(v):
            return False, ""
        return True, "digitos verificadores validos"

    if rule_id == "cpf":
        return (True, "digitos verificadores validos") if cpf_ok(v) else (True, "formato de CPF, DV invalido")

    if rule_id in {"hardcoded_password", "hardcoded_password_prop", "basic_auth_header"}:
        # Referencia a variavel de ambiente E o padrao CORRETO - nunca e vazamento.
        if ENV_REFERENCE.search(v):
            return False, ""
        if is_placeholder(v):
            return False, ""
        if not looks_random(v, 2.2):
            return False, ""
        if v.lower() in {"true", "false", "none", "null", "localhost", "postgres",
                         "root", "admin", "user", "guest", "default"}:
            return False, ""
        # .properties de config so vale em arquivo de config, nao em codigo-fonte
        if rule_id == "hardcoded_password_prop":
            ext = os.path.splitext(path)[1].lower()
            base = os.path.basename(path).lower()
            if ext not in CONFIG_EXT and not base.startswith(".env"):
                return False, ""

    if rule_id == "email":
        if re.search(r"(?i)(example|test|sample|noreply|no-reply|dummy)\.(com|org|net)$", v):
            return False, ""

    if rule_id == "phone_br":
        digits = re.sub(r"\D", "", v)
        if len(set(digits)) <= 2:
            return False, ""

    if rule_id in {"aws_secret", "twilio", "google_api_key"} and is_placeholder(v):
        return False, ""

    return True, ""


def adjust_severity(sev: str, path: str, ext: str) -> tuple[str, str]:
    """Contexto de teste/doc rebaixa a severidade, mas nao elimina o achado."""
    if TEST_PATH.search(path.replace("\\", "/")):
        lowered = {"critical": "medium", "high": "low", "medium": "low", "low": "low"}
        return lowered[sev], "em caminho de teste/exemplo"
    if ext in DOC_EXT:
        lowered = {"critical": "medium", "high": "low", "medium": "low", "low": "low"}
        return lowered[sev], "em documentacao"
    return sev, ""


# ------------------------------------------------------------------ varredura

def build_rules(include_pii: bool, include_infra: bool):
    rules = list(SECRET_RULES)
    if include_pii:
        rules += PII_RULES
    if include_infra:
        rules += INFRA_RULES
    return [(rid, re.compile(rx), sev, desc, grp) for rid, rx, sev, desc, grp in rules]


def scan_text(text: str, path: str, rules, out: list, source: str = "worktree") -> None:
    lines = text.splitlines()
    ext = os.path.splitext(path)[1].lower()
    seen: set = set()

    for rid, rx, sev, desc, grp in rules:
        for m in rx.finditer(text):
            value = m.group(grp) if grp and m.lastindex and grp <= m.lastindex else m.group(0)
            keep, note = validate(rid, value, path, "")
            if not keep:
                continue
            line_no = text.count("\n", 0, m.start()) + 1
            key = (rid, path, line_no)
            if key in seen:
                continue
            seen.add(key)

            final_sev, ctx = adjust_severity(sev, path, ext)
            notes = [n for n in (note, ctx) if n]
            snippet = lines[line_no - 1].strip()[:150] if line_no <= len(lines) else ""
            # nunca vazar o valor no snippet
            if value and len(value) > 6 and value in snippet:
                snippet = snippet.replace(value, mask(value))

            out.append({
                "rule": rid, "severity": final_sev, "desc": desc,
                "file": path, "line": line_no, "source": source,
                "match": mask_len(value) if value else "",
                "note": "; ".join(notes), "snippet": snippet,
            })
            if len(seen) > 400:
                return


def check_filename(rel: str, out: list, source: str = "worktree") -> None:
    p = rel.replace("\\", "/")
    for rx, sev, desc in DANGEROUS_FILES:
        if re.search(rx, p, re.I):
            final_sev, ctx = adjust_severity(sev, p, os.path.splitext(p)[1].lower())
            out.append({
                "rule": "dangerous_file", "severity": final_sev, "desc": desc,
                "file": p, "line": 0, "source": source, "match": "",
                "note": ctx, "snippet": os.path.basename(p),
            })
            break


def scan_worktree(root: str, rules, max_bytes: int) -> tuple[list, int]:
    findings: list = []
    count = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root).replace("\\", "/")
            ext = os.path.splitext(fn)[1].lower()
            check_filename(rel, findings)
            if ext in SKIP_EXT:
                continue
            try:
                if os.path.getsize(full) > max_bytes:
                    continue
                with open(full, "rb") as fh:
                    raw = fh.read(max_bytes)
            except OSError:
                continue
            if b"\x00" in raw[:4096]:
                continue
            count += 1
            scan_text(raw.decode("utf-8", "replace"), rel, rules, findings)
    return findings, count


# ------------------------------------------------------------------ historico

def git(root: str, *args: str, timeout: int = 90):
    try:
        r = subprocess.run(["git", "--no-pager", "-C", root, *args],
                           capture_output=True, text=True, errors="replace", timeout=timeout)
        return r.stdout if r.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def scan_history(root: str, rules, max_commits: int) -> tuple[list, dict]:
    findings: list = []
    info = {"commits": 0, "deleted_sensitive": [], "available": False}

    if not os.path.isdir(os.path.join(root, ".git")):
        return findings, info
    if not git(root, "rev-parse", "--git-dir").strip():
        return findings, info
    info["available"] = True

    revs = [r for r in git(root, "rev-list", "--all", f"--max-count={max_commits}").split() if r]
    info["commits"] = len(revs)

    # arquivos sensiveis que existiram em qualquer ponto do historico
    names = git(root, "log", "--all", "--pretty=format:", "--name-only", "--diff-filter=A")
    for name in sorted(set(n.strip() for n in names.splitlines() if n.strip())):
        pre = len(findings)
        check_filename(name, findings, source="history")
        if len(findings) > pre:
            findings[-1]["note"] = ("existiu no historico; " + findings[-1]["note"]).strip("; ")
            info["deleted_sensitive"].append(name)

    # conteudo dos blobs adicionados em cada commit
    for rev in revs:
        diff = git(root, "show", rev, "--no-color", "--diff-filter=AM",
                   "--unified=0", "--format=%H", timeout=30)
        if not diff:
            continue
        cur_file = "?"
        added: dict[str, list] = {}
        for ln in diff.splitlines():
            if ln.startswith("+++ b/"):
                cur_file = ln[6:]
            elif ln.startswith("+") and not ln.startswith("+++"):
                added.setdefault(cur_file, []).append(ln[1:])
        for f, chunk in added.items():
            if os.path.splitext(f)[1].lower() in SKIP_EXT:
                continue
            pre = len(findings)
            scan_text("\n".join(chunk), f, rules, findings, source=f"history:{rev[:8]}")
            for fi in findings[pre:]:
                fi["line"] = 0
                fi["note"] = (fi["note"] + f"; adicionado no commit {rev[:8]}").strip("; ")
    return findings, info


# ------------------------------------------------------------------ relatorio

def dedupe(findings: list) -> list:
    """Agrupa achado identico repetido, mantendo o de maior severidade."""
    best: dict = {}
    for f in findings:
        key = (f["rule"], f["file"], f["match"], f["source"].split(":")[0])
        cur = best.get(key)
        if cur is None or SEVERITY_ORDER[f["severity"]] > SEVERITY_ORDER[cur["severity"]]:
            best[key] = f
    return list(best.values())


def main() -> int:
    ap = argparse.ArgumentParser(description="Auditoria de exposicao pre-publicacao")
    ap.add_argument("repo")
    ap.add_argument("--history", action="store_true", help="varrer tambem o historico do git")
    ap.add_argument("--max-commits", type=int, default=400)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--severity", choices=["low", "medium", "high", "critical"], default="low")
    ap.add_argument("--no-pii", action="store_true", help="nao procurar PII/PCI/PHI")
    ap.add_argument("--no-infra", action="store_true", help="nao procurar IP/hostname interno")
    ap.add_argument("--max-bytes", type=int, default=2 * 1024 * 1024)
    args = ap.parse_args()

    root = os.path.abspath(args.repo)
    if not os.path.isdir(root):
        print(f"erro: nao e um diretorio: {root}", file=sys.stderr)
        return 2

    rules = build_rules(not args.no_pii, not args.no_infra)
    findings, scanned = scan_worktree(root, rules, args.max_bytes)

    hist_info = {"available": False, "commits": 0, "deleted_sensitive": []}
    if args.history:
        hf, hist_info = scan_history(root, rules, args.max_commits)
        findings += hf

    findings = dedupe(findings)
    floor = SEVERITY_ORDER[args.severity]
    findings = [f for f in findings if SEVERITY_ORDER[f["severity"]] >= floor]
    findings.sort(key=lambda f: (-SEVERITY_ORDER[f["severity"]], f["source"], f["file"], f["line"]))

    counts = Counter(f["severity"] for f in findings)
    blockers = counts["critical"] + counts["high"]

    if args.json:
        print(json.dumps({
            "repo": root, "files_scanned": scanned, "history": hist_info,
            "counts": dict(counts), "safe_to_publish": blockers == 0,
            "findings": findings,
        }, indent=2, ensure_ascii=False))
        return 0

    print(f"repo    : {root}")
    print(f"arquivos: {scanned}")
    if args.history:
        if hist_info["available"]:
            print(f"historico: {hist_info['commits']} commits varridos")
        else:
            print("historico: nao e repositorio git (ou git indisponivel)")
    print(f"achados : {len(findings)}  "
          f"[critical={counts['critical']} high={counts['high']} "
          f"medium={counts['medium']} low={counts['low']}]\n")

    if not findings:
        print("Nenhum achado no escopo analisado.")
        print("ATENCAO: scanner nao acha 100%. Revisao manual ainda e recomendada,")
        print("principalmente para dado pessoal em fixtures/dumps e secret em formato incomum.")
        if not args.history:
            print("\nVoce NAO varreu o historico. Rode de novo com --history antes de publicar.")
        return 0

    label = {"critical": "CRITICO", "high": "ALTO", "medium": "MEDIO", "low": "BAIXO"}
    for sev in ("critical", "high", "medium", "low"):
        group = [f for f in findings if f["severity"] == sev]
        if not group:
            continue
        print(f"{'=' * 62}\n{label[sev]} ({len(group)})\n{'=' * 62}")
        for f in group:
            loc = f"{f['file']}:{f['line']}" if f["line"] else f["file"]
            src = "" if f["source"] == "worktree" else f"  [{f['source']}]"
            print(f"  {f['desc']}{src}")
            print(f"    {loc}")
            if f["match"]:
                print(f"    valor: {f['match']}")
            if f["note"]:
                print(f"    nota : {f['note']}")
            if f["snippet"]:
                print(f"    > {f['snippet']}")
            print()

    print("=" * 62)
    if blockers:
        print(f"VEREDITO: NAO PUBLICAR — {blockers} bloqueador(es) critico/alto.")
        print("Ordem de remediacao: (1) ROTACIONAR a credencial, (2) tirar do codigo,")
        print("(3) limpar o historico se ja foi commitada, (4) prevenir com .gitignore + hook.")
    else:
        print("VEREDITO: nenhum bloqueador critico/alto no escopo analisado.")
        print("Revise os itens medio/baixo antes de publicar.")
    if not args.history and hist_info["available"] is False:
        print("\nAVISO: historico do git NAO foi varrido. Rode com --history —")
        print("segredo deletado continua no historico e vaza igual.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
