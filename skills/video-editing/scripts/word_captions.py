# -*- coding: utf-8 -*-
"""Legendas word-level (estilo CapCut/Reels) com faster-whisper GPU.

Transcreve com word_timestamps=True, agrupa em blocos curtos (2-3 palavras)
e gera .ass pronto para queimar (ffmpeg -vf ass=...) + .srt dos mesmos blocos.

Uso:
  python word_captions.py VIDEO --out-dir DIR --base NOME [--language en]
      [--prompt "nomes e jargão"] [--max-words 3] [--max-dur 1.2]
      [--res 1080x1920] [--font "Arial Black"] [--font-size 88]
      [--margin-v 400] [--no-upper]

IMPORTANTE: transcreva o VÍDEO JÁ CORTADO (timestamps nascem certos no
timeline final). Queima depois (WSL): ffmpeg -nostdin -y -i corte.mp4
  -vf "ass=/tmp/subs.ass:fontsdir=/mnt/c/Windows/Fonts"
  -c:v libx264 -crf 18 -preset slow -c:a copy saida.mp4
"""
import argparse
import ctypes
import glob
import os
import site
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def setup_cuda_dlls():
    """Windows: ctranslate2 não acha as DLLs pip da NVIDIA sozinho —
    precisa de PATH + pré-carga ctypes ANTES do import (add_dll_directory não basta)."""
    roots = []
    for sp in site.getsitepackages() + [site.getusersitepackages()]:
        if sp and os.path.isdir(os.path.join(sp, "nvidia")):
            roots.append(sp)
    dll_dirs = []
    for root in roots:
        for sub in ("cublas", "cudnn", "cuda_nvrtc"):
            for d in glob.glob(os.path.join(root, "nvidia", sub, "bin")):
                os.add_dll_directory(d)
                dll_dirs.append(d)
    if dll_dirs:
        os.environ["PATH"] = os.pathsep.join(dll_dirs) + os.pathsep + os.environ.get("PATH", "")
    preload = [
        "cublasLt64_12.dll", "cublas64_12.dll", "nvrtc64_120_0.dll",
        "cudnn64_9.dll", "cudnn_graph64_9.dll", "cudnn_ops64_9.dll",
        "cudnn_engines_precompiled64_9.dll", "cudnn_engines_runtime_compiled64_9.dll",
        "cudnn_engines_tensor_ir64_9.dll", "cudnn_heuristic64_9.dll",
        "cudnn_cnn64_9.dll", "cudnn_adv64_9.dll", "cudnn_ext64_9.dll",
    ]
    for name in preload:
        for d in dll_dirs:
            p = os.path.join(d, name)
            if os.path.exists(p):
                try:
                    ctypes.WinDLL(p)
                except OSError as e:
                    print(f"[setup] preload FALHOU {name}: {e}", flush=True)
                break


