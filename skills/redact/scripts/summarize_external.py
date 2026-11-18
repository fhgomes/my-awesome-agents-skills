#!/usr/bin/env python3
"""
summarize_external.py - value-free summary of reports written by external secret scanners.

Some scanners write raw secret values into their reports even when asked to redact
(TruffleHog always does; gitleaks/Betterleaks keep other secrets inside `Match` when two
sit in one match; Trivy keeps the surrounding source lines in `Code`). Never paste such a
report into a chat, issue or PR. Pipe it through this script instead.

The summary contains only: tool, rule, file, line, commit, date, verification status, count,
and whether the file still exists in HEAD. It is built from an allowlist of fields; no
`Secret`, `Match`, `Raw`, `Line`, `Code`, `snippet`, `ExtraData`, author or message field is
ever read into the output. As a second guard, any output field that contains a 5+ character
piece of the report's secret/match text is withheld.

Supported formats (auto-detected per file):
  gitleaks / Betterleaks   --report-format json          (JSON array)
  TruffleHog v3            --json                        (JSON lines)
  Kingfisher               --format json | jsonl
  Trivy                    --format json  (fs, repo, image; secret scanner)
  detect-secrets           scan output / baseline        (JSON)

Usage:
  python3 summarize_external.py REPORT [REPORT ...] [--repo PATH] [--tool NAME] [--json]
  ... | python3 summarize_external.py -            # report on stdin

  --repo PATH   the repository that was scanned: paths are made relative to it and each
                finding is marked "file in HEAD" (the file exists in HEAD; the secret may
                or may not still be in it), "history only" (file not in HEAD's tree: deleted,
                renamed, or only on another branch) or "not tracked" (working tree only)
  --tool NAME   override the detected tool label (e.g. gitleaks vs betterleaks)
  --low-signal RULE   treat an extra rule id as low-signal (repeatable)

Exit code: 0 no findings, 1 findings, 2 usage/parse error. Stdlib only.
"""
import argparse
import json
import os
import re
import subprocess
import sys

# Generic, keyword/entropy-driven rules: noisy, reported apart as low-signal.
LOW_SIGNAL = re.compile(
    r"(^|[.:/])generic-api-key$|high entropy string$|^secret keyword$", re.I)

SENSITIVE_KEYS = {"secret", "match", "raw", "rawv2", "redacted", "line", "snippet",
                  "hashed_secret", "content", "code", "secretparts", "extradata",
                  "structureddata", "message", "author", "email", "createdby"}


