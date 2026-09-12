#!/usr/bin/env python3
"""16:9 -> 9:16 following whoever is speaking (hard-cut pan), no OpenCV, no ML.

Ported from `clipify` (MIT, Louise de Sadeleer) and adapted to the WSL workflow
of this skill. An alternative to SKILL.md's blurred background: instead of
shrinking the video in the middle of the frame, it FRAMES the speaker's face
full-screen at 1080x1920.

How it works (clipify's trick): it does not detect faces. It measures the MEAN
BRIGHTNESS (signalstats.YAVG) of two ROIs — each person's mouth/chin — frame by
frame. Whoever is speaking moves more, so their ROI varies more. Smooth it,
apply hysteresis, and out comes a timeline of who speaks when. A static camera
within the cut is the premise (true for interviews/podcasts).

Typical use (2 steps):

  # 1) find the ROIs: extract a frame and LOOK at it (rules 4/5 of SKILL.md)
  python face_pan.py probe --video IN.mp4 --at 5

  # 2) build the timeline + the ffmpeg filter
  python face_pan.py build --video IN.mp4 \
      --left  100,300,500,400 \
      --right 1300,300,500,400 \
      --out-filter /tmp/pan.txt

Then burn it together with the captions (one encode generation less).

Requires: ffmpeg (the one on PATH by default — this is filter/analysis only, CPU
is fine). Set FFMPEG_BIN to point at a specific build, e.g. a Windows ffmpeg
with NVENC when the one on PATH is CPU-only.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys


def ffmpeg_bin():
    """$FFMPEG_BIN if set, else the ffmpeg on PATH, else the bare name."""
    return os.environ.get("FFMPEG_BIN") or shutil.which("ffmpeg") or "ffmpeg"


def run(cmd, timeout=900):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def parse_roi(s, label):
    """'x,y,w,h' -> (x,y,w,h). Clear error instead of a stack trace."""
    try:
        x, y, w, h = (int(v) for v in s.split(","))
    except Exception:
        sys.exit(f"ERROR: --{label} must be 'x,y,w,h' in pixels. Got: {s!r}")
    if w <= 0 or h <= 0:
        sys.exit(f"ERROR: --{label} has width/height <= 0.")
    return x, y, w, h


def probe_frame(video, at, out_jpg, left=None, right=None):
    """Extract 1 frame (with the ROIs drawn, if given) for visual inspection."""
    ff = ffmpeg_bin()
    cmd = [ff, "-nostdin", "-y", "-ss", str(at), "-i", video, "-frames:v", "1"]
    if left and right:
        lx, ly, lw, lh = left
        rx, ry, rw, rh = right
        cmd += ["-vf", (f"drawbox=x={lx}:y={ly}:w={lw}:h={lh}:color=cyan@0.9:t=4,"
                        f"drawbox=x={rx}:y={ry}:w={rw}:h={rh}:color=magenta@0.9:t=4")]
    cmd += [out_jpg, "-loglevel", "error"]
    p = run(cmd)
    if p.returncode != 0:
        sys.exit(f"ERROR extracting frame:\n{p.stderr[:500]}")
    return out_jpg


def video_info(video):
    """fps, width, height and duration via ffprobe."""
    probe = shutil.which("ffprobe") or "ffprobe"
    p = run([probe, "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height,r_frame_rate,duration",
             "-show_entries", "format=duration", "-of", "json", video])
    if p.returncode != 0:
        sys.exit(f"ERROR in ffprobe:\n{p.stderr[:300]}")
    data = json.loads(p.stdout)
    st = data["streams"][0]
    num, _, den = st["r_frame_rate"].partition("/")
    fps = float(num) / float(den or 1)
    dur = float(st.get("duration") or data.get("format", {}).get("duration") or 0)
    return {"fps": fps, "w": int(st["width"]), "h": int(st["height"]), "dur": dur}


def measure_roi(video, roi, tag, workdir):
    """YAVG (mean brightness) of the ROI, frame by frame, into a log file."""
    ff = ffmpeg_bin()
    x, y, w, h = roi
    out = os.path.join(workdir, f"motion_{tag}.txt")
    # ffmpeg's filter parser treats ':' and '\' as syntax. On a Windows path
    # ("C:\...") that breaks the filter — escape before interpolating.
    esc = out.replace("\\", "/").replace(":", r"\:")
    # crop to the ROI -> signalstats -> metadata:print dumps YAVG per frame.
    vf = f"crop={w}:{h}:{x}:{y},signalstats,metadata=print:file='{esc}'"
    p = run([ff, "-nostdin", "-y", "-i", video, "-vf", vf, "-an",
             "-f", "null", "-"])
    if p.returncode != 0 or not os.path.exists(out):
        sys.exit(f"ERROR measuring ROI {tag} (file={out}):\n"
                 f"{(p.stderr or '')[-800:]}")
    return out


def parse_motion(path):
    """Read the metadata=print log -> (times, YAVG values)."""
    times, vals, cur_t = [], [], None
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            m = re.match(r"frame:\d+\s+pts:\d+\s+pts_time:([0-9.]+)", line)
            if m:
                cur_t = float(m.group(1))
                continue
            m = re.search(r"lavfi\.signalstats\.YAVG=([0-9.]+)", line)
            if m and cur_t is not None:
                times.append(cur_t)
                vals.append(float(m.group(1)))
                cur_t = None
    return times, vals


def deltas(vals):
    """Frame-to-frame variation. Speaking moves the mouth -> YAVG oscillates more.

    The original clipify compares YAVG directly, which mixes scene brightness
    with motion. Using |delta| isolates the motion and copes better with
    different lighting on the two sides of the frame.
    """
    return [0.0] + [abs(vals[i] - vals[i - 1]) for i in range(1, len(vals))]


def smooth(v, win=15):
    """Moving average — removes compression jitter."""
    out = []
    for i in range(len(v)):
        a, b = max(0, i - win // 2), min(len(v), i + win // 2 + 1)
        out.append(sum(v[a:b]) / (b - a))
    return out


def normalize(v):
    m = sum(v) / max(len(v), 1)
    return [x / m if m > 0 else 0.0 for x in v]


def speaker_timeline(t_l, v_l, v_d, fps, min_dur=1.0, margin=1.15):
    """Who speaks in each frame -> segments [start, end, speaker].

    Hysteresis (margin): only switch speaker when the other exceeds the current
    one by 15%. Without it the cut flickers during silence, the classic defect
    of this method. min_dur drops switches too short to read on screen.
    """
    n = min(len(v_l), len(v_d))
    if n == 0:
        sys.exit("ERROR: no motion samples — check the ROIs.")
    s_l = smooth(normalize(deltas(v_l[:n])))
    s_d = smooth(normalize(deltas(v_d[:n])))

    cur = 0 if s_l[0] >= s_d[0] else 1
    speaker = []
    for i in range(n):
        if cur == 0 and s_d[i] > s_l[i] * margin:
            cur = 1
        elif cur == 1 and s_l[i] > s_d[i] * margin:
            cur = 0
        speaker.append(cur)

    # Group consecutive frames of the same speaker.
    segs, start, cur = [], 0, speaker[0]
    for i in range(1, n):
        if speaker[i] != cur:
            segs.append([start / fps, i / fps, cur])
            start, cur = i, speaker[i]
    segs.append([start / fps, n / fps, cur])

    # Absorb short segments into their neighbor (avoids epileptic cutting).
    merged = []
    for seg in segs:
        if merged and (seg[1] - seg[0]) < min_dur:
            merged[-1][1] = seg[1]
        elif merged and merged[-1][2] == seg[2]:
            merged[-1][1] = seg[1]
        else:
            merged.append(seg)
    return merged


def build_filter(segs, info, left, right, target_w=1080, target_h=1920):
    """Crop expression with a hard cut between the two framings.

    The crop window has the source's HEIGHT and width = height*9/16, centered
    horizontally on the speaker's face. Only X changes over time -> a nested
    conditional expression does it, with no per-segment re-encode.
    """
    src_w, src_h = info["w"], info["h"]
    crop_w = int(src_h * target_w / target_h)  # 9:16 within the source height
    crop_w -= crop_w % 2
    if crop_w > src_w:
        sys.exit(f"ERROR: source {src_w}x{src_h} is already narrower than 9:16.")

    def center_x(roi):
        cx = roi[0] + roi[2] // 2
        x = cx - crop_w // 2
        return max(0, min(x, src_w - crop_w))  # keep it inside the frame

    x_l, x_r = center_x(left), center_x(right)

    # if(lt(t,T1), X1, if(lt(t,T2), X2, ...)) — hard cut, no interpolation.
    expr = str(x_r if segs[-1][2] else x_l)
    for start, end, spk in reversed(segs[:-1]):
        expr = f"if(lt(t,{end:.3f}),{x_r if spk else x_l},{expr})"

    return (f"crop=w={crop_w}:h={src_h}:x='{expr}':y=0,"
            f"scale={target_w}:{target_h},setsar=1"), crop_w


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("probe", help="extract a frame so you can find the ROIs")
    p1.add_argument("--video", required=True)
    p1.add_argument("--at", default="5", help="second of the frame (default 5)")
    p1.add_argument("--out", default="/tmp/facepan_probe.jpg")
    p1.add_argument("--left", help="x,y,w,h — if given, draws the box")
    p1.add_argument("--right", help="x,y,w,h — if given, draws the box")

    p2 = sub.add_parser("build", help="measure, build the timeline and the filter")
    p2.add_argument("--video", required=True)
    p2.add_argument("--left", required=True, help="left mouth/chin ROI: x,y,w,h")
    p2.add_argument("--right", required=True, help="right mouth/chin ROI: x,y,w,h")
    p2.add_argument("--min-dur", type=float, default=1.0)
    p2.add_argument("--margin", type=float, default=1.15)
    p2.add_argument("--workdir", default="/tmp/facepan")
    p2.add_argument("--out-filter", help="write the filter chain to this file")
    p2.add_argument("--json", action="store_true", help="print the timeline as JSON")

    a = ap.parse_args()

    if a.cmd == "probe":
        left = parse_roi(a.left, "left") if a.left else None
        right = parse_roi(a.right, "right") if a.right else None
        out = probe_frame(a.video, a.at, a.out, left, right)
        info = video_info(a.video)
        print(f"Source: {info['w']}x{info['h']} @ {info['fps']:.2f}fps, {info['dur']:.1f}s")
        print(f"Frame: {out}")
        print()
        print("Open the .jpg (Read) and note x,y,w,h of each person's MOUTH+CHIN.")
        print("Avoid hands and microphones. Then run 'build' with --left/--right.")
        return

    left, right = parse_roi(a.left, "left"), parse_roi(a.right, "right")
    os.makedirs(a.workdir, exist_ok=True)
    info = video_info(a.video)

    print(f"Source: {info['w']}x{info['h']} @ {info['fps']:.2f}fps", file=sys.stderr)
    print("Measuring left ROI...", file=sys.stderr)
    f_l = measure_roi(a.video, left, "left", a.workdir)
    print("Measuring right ROI...", file=sys.stderr)
    f_r = measure_roi(a.video, right, "right", a.workdir)

    _, v_l = parse_motion(f_l)
    _, v_r = parse_motion(f_r)
    segs = speaker_timeline(None, v_l, v_r, info["fps"], a.min_dur, a.margin)

    vf, crop_w = build_filter(segs, info, left, right)

    n_l = sum(1 for s in segs if s[2] == 0)
    print(f"{len(segs)} segments ({n_l} left, {len(segs)-n_l} right), "
          f"crop window {crop_w}px", file=sys.stderr)

    if a.json:
        print(json.dumps({"segments": segs, "filter": vf, "crop_w": crop_w},
                         indent=2))
    if a.out_filter:
        with open(a.out_filter, "w", encoding="utf-8") as f:
            f.write(vf)
        print(f"Filter written to: {a.out_filter}", file=sys.stderr)
    if not a.json and not a.out_filter:
        print(vf)


if __name__ == "__main__":
    sys.exit(main())