def fmt_srt(t):
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def fmt_ass(t):
    cs = int(round(t * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h:d}:{m:02d}:{s:02d}.{cs:02d}"


def group_words(words, max_words, max_dur, max_gap=0.6):
    """Agrupa palavras em blocos curtos; quebra em pontuação forte, limite de
    palavras, duração ou pausa. Estende o fim até a próxima palavra (sem piscar)."""
    blocks = []
    cur = []
    for w in words:
        if cur:
            gap = w["start"] - cur[-1]["end"]
            dur = w["end"] - cur[0]["start"]
            prev_txt = cur[-1]["word"]
            if (len(cur) >= max_words or dur >= max_dur or gap > max_gap
                    or prev_txt.rstrip().endswith((".", "?", "!", ",", ";", ":"))):
                blocks.append(cur)
                cur = []
        cur.append(w)
    if cur:
        blocks.append(cur)

    out = []
    for i, b in enumerate(blocks):
        start = b[0]["start"]
        end = b[-1]["end"]
        if i + 1 < len(blocks):
            nxt = blocks[i + 1][0]["start"]
            end = nxt if (nxt - end) < 0.5 else end + 0.2
        else:
            end += 0.3
        end = max(end, start + 0.3)
        text = " ".join(w["word"].strip() for w in b)
        out.append((start, end, text))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--base", required=True)
    ap.add_argument("--language", default="en")
    ap.add_argument("--prompt", default=None)
    ap.add_argument("--beam", type=int, default=5)
    ap.add_argument("--max-words", type=int, default=3)
    ap.add_argument("--max-dur", type=float, default=1.2)
    ap.add_argument("--res", default="1080x1920")
    ap.add_argument("--font", default="Arial Black")
    ap.add_argument("--font-size", type=int, default=88)
    ap.add_argument("--margin-v", type=int, default=400)
    ap.add_argument("--no-upper", action="store_true")
    args = ap.parse_args()

    setup_cuda_dlls()
    from faster_whisper import WhisperModel

    try:
        r = subprocess.run(["nvidia-smi", "--query-gpu=memory.used,memory.total",
                            "--format=csv,noheader"], capture_output=True, text=True, timeout=15)
        print(f"[vram] {r.stdout.strip()}", flush=True)
    except Exception:
        pass

    t0 = time.perf_counter()
    model = None
    for ct in ("int8_float16", "int8"):
        try:
            model = WhisperModel("large-v3", device="cuda", compute_type=ct)
            print(f"[load] large-v3 cuda {ct} em {time.perf_counter() - t0:.1f}s", flush=True)
            break
        except Exception as e:
            print(f"[load] {ct} falhou: {e}", flush=True)
    if model is None:
        print("[fatal] GPU indisponível — NÃO caia para CPU sem perguntar ao usuário", flush=True)
        sys.exit(2)

    t1 = time.perf_counter()
    seg_iter, info = model.transcribe(
        args.video, language=args.language, vad_filter=True,
        beam_size=args.beam, initial_prompt=args.prompt, word_timestamps=True)
    print(f"[audio] {info.duration:.1f}s", flush=True)

    words = []
    for seg in seg_iter:
        for w in seg.words or []:
            words.append({"start": w.start, "end": w.end, "word": w.word})
    took = time.perf_counter() - t1
    print(f"[done] {took:.1f}s | {len(words)} palavras | "
          f"{info.duration / took:.1f}x tempo real", flush=True)

    blocks = group_words(words, args.max_words, args.max_dur)
    if not args.no_upper:
        blocks = [(s, e, t.upper()) for s, e, t in blocks]
    print(f"[blocks] {len(blocks)} blocos (média {info.duration / max(len(blocks), 1):.1f}s)",
          flush=True)

    w, h = args.res.lower().split("x")
    ass_path = os.path.join(args.out_dir, f"{args.base}-words.ass")
    with open(ass_path, "w", encoding="utf-8") as f:
        f.write("[Script Info]\nScriptType: v4.00+\n"
                f"PlayResX: {w}\nPlayResY: {h}\nWrapStyle: 2\n\n"
                "[V4+ Styles]\n"
                "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
                "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
                "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
                "Alignment, MarginL, MarginR, MarginV, Encoding\n"
                f"Style: Reels,{args.font},{args.font_size},&H00FFFFFF,&H00FFFFFF,"
                "&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,7,0,2,60,60,"
                f"{args.margin_v},1\n\n"
                "[Events]\n"
                "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, "
                "Effect, Text\n")
        for s, e, txt in blocks:
            f.write(f"Dialogue: 0,{fmt_ass(s)},{fmt_ass(e)},Reels,,0,0,0,,{txt}\n")

    srt_path = os.path.join(args.out_dir, f"{args.base}-words.srt")
    with open(srt_path, "w", encoding="utf-8") as f:
        for i, (s, e, txt) in enumerate(blocks, 1):
            f.write(f"{i}\n{fmt_srt(s)} --> {fmt_srt(e)}\n{txt}\n\n")

    print(f"[out] {ass_path}", flush=True)
    print(f"[out] {srt_path}", flush=True)


if __name__ == "__main__":
    main()