def collect_sensitive(obj, out, key=""):
    """Gather every string under a sensitive key, for the second guard."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            collect_sensitive(v, out, k if k.lower() in SENSITIVE_KEYS else key)
    elif isinstance(obj, list):
        for v in obj:
            collect_sensitive(v, out, key)
    elif isinstance(obj, str) and key and len(obj) >= 5:
        out.append(obj)


def pieces(texts):
    """5-char windows of the sensitive strings, minus markers every tool prints anyway."""
    out = set()
    for t in texts:
        for tok in re.split(r"[\s\"'=:,;()\[\]{}<>@/]+", t):
            tok = tok.replace("REDACTED", " ").replace("*", " ")
            for part in tok.split():
                # secret-looking material only: 8+ chars with a digit or mixed case;
                # plain words from code context would only cause needless withholding
                if len(part) < 8 or not (re.search(r"\d", part) or
                                         (re.search(r"[a-z]", part) and re.search(r"[A-Z]", part))):
                    continue
                for i in range(len(part) - 4):
                    out.add(part[i:i + 5])
    return out


def clean(s, limit=200):
    s = "" if s is None else str(s)
    s = re.sub(r"[\x00-\x1f\x7f]", "?", s)
    return s if len(s) <= limit else s[:limit] + "..."


def short_date(s):
    m = re.match(r"\d{4}-\d{2}-\d{2}", str(s or ""))
    return m.group(0) if m else ""


# ---------------------------------------------------------------- parsers
def parse_gitleaks(items, tool):
    for f in items:
        label = tool or ("betterleaks" if "Attributes" in f else "gitleaks")
        yield f, dict(tool=label, rule=f.get("RuleID"), file=f.get("File"),
                      line=f.get("StartLine"), commit=(f.get("Commit") or "")[:12],
                      date=short_date(f.get("Date")), status="")


def parse_trufflehog(items, tool):
    for f in items:
        data = (f.get("SourceMetadata") or {}).get("Data") or {}
        src = next(iter(data.values()), {}) if data else {}
        verified = f.get("Verified")
        status = "verified LIVE" if verified else ("verification error" if f.get("VerificationError")
                                                    else "unverified")
        yield f, dict(tool=tool or "trufflehog", rule=f.get("DetectorName"),
                      file=src.get("file") or src.get("path"), line=src.get("line"),
                      commit=(src.get("commit") or "")[:12], date=short_date(src.get("timestamp")),
                      status=status)


def parse_kingfisher(items, tool):
    for x in items:
        f = x.get("finding") or {}
        gm = f.get("git_metadata") or {}
        c = gm.get("commit") or {}
        path = ((gm.get("file") or {}).get("path")) or f.get("path")
        st = ((f.get("validation") or {}).get("status")) or ""
        yield x, dict(tool=tool or "kingfisher", rule=(x.get("rule") or {}).get("id"),
                      file=path, line=f.get("line"), commit=(c.get("id") or "")[:12],
                      date=short_date(c.get("date")), status=st)


def parse_trivy(doc, tool):
    image = doc.get("ArtifactType") == "container_image"
    for r in doc.get("Results") or []:
        for s in r.get("Secrets") or []:
            layer = ((s.get("Layer") or {}).get("DiffID") or "").replace("sha256:", "")[:12]
            target = r.get("Target")
            if image and not layer:
                # no layer = found in the image config (ENV, labels, build history)
                layer, target = "config", "<image config: ENV/labels/history>"
            yield s, dict(tool=tool or "trivy", rule=s.get("RuleID"), file=target,
                          line=s.get("StartLine"), commit="", date="",
                          status=(s.get("Severity") or "").lower(),
                          layer=layer if image else "")


def parse_detect_secrets(doc, tool):
    for path, lst in (doc.get("results") or {}).items():
        for s in lst:
            yield s, dict(tool=tool or "detect-secrets", rule=s.get("type"), file=path,
                          line=s.get("line_number"), commit="", date="",
                          status="verified LIVE" if s.get("is_verified") else "")


def load(text, tool):
    text = text.strip()
    if not text:
        return "empty", []
    try:
        doc = json.loads(text)
    except json.JSONDecodeError:
        doc = None
        items = []
        for ln in text.splitlines():
            ln = ln.strip()
            if ln.startswith("{"):
                try:
                    items.append(json.loads(ln))
                except json.JSONDecodeError:
                    pass
        if not items:
            raise ValueError("not JSON / JSON lines")
        if "DetectorName" in items[0] or "SourceMetadata" in items[0]:
            return "trufflehog", list(parse_trufflehog(items, tool))
        if "finding" in items[0] and "rule" in items[0]:
            return "kingfisher", list(parse_kingfisher(items, tool))
        raise ValueError("unknown JSON-lines format")
    if isinstance(doc, list):
        if not doc:
            return "empty", []
        if "RuleID" in doc[0]:
            return "gitleaks", list(parse_gitleaks(doc, tool))
        if "DetectorName" in doc[0]:
            return "trufflehog", list(parse_trufflehog(doc, tool))
        if "finding" in doc[0]:
            return "kingfisher", list(parse_kingfisher(doc, tool))
    if isinstance(doc, dict):
        if "DetectorName" in doc:
            return "trufflehog", list(parse_trufflehog([doc], tool))
        if "findings" in doc and ("metadata" in doc or "audit" in doc):
            return "kingfisher", list(parse_kingfisher(doc.get("findings") or [], tool))
        if "Results" in doc and "SchemaVersion" in doc:
            return "trivy", list(parse_trivy(doc, tool))
        if isinstance(doc.get("results"), dict):
            return "detect-secrets", list(parse_detect_secrets(doc, tool))
    raise ValueError("unrecognized report format")


# ---------------------------------------------------------------- repo state
def head_files(repo):
    try:
        out = subprocess.run(["git", "--no-pager", "-C", repo, "ls-tree", "-r", "-z",
                              "--name-only", "HEAD"], capture_output=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0:
        return None
    return set(p.decode("utf-8", "replace") for p in out.stdout.split(b"\0") if p)


def locate(rec, repo, head):
    path = rec.get("file") or ""
    if rec.get("layer") == "config":
        return path, "image config"
    if rec.get("layer"):
        return path, "image layer " + rec["layer"]
    if repo:
        rp = os.path.realpath(repo)
        if os.path.isabs(path):
            real = os.path.realpath(path)
            if real.startswith(rp + os.sep):
                path = os.path.relpath(real, rp)
        path = path[2:] if path.startswith("./") else path
    if re.match(r"(.*/)?\.git/objects/", path) or path.startswith(".git/"):
        return ".git/objects/<object>", "git object (history)"
    if head is None:
        return path, "commit " + rec["commit"] if rec.get("commit") else ""
    if path in head:
        return path, "file in HEAD"
    if rec.get("commit"):
        return path, "history only"
    return path, "not tracked"


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("reports", nargs="+", help="report files, or - for stdin")
    ap.add_argument("--repo", help="scanned repository (enables in-HEAD / history-only marking)")
    ap.add_argument("--tool", help="override the tool label")
    ap.add_argument("--low-signal", action="append", default=[], metavar="RULE")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    head = head_files(a.repo) if a.repo else None
    findings, problems = [], []
    for rp in a.reports:
        try:
            text = sys.stdin.read() if rp == "-" else open(rp, encoding="utf-8", errors="replace").read()
            fmt, parsed = load(text, a.tool)
        except (OSError, ValueError) as e:
            problems.append(f"{os.path.basename(rp)}: {e}")
            continue
        for raw, rec in parsed:
            sens = []
            collect_sensitive(raw, sens)
            bad = pieces(sens)
            rec["file"], rec["where"] = locate(rec, a.repo, head)
            out = {}
            for k in ("tool", "rule", "file", "line", "commit", "date", "status", "where"):
                v = clean(rec.get(k)) if k != "line" else rec.get(k)
                if isinstance(v, str) and any(p in v for p in bad if len(v) >= 5):
                    v = "<withheld: overlaps secret text>"
                out[k] = v if v not in (None, "") else ("" if k != "line" else None)
            rid = out["rule"] or ""
            out["low_signal"] = bool(LOW_SIGNAL.search(rid)) or rid in a.low_signal
            out["report"] = "stdin" if rp == "-" else os.path.basename(rp)
            findings.append(out)

    if a.json:
        json.dump({"findings": findings, "problems": problems,
                   "counts": {"total": len(findings),
                              "low_signal": sum(f["low_signal"] for f in findings),
                              "by_where": count(findings, "where"),
                              "by_tool": count(findings, "tool")}},
                  sys.stdout, indent=2)
        print()
    else:
        print_text(findings, problems, a.repo)
    sys.exit(2 if problems and not findings else (1 if findings else 0))


def count(fs, key):
    c = {}
    for f in fs:
        c[f[key] or "unchecked"] = c.get(f[key] or "unchecked", 0) + 1
    return c


def print_text(findings, problems, repo):
    print("External scanner summary - no secret value or match text is shown")
    for p in problems:
        print("  could not read:", p)
    if not findings:
        print("  no findings in the given report(s)")
        return
    tools = count(findings, "tool")
    print("  findings:", len(findings), "|", ", ".join(f"{t}={n}" for t, n in sorted(tools.items())))
    if not repo:
        print("  (pass --repo PATH to mark each finding in HEAD / history only)")
    for title, sel in (("HIGH-SIGNAL (named formats)", False),
                       ("LOW-SIGNAL (generic keyword/entropy rules - expect noise, confirm by hand)", True)):
        group = [f for f in findings if f["low_signal"] == sel]
        if not group:
            continue
        print(f"\n{title}: {len(group)}")
        rules = {}
        for f in group:
            rules.setdefault((f["tool"], f["rule"]), []).append(f)
        for (tool, rule), lst in sorted(rules.items(), key=lambda kv: (-len(kv[1]), kv[0])):
            print(f"  [{tool}] {rule}  x{len(lst)}")
            for f in sorted(lst, key=lambda f: (f["file"], f["line"] or 0)):
                loc = f"{f['file']}:{f['line']}" if f["line"] is not None else f["file"]
                extra = " ".join(x for x in (
                    f"commit {f['commit']}" if f["commit"] else "", f["date"], f["status"],
                    f"[{f['where']}]" if f["where"] else "") if x)
                print(f"      {loc}  {extra}")
    w = count(findings, "where")
    print("\nWHERE:", ", ".join(f"{k}={n}" for k, n in sorted(w.items())))


if __name__ == "__main__":
    main()
