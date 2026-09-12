#!/usr/bin/env python3
"""Detect this machine's GPU/encoder and print the right encode params.

Assumes no particular card: it asks nvidia-smi and ffmpeg itself what exists
HERE, so the same skill runs on any machine (or falls back to libx264 without
NVIDIA).

Usage:
    python gpu_probe.py                 # human-readable report
    python gpu_probe.py --json          # for consumption by scripts
    python gpu_probe.py --encode-args   # just the ffmpeg param line
    python gpu_probe.py --codec hevc    # HEVC params instead of H.264

ffmpeg resolution: set FFMPEG_BIN to a specific build, e.g. a Windows ffmpeg
with NVENC when the PATH one is CPU-only; otherwise the ffmpeg on PATH is used.

Why this exists: an earlier version hardcoded one card's parameters; a 1650
vs a 1650 SUPER are different NVENC generations (TU117 Volta-class without
B-frames vs TU116 Turing with B-frames), and guessing wrong costs quality or
a failed encode. Better to ask the hardware.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys

# NVENC by chip generation. What actually changes between them:
#   - Volta/TU117 (plain 1650): NO B-frames in H.264.
#   - Turing TU116+ (1650 Super/1660): B-frames OK in H.264 AND HEVC
#     (confirmed by a real encode on 2026-08-09: 44 B-frames in an HEVC test).
#   - Ampere (30xx): same, better quality at the same bitrate.
#   - Ada (40xx): + AV1.
#   - Blackwell (50xx): + AV1, 4:2:2, 2 NVENC chips on most SKUs.
# The table is only the initial guess: test_bframes() confirms empirically and overrides.
NVENC_GENS = [
    # (name regex, generation, h264_bframes, hevc_bframes, max_sessions)
    (r"\b(50[6-9]0|5060|5070|5080|5090)\b", "Blackwell", True, True, 8),
    (r"\b(40[5-9]0|4060|4070|4080|4090)\b", "Ada", True, True, 8),
    (r"\b(30[5-9]0|3060|3070|3080|3090)\b", "Ampere", True, True, 5),
    (r"1650\s*SUPER|1660|1[67]50\s*Ti", "Turing (TU116)", True, True, 3),
    (r"\b1650\b", "Turing (TU117/Volta NVENC)", False, False, 3),
    (r"\b(20[6-8]0|2060|2070|2080)\b", "Turing (TU10x)", True, True, 3),
]


def run(cmd, timeout=25):
    """Run a command and return stdout+stderr. Never raises — returns '' on failure."""
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return (p.stdout or "") + (p.stderr or "")
    except Exception:
        return ""


def find_ffmpeg():
    """ffmpeg with NVENC: $FFMPEG_BIN if set, else the one on PATH, else the bare name."""
    return os.environ.get("FFMPEG_BIN") or shutil.which("ffmpeg") or "ffmpeg"


def probe_gpu():
    """nvidia-smi: name, driver and VRAM. Returns None without NVIDIA."""
    if not shutil.which("nvidia-smi"):
        return None
    out = run(["nvidia-smi", "--query-gpu=name,driver_version,memory.total,memory.used",
               "--format=csv,noheader,nounits"])
    line = next((l for l in out.splitlines() if l.strip() and "," in l), "")
    if not line:
        return None
    parts = [p.strip() for p in line.split(",")]
    if len(parts) < 3:
        return None
    try:
        total, used = int(float(parts[2])), int(float(parts[3])) if len(parts) > 3 else 0
    except ValueError:
        total, used = 0, 0
    return {"name": parts[0], "driver": parts[1], "vram_mb": total, "vram_used_mb": used}


def classify(name):
    """Match the card name to its NVENC generation."""
    for pattern, gen, h264_bf, hevc_bf, sessions in NVENC_GENS:
        if re.search(pattern, name, re.I):
            return {"generation": gen, "h264_bframes": h264_bf,
                    "hevc_bframes": hevc_bf, "max_sessions": sessions}
    # Unknown card: assume the conservative option and trust the empirical test.
    return {"generation": "unknown", "h264_bframes": False,
            "hevc_bframes": False, "max_sessions": 2}


def probe_encoders(ffmpeg):
    """Which NVENC encoders this ffmpeg binary actually exposes."""
    if not ffmpeg:
        return []
    out = run([ffmpeg, "-hide_banner", "-encoders"])
    return sorted(set(re.findall(r"\b(h264_nvenc|hevc_nvenc|av1_nvenc)\b", out)))


def test_bframes(ffmpeg, codec="h264"):
    """Confirm B-frames empirically: encode 1s of synthetic video with -bf 3.

    The per-generation table is a good guess; this test is the truth. An old
    driver or a card missing from the list shows up here.
    """
    if not ffmpeg:
        return None
    out = run([ffmpeg, "-hide_banner", "-nostdin",
               "-f", "lavfi", "-i", "testsrc=size=320x180:rate=30:duration=1",
               "-c:v", f"{codec}_nvenc", "-preset", "p5", "-bf", "3",
               "-f", "null", "-"], timeout=45)
    if not out:
        return None
    # NVENC complains explicitly when the card does not support B-frames.
    if re.search(r"b.?frames? (are )?not supported|InitializeEncoder failed", out, re.I):
        return False
    return bool(re.search(r"frame=\s*\d+", out))


def build_args(caps, codec="h264", quality="normal"):
    """Assemble the encode params for the detected card.

    quality: 'normal' (cq 22, day-to-day) | 'high' (cq 19, final delivery)
    """
    # No NVENC, or the requested codec does not exist on this card (e.g. av1 on
    # Turing) -> fall back to CPU instead of blowing up mid-encode.
    if not caps["nvenc_available"] or f"{codec}_nvenc" not in caps["encoders"]:
        crf = "18" if quality == "high" else "20"
        cpu_enc = {"hevc": "libx265", "av1": "libsvtav1"}.get(codec, "libx264")
        return ["-c:v", cpu_enc, "-preset", "slow", "-crf", crf,
                "-pix_fmt", "yuv420p"]

    enc = f"{codec}_nvenc"
    # p5 = the balance validated on a 4 GB Turing card. Ampere+ cards handle
    # p6/p7 with headroom and do better at the same bitrate.
    preset = "p6" if caps["generation"] in ("Ampere", "Ada", "Blackwell") else "p5"
    cq = "19" if quality == "high" else "22"
    args = ["-c:v", enc, "-preset", preset, "-rc", "vbr", "-cq", cq, "-b:v", "0",
            "-pix_fmt", "yuv420p"]

    bf_ok = caps["hevc_bframes"] if codec == "hevc" else caps["h264_bframes"]
    if bf_ok:
        # B-frames cut bitrate without losing quality. 3 is the sweet spot.
        args += ["-bf", "3"]
    return args


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true", help="JSON output")
    ap.add_argument("--encode-args", action="store_true",
                    help="just the ffmpeg param line")
    ap.add_argument("--codec", default="h264", choices=["h264", "hevc", "av1"],
                    help="av1 only exists on Ada/Blackwell (40xx/50xx)")
    ap.add_argument("--quality", default="normal", choices=["normal", "high"])
    ap.add_argument("--no-test", action="store_true",
                    help="skip the empirical B-frame test (faster)")
    args = ap.parse_args()

    ffmpeg = find_ffmpeg()
    gpu = probe_gpu()
    encoders = probe_encoders(ffmpeg)

    caps = {
        "gpu": gpu["name"] if gpu else None,
        "driver": gpu["driver"] if gpu else None,
        "vram_mb": gpu["vram_mb"] if gpu else 0,
        "vram_used_mb": gpu["vram_used_mb"] if gpu else 0,
        "ffmpeg": ffmpeg,
        "encoders": encoders,
        "nvenc_available": bool(encoders),
    }
    caps.update(classify(gpu["name"]) if gpu else
                {"generation": "no NVIDIA", "h264_bframes": False,
                 "hevc_bframes": False, "max_sessions": 0})

    # The empirical test overrides the table — test EVERY available codec, not
    # just the requested one (otherwise the report shows the other codec from
    # the table).
    if caps["nvenc_available"] and not args.no_test:
        for codec, key in (("h264", "h264_bframes"), ("hevc", "hevc_bframes")):
            if f"{codec}_nvenc" not in caps["encoders"]:
                continue
            measured = test_bframes(ffmpeg, codec)
            if measured is not None:
                caps[f"{key}_measured"] = measured
                caps[key] = measured

    enc_args = build_args(caps, args.codec, args.quality)

    if args.encode_args:
        print(" ".join(enc_args))
        return
    if args.json:
        caps["encode_args"] = enc_args
        print(json.dumps(caps, indent=2, ensure_ascii=False))
        return

    print(f"GPU .............. {caps['gpu'] or 'no NVIDIA detected'}")
    if gpu:
        free = caps["vram_mb"] - caps["vram_used_mb"]
        print(f"Driver ........... {caps['driver']}")
        print(f"VRAM ............. {caps['vram_mb']} MB "
              f"({free} MB free)")
        print(f"NVENC generation . {caps['generation']}")
    print(f"ffmpeg ........... {caps['ffmpeg'] or 'NOT FOUND'}")
    print(f"NVENC encoders ... {', '.join(caps['encoders']) or 'none (CPU only)'}")
    print(f"B-frames H.264 ... {caps['h264_bframes']}"
          f"{' (tested)' if 'h264_bframes_measured' in caps else ''}")
    print(f"B-frames HEVC .... {caps['hevc_bframes']}")
    print(f"Parallel encodes   max {caps['max_sessions']}")
    print()
    print("ffmpeg params:")
    print("  " + " ".join(enc_args))

    # Warnings that matter in practice.
    if gpu and caps["vram_mb"] <= 4096:
        print()
        print("WARNING: 4 GB of VRAM — run ONE whisper at a time (see media-transcription).")
    if gpu and caps["vram_used_mb"] > 1500:
        print()
        print(f"WARNING: {caps['vram_used_mb']} MB of VRAM already in use (a game running?) — "
              "consider CPU int8 for transcription.")


if __name__ == "__main__":
    sys.exit(main())
