#!/usr/bin/env python3
"""Detecta a GPU/encoder desta maquina e imprime os params de encode certos.

Nao assume placa nenhuma: pergunta pro nvidia-smi e pro proprio ffmpeg o que
existe AQUI. Serve pra rodar tanto na 1650 Super do Fernando quanto na 3050
da esposa (ou numa maquina sem NVIDIA — ai cai pra libx264).

Uso:
    python gpu_probe.py                 # relatorio legivel
    python gpu_probe.py --json          # pra consumir em script
    python gpu_probe.py --encode-args   # so a linha de params pro ffmpeg
    python gpu_probe.py --codec hevc    # params de HEVC em vez de H.264

Por que isso existe: a skill tinha "GTX 1650" hardcoded no texto, mas a placa
real e uma 1650 SUPER (TU116, NVENC Turing) — gerador diferente do 1650 liso
(TU117, NVENC Volta, sem B-frames). Chutar errado custa qualidade ou um encode
que falha no meio. Melhor perguntar.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys

# ffmpeg do Windows com NVENC (BtbN n7.1 pinado — ver SKILL.md).
FFMPEG_WIN = r"C:\Users\ferna\Tools\ffmpeg71\ffmpeg-n7.1-latest-win64-gpl-7.1\bin\ffmpeg.exe"

# NVENC por geracao de chip. O que muda de verdade entre elas:
#   - Volta/TU117 (1650 liso): SEM B-frames em H.264.
#   - Turing TU116+ (1650 Super/1660): B-frames OK em H.264 E HEVC
#     (confirmado por encode real em 2026-08-09: 44 B-frames num teste HEVC).
#   - Ampere (30xx): mesma coisa, melhor qualidade no mesmo bitrate.
#   - Ada (40xx): + AV1.
#   - Blackwell (50xx): + AV1, 4:2:2, 2 chips NVENC na maioria dos SKUs.
# A tabela e so o palpite inicial: test_bframes() confirma na marra e sobrepoe.
NVENC_GENS = [
    # (regex do nome, geracao, h264_bframes, hevc_bframes, max_sessions)
    (r"\b(50[6-9]0|5060|5070|5080|5090)\b", "Blackwell", True, True, 8),
    (r"\b(40[5-9]0|4060|4070|4080|4090)\b", "Ada", True, True, 8),
    (r"\b(30[5-9]0|3060|3070|3080|3090)\b", "Ampere", True, True, 5),
    (r"1650\s*SUPER|1660|1[67]50\s*Ti", "Turing (TU116)", True, True, 3),
    (r"\b1650\b", "Turing (TU117/Volta NVENC)", False, False, 3),
    (r"\b(20[6-8]0|2060|2070|2080)\b", "Turing (TU10x)", True, True, 3),
]


def run(cmd, timeout=25):
    """Roda comando e devolve stdout+stderr. Nunca levanta — devolve '' se falhar."""
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return (p.stdout or "") + (p.stderr or "")
    except Exception:
        return ""


def find_ffmpeg():
    """ffmpeg com NVENC: prefere o build pinado do Windows, senao o do PATH."""
    if os.path.exists(FFMPEG_WIN):
        return FFMPEG_WIN
    return shutil.which("ffmpeg") or ""


def probe_gpu():
    """nvidia-smi: nome, driver e VRAM. Sem NVIDIA devolve None."""
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
    """Casa o nome da placa com a geracao de NVENC."""
    for pattern, gen, h264_bf, hevc_bf, sessions in NVENC_GENS:
        if re.search(pattern, name, re.I):
            return {"generation": gen, "h264_bframes": h264_bf,
                    "hevc_bframes": hevc_bf, "max_sessions": sessions}
    # Placa desconhecida: assume o conservador e confia no teste empirico.
    return {"generation": "desconhecida", "h264_bframes": False,
            "hevc_bframes": False, "max_sessions": 2}


def probe_encoders(ffmpeg):
    """Quais encoders NVENC este binario de ffmpeg realmente expoe."""
    if not ffmpeg:
        return []
    out = run([ffmpeg, "-hide_banner", "-encoders"])
    return sorted(set(re.findall(r"\b(h264_nvenc|hevc_nvenc|av1_nvenc)\b", out)))


def test_bframes(ffmpeg, codec="h264"):
    """Confirma B-frames na marra: encoda 1s sintetico com -bf 3.

    A tabela por geracao e um palpite bom; este teste e a verdade. Driver
    velho ou placa fora da lista aparecem aqui.
    """
    if not ffmpeg:
        return None
    out = run([ffmpeg, "-hide_banner", "-nostdin",
               "-f", "lavfi", "-i", "testsrc=size=320x180:rate=30:duration=1",
               "-c:v", f"{codec}_nvenc", "-preset", "p5", "-bf", "3",
               "-f", "null", "-"], timeout=45)
    if not out:
        return None
    # NVENC reclama explicitamente quando a placa nao suporta B-frames.
    if re.search(r"b.?frames? (are )?not supported|InitializeEncoder failed", out, re.I):
        return False
    return bool(re.search(r"frame=\s*\d+", out))


def build_args(caps, codec="h264", quality="normal"):
    """Monta os params de encode pra placa detectada.

    quality: 'normal' (cq 22, dia-a-dia) | 'high' (cq 19, entrega final)
    """
    # Sem NVENC, ou o codec pedido nao existe nesta placa (ex.: av1 numa
    # Turing) -> cai pro CPU em vez de estourar no meio do encode.
    if not caps["nvenc_available"] or f"{codec}_nvenc" not in caps["encoders"]:
        crf = "18" if quality == "high" else "20"
        cpu_enc = {"hevc": "libx265", "av1": "libsvtav1"}.get(codec, "libx264")
        return ["-c:v", cpu_enc, "-preset", "slow", "-crf", crf,
                "-pix_fmt", "yuv420p"]

    enc = f"{codec}_nvenc"
    # p5 = equilibrio validado na 1650 Super. Placas Ampere+ aguentam p6/p7
    # com folga e rendem melhor no mesmo bitrate.
    preset = "p6" if caps["generation"] in ("Ampere", "Ada", "Blackwell") else "p5"
    cq = "19" if quality == "high" else "22"
    args = ["-c:v", enc, "-preset", preset, "-rc", "vbr", "-cq", cq, "-b:v", "0",
            "-pix_fmt", "yuv420p"]

    bf_ok = caps["hevc_bframes"] if codec == "hevc" else caps["h264_bframes"]
    if bf_ok:
        # B-frames cortam bitrate sem perder qualidade. 3 e o ponto doce.
        args += ["-bf", "3"]
    return args


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true", help="saida JSON")
    ap.add_argument("--encode-args", action="store_true",
                    help="so a linha de params pro ffmpeg")
    ap.add_argument("--codec", default="h264", choices=["h264", "hevc", "av1"],
                    help="av1 so existe em Ada/Blackwell (40xx/50xx)")
    ap.add_argument("--quality", default="normal", choices=["normal", "high"])
    ap.add_argument("--no-test", action="store_true",
                    help="pula o teste empirico de B-frames (mais rapido)")
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
                {"generation": "sem NVIDIA", "h264_bframes": False,
                 "hevc_bframes": False, "max_sessions": 0})

    # Teste empirico manda mais que a tabela — testa CADA codec disponivel,
    # nao so o pedido (senao o relatorio mostra o outro codec pela tabela).
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

    print(f"GPU .............. {caps['gpu'] or 'nenhuma NVIDIA detectada'}")
    if gpu:
        free = caps["vram_mb"] - caps["vram_used_mb"]
        print(f"Driver ........... {caps['driver']}")
        print(f"VRAM ............. {caps['vram_mb']} MB "
              f"({free} MB livres)")
        print(f"Geracao NVENC .... {caps['generation']}")
    print(f"ffmpeg ........... {caps['ffmpeg'] or 'NAO ENCONTRADO'}")
    print(f"Encoders NVENC ... {', '.join(caps['encoders']) or 'nenhum (CPU only)'}")
    print(f"B-frames H.264 ... {caps['h264_bframes']}"
          f"{' (testado)' if 'h264_bframes_measured' in caps else ''}")
    print(f"B-frames HEVC .... {caps['hevc_bframes']}")
    print(f"Encodes paralelos  max {caps['max_sessions']}")
    print()
    print("Params pro ffmpeg:")
    print("  " + " ".join(enc_args))

    # Avisos que importam na pratica.
    if gpu and caps["vram_mb"] <= 4096:
        print()
        print("AVISO: 4 GB de VRAM — rode UM whisper por vez (ver media-transcription).")
    if gpu and caps["vram_used_mb"] > 1500:
        print()
        print(f"AVISO: {caps['vram_used_mb']} MB de VRAM ja em uso (jogo aberto?) — "
              "considere CPU int8 pra transcricao.")


if __name__ == "__main__":
    sys.exit(main())
