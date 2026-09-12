#!/usr/bin/env python3
"""
deobfuscate.py - Layered deobfuscation WITHOUT executing code.

Decodes base64 (including the UTF-16LE of PowerShell -EncodedCommand), hex,
\\x/%/\\u escapes, String.fromCharCode / [char] arrays, gzip/zlib/bz2 and
single-byte XOR. Repeats as long as the next layer is decodable.

Never uses eval/exec. Data transformations only.

Usage:
    python3 deobfuscate.py --string 'BASE64HERE'
    python3 deobfuscate.py file.ps1
    cat payload.txt | python3 deobfuscate.py -
    python3 deobfuscate.py file.js --extract      # only list the blobs found
"""

from __future__ import annotations

import argparse
import base64
import binascii
import bz2
import gzip
import re
import sys
import zlib

MAX_DEPTH = 12
PREVIEW = 3000

B64_RE = re.compile(r"[A-Za-z0-9+/]{40,}={0,2}")
HEX_RE = re.compile(r"(?:[0-9a-fA-F]{2}){20,}")
XESC_RE = re.compile(r"(?:\\x[0-9a-fA-F]{2}){8,}")
UESC_RE = re.compile(r"(?:\\u[0-9a-fA-F]{4}){8,}")
PESC_RE = re.compile(r"(?:%[0-9a-fA-F]{2}){8,}")
CHARCODE_RE = re.compile(r"(?:String\.fromCharCode|fromCharCode)\s*\(([\s\d,]+)\)")
PSCHAR_RE = re.compile(r"(?:\[char\]\s*(\d+)\s*[+,]?\s*){4,}")

SUSPICIOUS = re.compile(
    r"(?i)(?:https?://|IEX|Invoke-Expression|DownloadString|DownloadFile|"
    r"FromBase64String|powershell|cmd\.exe|/dev/tcp|\bnc\s+-e|reg\s+add|schtasks|"
    r"vssadmin|bcdedit|Add-MpPreference|child_process|os\.system|subprocess|"
    r"CreateRemoteThread|VirtualAlloc|wallet|\.onion|stratum\+|webhooks/|api\.telegram)"
)


def printable_ratio(b: bytes) -> float:
    if not b:
        return 0.0
    ok = sum(1 for c in b if 32 <= c < 127 or c in (9, 10, 13))
    return ok / len(b)


def is_utf16le(b: bytes) -> bool:
    """UTF-16LE text has a null byte at the odd position for most ASCII chars."""
    if len(b) < 8 or len(b) % 2:
        return False
    odd = b[1::2]
    return odd.count(0) / len(odd) > 0.60


def looks_useful(b: bytes) -> bool:
    """Does the decoded layer look like real text (not binary garbage)?

    Evaluates the decoded TEXT, not the raw bytes: a PowerShell -EncodedCommand
    payload is UTF-16LE and would have ~50% null bytes, so it would be rejected
    if we only looked at the bytes.
    """
    if len(b) < 8:
        return False
    if is_utf16le(b):
        try:
            return printable_ratio(b.decode("utf-16-le").encode("utf-8", "replace")) > 0.80
        except UnicodeDecodeError:
            return False
    return printable_ratio(b) > 0.80


def to_text(b: bytes) -> str:
    """Decode, preferring UTF-16LE when the null-byte pattern indicates it."""
    if is_utf16le(b):
        try:
            return b.decode("utf-16-le")
        except UnicodeDecodeError:
            pass
    return b.decode("utf-8", "replace")


# ---------------------------------------------------------------- decoders

def accept(label: str, raw: bytes):
    """Accept the layer if it became useful text, or a recognized compressed blob.

    Without this, a gzip+base64 payload would be discarded: the gzip bytes are
    not printable and would never reach try_compression.
    """
    if looks_useful(raw):
        return (label, raw)
    for fn in (try_compression, try_xor):
        nxt = fn(raw)
        if nxt:
            return (f"{label} -> {nxt[0]}", nxt[1])
    return None


def try_base64(s: str):
    t = re.sub(r"\s+", "", s)
    if len(t) < 24 or not re.fullmatch(r"[A-Za-z0-9+/]+={0,2}", t):
        return None
    try:
        raw = base64.b64decode(t + "=" * (-len(t) % 4), validate=True)
    except (binascii.Error, ValueError):
        return None
    return accept("base64", raw)


def try_hex(s: str):
    t = re.sub(r"[\s:,]|0x|\\x", "", s)
    if len(t) < 40 or len(t) % 2 or not re.fullmatch(r"[0-9a-fA-F]+", t):
        return None
    try:
        raw = bytes.fromhex(t)
    except ValueError:
        return None
    return accept("hex", raw)


def try_escapes(s: str):
    out, kind = s, None
    if XESC_RE.search(out):
        out = re.sub(r"\\x([0-9a-fA-F]{2})", lambda m: chr(int(m.group(1), 16)), out)
        kind = "\\xNN escape"
    if UESC_RE.search(out):
        out = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), out)
        kind = "\\uNNNN escape"
    if PESC_RE.search(out):
        out = re.sub(r"%([0-9a-fA-F]{2})", lambda m: chr(int(m.group(1), 16)), out)
        kind = "%NN url-encode"
    return (kind, out.encode("utf-8", "replace")) if kind and out != s else None


