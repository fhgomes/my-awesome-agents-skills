#!/usr/bin/env python3
"""Re-locate planned cut points from a synthetic-timing SRT onto a real one.

When a transcriber loses its VAD reference on a long recording it keeps
producing correct text but slices the rest of the file at a fixed interval.
The transcript is usable; the timestamps are not. If cut points were already
planned against that file, shifting them by hand is guesswork.

This script re-locates each cut by TEXT ANCHOR: it reads the words spoken
around the old timestamp, searches for that phrase in a word-level SRT
(real timing), and reports where it actually is.

    python remap_timestamps.py --synthetic bad.srt --words good.srt \
        --cuts cuts.json --out remapped.json

`cuts.json` is a list of objects with at least `id` and `start`, both in
seconds or "MM:SS.s" / "HH:MM:SS.s"; `end` is optional and its duration is
preserved. Anything else in each object is passed through untouched.

Anchors fail on phrases that are too short or too generic. Those fall back to
the median offset of the cuts that did match and are marked
`"method": "offset"` — confirm them by ear before encoding.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import unicodedata

TIME_RE = re.compile(
    r"(\d\d):(\d\d):(\d\d),(\d\d\d)\s*-->\s*(\d\d):(\d\d):(\d\d),(\d\d\d)"
)
MIN_ANCHOR_WORDS = 4
MIN_MATCH_RATIO = 0.55


def normalize(text: str) -> str:
    """Lowercase, strip accents and punctuation, so matching survives ASR drift."""
    decomposed = unicodedata.normalize("NFD", text.lower())
    stripped = "".join(c for c in decomposed if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9 ]", " ", stripped)


def parse_srt(path: str) -> list[dict]:
    with open(path, encoding="utf-8-sig") as handle:
        raw = handle.read()
    blocks = []
    for chunk in re.split(r"\n\s*\n", raw.strip()):
        lines = chunk.strip().split("\n")
        if len(lines) < 2:
            continue
        match = next((TIME_RE.match(line) for line in lines[:2] if TIME_RE.match(line)), None)
        if not match:
            continue
        g = [int(x) for x in match.groups()]
        start = g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000
        end = g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 1000
        text = " ".join(line for line in lines if not TIME_RE.match(line) and not line.strip().isdigit())
        blocks.append({"start": start, "end": end, "text": text.strip()})
    if not blocks:
        sys.exit(f"error: no subtitle blocks found in {path}")
    return blocks


def parse_time(value) -> float:
    """Accept seconds (int/float/str) or MM:SS.s / HH:MM:SS.s."""
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if ":" not in text:
        return float(text)
    parts = [float(p) for p in text.split(":")]
    seconds = 0.0
    for part in parts:
        seconds = seconds * 60 + part
    return seconds


def fmt(seconds: float) -> str:
    return f"{int(seconds // 60):02d}:{seconds % 60:06.3f}"


def phrase_around(blocks: list[dict], when: float, window: float) -> str:
    """The words spoken within `window` seconds of `when`."""
    return " ".join(
        b["text"] for b in blocks if b["start"] < when + window and b["end"] > when - window
    )


def build_index(blocks: list[dict]) -> tuple[list[str], list[float]]:
    """Flatten the SRT into a word sequence plus the start time of each word."""
    words: list[str] = []
    times: list[float] = []
    for block in blocks:
        tokens = normalize(block["text"]).split()
        if not tokens:
            continue
        span = max(block["end"] - block["start"], 0.001) / len(tokens)
        for i, token in enumerate(tokens):
            words.append(token)
            times.append(block["start"] + i * span)
    return words, times


def locate(words: list[str], times: list[float], anchor: str) -> dict | None:
    """Best sliding-window match for `anchor`; None when nothing is convincing."""
    target = normalize(anchor).split()
    if len(target) < MIN_ANCHOR_WORDS:
        return None
    n = len(target)
    best_ratio, best_index = 0.0, None
    for i in range(len(words) - n + 1):
        window = words[i : i + n]
        hits = sum(1 for a, b in zip(target, window) if a == b)
        ratio = hits / n
        if ratio > best_ratio:
            best_ratio, best_index = ratio, i
    if best_index is None or best_ratio < MIN_MATCH_RATIO:
        return None
    return {"start": times[best_index], "confidence": round(best_ratio, 2)}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--synthetic", required=True, help="SRT with the bad timing (source of the anchors)")
    ap.add_argument("--words", required=True, help="word-level SRT with real timing")
    ap.add_argument("--cuts", required=True, help="JSON list of cuts to remap")
    ap.add_argument("--out", help="write the remapped JSON here (default: stdout only)")
    ap.add_argument("--window", type=float, default=6.0, help="seconds of context used as the anchor (default: 6)")
    args = ap.parse_args()

    synthetic = parse_srt(args.synthetic)
    words, times = build_index(parse_srt(args.words))

    with open(args.cuts, encoding="utf-8") as handle:
        cuts = json.load(handle)
    if not isinstance(cuts, list):
        sys.exit("error: --cuts must contain a JSON list")

    results, offsets = [], []
    for cut in cuts:
        if "id" not in cut or "start" not in cut:
            sys.exit("error: every cut needs at least 'id' and 'start'")
        start = parse_time(cut["start"])
        end = parse_time(cut["end"]) if cut.get("end") is not None else None
        found = locate(words, times, phrase_around(synthetic, start, args.window))
        entry = dict(cut)
        entry["original_start"] = round(start, 2)
        if found:
            offsets.append(found["start"] - start)
            entry.update(
                real_start=round(found["start"], 2),
                real_end=round(found["start"] + (end - start), 2) if end is not None else None,
                confidence=found["confidence"],
                method="anchor",
            )
        else:
            entry.update(real_start=None, real_end=None, confidence=None, method="offset")
        results.append(entry)

    if not offsets:
        sys.exit("error: no cut could be anchored — are both files from the same recording?")

    median = statistics.median(offsets)
    for entry in results:
        if entry["method"] != "offset":
            continue
        start = entry["original_start"]
        end = parse_time(entry["end"]) if entry.get("end") is not None else None
        entry["real_start"] = round(start + median, 2)
        entry["real_end"] = round(start + median + (end - start), 2) if end is not None else None

    anchored = sum(1 for e in results if e["method"] == "anchor")
    confident = sum(1 for e in results if e["method"] == "anchor" and e["confidence"] >= 0.8)
    spread = max(offsets) - min(offsets)

    print(f"{'cut':<34}{'old':>10}{'new':>10}{'drift':>9}{'conf':>7}  method")
    for entry in results:
        conf = f"{entry['confidence']:.2f}" if entry["confidence"] is not None else "—"
        drift = entry["real_start"] - entry["original_start"]
        print(
            f"{str(entry['id'])[:33]:<34}{fmt(entry['original_start']):>10}"
            f"{fmt(entry['real_start']):>10}{drift:>+9.1f}{conf:>7}  {entry['method']}"
        )

    print(
        f"\nanchored {anchored}/{len(results)} ({confident} at confidence >= 0.8) | "
        f"median drift {median:+.1f}s | spread {spread:.1f}s"
    )
    if spread > 10:
        print("warning: offsets are scattered — the drift is not a clean systematic shift, review by ear")
    if anchored < len(results):
        print(f"warning: {len(results) - anchored} cut(s) fell back to the median offset — confirm those by ear")

    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            json.dump(results, handle, ensure_ascii=False, indent=2)
        print(f"written: {args.out}")


if __name__ == "__main__":
    main()
