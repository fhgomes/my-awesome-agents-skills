#!/usr/bin/env python3
"""Report which vendor files in guides/model-selection/vendors/ are stale.

Each vendor file starts with YAML-style frontmatter containing
`last_verified: YYYY-MM-DD`. This script prints one row per vendor with its age
in days and exits with status 1 when any file is older than --max-age-days
(default 30), or has no parseable date. Stdlib only.

Usage:
    python check_staleness.py
    python check_staleness.py --max-age-days 14
    python check_staleness.py --vendors-dir /path/to/vendors --today 2026-11-01
"""

from __future__ import annotations

import argparse
import datetime as dt
import pathlib
import re
import sys

DATE_RE = re.compile(r"^last_verified:\s*['\"]?(\d{4}-\d{2}-\d{2})['\"]?\s*$", re.MULTILINE)
VENDOR_RE = re.compile(r"^vendor:\s*(.+?)\s*$", re.MULTILINE)


def read_frontmatter(path: pathlib.Path) -> str:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return ""
    end = text.find("\n---", 3)
    return text[3:end] if end != -1 else ""


def main() -> int:
    default_dir = pathlib.Path(__file__).resolve().parent.parent / "vendors"
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--vendors-dir", type=pathlib.Path, default=default_dir)
    parser.add_argument("--max-age-days", type=int, default=30)
    parser.add_argument("--today", type=dt.date.fromisoformat, default=dt.date.today(),
                        help="override today's date (YYYY-MM-DD), useful in tests")
    args = parser.parse_args()

    files = sorted(args.vendors_dir.glob("*.md"))
    if not files:
        print(f"No vendor files found in {args.vendors_dir}", file=sys.stderr)
        return 1

    stale = False
    rows = []
    for path in files:
        front = read_frontmatter(path)
        vendor_match = VENDOR_RE.search(front)
        date_match = DATE_RE.search(front)
        vendor = vendor_match.group(1) if vendor_match else path.stem
        if not date_match:
            rows.append((vendor, "missing", "-", "NO DATE"))
            stale = True
            continue
        verified = dt.date.fromisoformat(date_match.group(1))
        age = (args.today - verified).days
        status = "STALE" if age > args.max_age_days else "ok"
        stale = stale or status == "STALE"
        rows.append((vendor, verified.isoformat(), str(age), status))

    width = max(len(r[0]) for r in rows + [("vendor", "", "", "")])
    print(f"{'vendor':<{width}}  last_verified  age_days  status")
    for vendor, verified, age, status in rows:
        print(f"{vendor:<{width}}  {verified:<13}  {age:>8}  {status}")
    print(f"\nThreshold: {args.max_age_days} days. "
          + ("Refresh the STALE rows: see keeping-it-current.md." if stale else "All vendor files are fresh."))
    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(main())