def try_charcode(s: str):
    parts = []
    for m in CHARCODE_RE.finditer(s):
        nums = [int(x) for x in re.findall(r"\d+", m.group(1))]
        if len(nums) >= 6:
            parts.append("".join(chr(n) for n in nums if 0 < n < 0x110000))
    if PSCHAR_RE.search(s):
        nums = [int(x) for x in re.findall(r"\[char\]\s*(\d+)", s)]
        if len(nums) >= 6:
            parts.append("".join(chr(n) for n in nums if 0 < n < 0x110000))
    if not parts:
        return None
    joined = "".join(parts)
    return ("fromCharCode/[char]", joined.encode("utf-8", "replace")) if len(joined) >= 8 else None


def try_compression(b: bytes):
    for name, fn in (
        ("gzip", lambda d: gzip.decompress(d)),
        ("zlib", lambda d: zlib.decompress(d)),
        ("deflate-raw", lambda d: zlib.decompress(d, -15)),
        ("bz2", lambda d: bz2.decompress(d)),
    ):
        try:
            raw = fn(b)
        except Exception:
            continue
        if looks_useful(raw):
            return (name, raw)
    return None


def try_xor(b: bytes):
    """Single-byte XOR - tries all 255 keys, accepts the one that yields text."""
    if len(b) < 24:
        return None
    best = None
    for key in range(1, 256):
        dec = bytes(c ^ key for c in b)
        if printable_ratio(dec) > 0.92 and SUSPICIOUS.search(dec.decode("utf-8", "replace")):
            score = printable_ratio(dec)
            if best is None or score > best[0]:
                best = (score, key, dec)
    return (f"XOR key=0x{best[1]:02x}", best[2]) if best else None


def decode_once(data: bytes):
    """Apply the first transformation that works. Returns (name, bytes) or None."""
    text = to_text(data)

    for fn in (try_charcode, try_escapes):
        r = fn(text)
        if r:
            return r

    # embedded blob: take the largest base64/hex candidate inside the text
    cands = [(m.group(0), m.start()) for m in B64_RE.finditer(text)]
    if cands:
        blob = max(cands, key=lambda c: len(c[0]))[0]
        r = try_base64(blob)
        if r:
            return r

    r = try_base64(text.strip())
    if r:
        return r

    hm = HEX_RE.search(text)
    if hm:
        r = try_hex(hm.group(0))
        if r:
            return r

    for fn in (try_compression, try_xor):
        r = fn(data)
        if r:
            return r
    return None


# ---------------------------------------------------------------- pipeline

def peel(data: bytes, quiet: bool = False) -> bytes:
    current = data
    for depth in range(1, MAX_DEPTH + 1):
        step = decode_once(current)
        if not step:
            if depth == 1 and not quiet:
                print("No recognized encoding layer.\n")
            break
        name, raw = step
        current = raw
        text = to_text(raw)
        if not quiet:
            print(f"--- layer {depth}: {name}  ({len(raw)} bytes) " + "-" * 24)
            print(text[:PREVIEW])
            if len(text) > PREVIEW:
                print(f"... [+{len(text) - PREVIEW} chars]")
            print()
    return current


def report(final: bytes) -> None:
    text = to_text(final)
    hits = sorted(set(m.group(0) for m in SUSPICIOUS.finditer(text)))
    urls = sorted(set(re.findall(r"https?://[^\s'\"<>)\\]+", text)))
    ips = sorted(set(re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", text)))

    print("=" * 60)
    if hits:
        print("Indicators in the final result:")
        for h in hits:
            print(f"  - {h}")
    else:
        print("No obvious indicator in the final result.")
    if urls:
        print("\nURLs (defanged):")
        for u in urls[:25]:
            print("  - " + u.replace("http", "hxxp").replace(".", "[.]", 1))
    if ips:
        print("\nIPs:")
        for i in ips[:25]:
            print("  - " + i.replace(".", "[.]"))
    print("\nNo code was executed - data transformation only.")


def main() -> int:
    ap = argparse.ArgumentParser(description="Layered deobfuscation without executing code")
    ap.add_argument("file", nargs="?", help="input file, or - for stdin")
    ap.add_argument("--string", help="decode this string directly")
    ap.add_argument("--extract", action="store_true",
                    help="only list the encoded blobs found, without decoding")
    args = ap.parse_args()

    if args.string:
        data = args.string.encode()
    elif args.file == "-":
        data = sys.stdin.buffer.read()
    elif args.file:
        with open(args.file, "rb") as fh:
            data = fh.read()
    else:
        ap.print_help()
        return 2

    if args.extract:
        text = to_text(data)
        found = False
        for label, rx in (("base64", B64_RE), ("hex", HEX_RE),
                          ("\\x escape", XESC_RE), ("charcode", CHARCODE_RE)):
            for m in rx.finditer(text):
                line = text.count("\n", 0, m.start()) + 1
                blob = m.group(0)
                print(f"[{label}] line {line}, {len(blob)} chars")
                print(f"  {blob[:100]}{'...' if len(blob) > 100 else ''}\n")
                found = True
        if not found:
            print("No encoded blob found.")
        return 0

    final = peel(data)
    report(final)
    return 0


if __name__ == "__main__":
    sys.exit(main())
