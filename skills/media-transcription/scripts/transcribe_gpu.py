# -*- coding: utf-8 -*-
"""Transcrição local GPU com faster-whisper large-v3 (aceita .wav/.mp3/.mp4 direto).

Uso:
  python transcribe_gpu.py --out-dir DIR --base NOME arquivo1 [arquivo2 ...]
      [--prompt "vocabulário de contexto"] [--language pt] [--beam 5]

Gera por arquivo: <base>-parteN-legenda-<lang>.srt e <base>-parteN-transcript-<lang>.txt
(sem sufixo parteN quando for um arquivo só) e, se houver vários,
<base>-COMPLETO-transcript-<lang>.txt combinado.
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
    """No Windows, ctranslate2 não acha as DLLs pip da NVIDIA sozinho:
    precisa de PATH + pré-carga via ctypes ANTES do import (add_dll_directory não basta)."""
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


def fmt_hms(t):
    t = int(t)
    return f"{t // 3600:02d}:{(t % 3600) // 60:02d}:{t % 60:02d}"


def write_blocks(f, segments):
    block_start, block = None, []
    for s, _e, txt in segments:
        if block_start is None or s - block_start >= 30.0:
            if block:
                f.write(" ".join(block) + "\n\n")
            f.write(f"[{fmt_hms(s)}]\n")
            block_start, block = s, []
        block.append(txt)
    if block:
        f.write(" ".join(block) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--base", required=True)
    ap.add_argument("--prompt", default=None)
    ap.add_argument("--language", default="pt")
    ap.add_argument("--beam", type=int, default=5)
    args = ap.parse_args()

    setup_cuda_dlls()
    from faster_whisper import WhisperModel

    try:
        r = subprocess.run(["nvidia-smi", "--query-gpu=memory.used,memory.total",
                            "--format=csv,noheader"], capture_output=True, text=True, timeout=15)
        print(f"[vram] {r.stdout.strip()} (se quase cheia, feche apps de GPU: "
              f"transcrição pode cair de ~4x para ~0.3x tempo real)", flush=True)
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

    multi = len(args.files) > 1
    all_parts = []
    grand = time.perf_counter()
    for idx, path in enumerate(args.files, 1):
        tag = f"-parte{idx}" if multi else ""
        print(f"\n[{idx}/{len(args.files)}] {os.path.basename(path)}", flush=True)
        t1 = time.perf_counter()
        seg_iter, info = model.transcribe(
            path, language=args.language, vad_filter=True,
            beam_size=args.beam, initial_prompt=args.prompt)
        print(f"[audio] {fmt_hms(info.duration)}", flush=True)
        segments = []
        last = 0.0
        for seg in seg_iter:
            segments.append((seg.start, seg.end, seg.text.strip()))
            el = time.perf_counter() - t1
            if el - last >= 10.0:
                last = el
                print(f"[prog] {fmt_hms(seg.end)}/{fmt_hms(info.duration)} | {el:6.1f}s | "
                      f"{seg.end / el:4.1f}x", flush=True)
        took = time.perf_counter() - t1
        print(f"[done] {took / 60:.1f} min | {len(segments)} seg | "
              f"{info.duration / took:.2f}x tempo real", flush=True)
        all_parts.append((os.path.basename(path), info.duration, segments))

        with open(os.path.join(args.out_dir, f"{args.base}{tag}-legenda-{args.language}.srt"),
                  "w", encoding="utf-8") as f:
            for i, (s, e, txt) in enumerate(segments, 1):
                f.write(f"{i}\n{fmt_srt(s)} --> {fmt_srt(e)}\n{txt}\n\n")
        with open(os.path.join(args.out_dir, f"{args.base}{tag}-transcript-{args.language}.txt"),
                  "w", encoding="utf-8") as f:
            f.write(f"TRANSCRIPT — {os.path.basename(path)} ({fmt_hms(info.duration)})\n")
            f.write("faster-whisper large-v3 GPU — revisar nomes próprios.\n\n")
            write_blocks(f, segments)

    if multi:
        combo = os.path.join(args.out_dir, f"{args.base}-COMPLETO-transcript-{args.language}.txt")
        with open(combo, "w", encoding="utf-8") as f:
            f.write(f"TRANSCRIPT COMPLETO — {args.base}\n"
                    "Partes sequenciais; timestamps reiniciam por parte.\n")
            for i, (name, dur, segments) in enumerate(all_parts, 1):
                f.write(f"\n{'=' * 70}\nPARTE {i}/{len(all_parts)} — {name} "
                        f"({fmt_hms(dur)})\n{'=' * 70}\n\n")
                write_blocks(f, segments)
        print(f"[out] {combo}", flush=True)

    total_audio = sum(p[1] for p in all_parts)
    total = time.perf_counter() - grand
    print(f"[fim] áudio {fmt_hms(total_audio)} | {total / 60:.1f} min | "
          f"{total_audio / total:.2f}x tempo real", flush=True)


if __name__ == "__main__":
    main()
