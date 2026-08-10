#!/usr/bin/env python3
"""16:9 -> 9:16 seguindo quem fala (hard-cut pan), sem OpenCV nem ML.

Portado de `clipify` (MIT, Louise de Sadeleer) e adaptado pro fluxo WSL daqui.
Alternativa ao fundo desfocado da SKILL.md: em vez de encolher o video no meio
do quadro, ENQUADRA o rosto de quem esta falando em tela cheia 1080x1920.

Como funciona (a sacada do clipify): nao detecta rosto. Mede o BRILHO MEDIO
(signalstats.YAVG) de duas ROIs — a boca/queixo de cada pessoa — quadro a
quadro. Quem esta falando mexe mais, entao a ROI dele varia mais. Suaviza,
aplica histerese e sai uma timeline de quem fala quando. Camera estatica
dentro do corte e premissa (verdadeiro em entrevista/podcast).

Uso tipico (2 passos):

  # 1) descobre as ROIs: extrai um frame e VOCE olha (regra 4/5 da SKILL.md)
  python face_pan.py probe --video IN.mp4 --at 5

  # 2) gera a timeline + o filtro ffmpeg
  python face_pan.py build --video IN.mp4 \
      --left  100,300,500,400 \
      --right 1300,300,500,400 \
      --out-filter /tmp/pan.txt

Depois queime junto com a legenda (uma geracao de encode a menos).

Requer: ffmpeg (usa o do WSL por padrao — e so filtro/analise, CPU serve).
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys

FFMPEG_WIN = r"C:\Users\ferna\Tools\ffmpeg71\ffmpeg-n7.1-latest-win64-gpl-7.1\bin\ffmpeg.exe"


def ffmpeg_bin():
    return shutil.which("ffmpeg") or (FFMPEG_WIN if os.path.exists(FFMPEG_WIN) else "ffmpeg")


def run(cmd, timeout=900):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def parse_roi(s, label):
    """'x,y,w,h' -> (x,y,w,h). Erro claro em vez de stacktrace."""
    try:
        x, y, w, h = (int(v) for v in s.split(","))
    except Exception:
        sys.exit(f"ERRO: --{label} precisa ser 'x,y,w,h' em pixels. Recebi: {s!r}")
    if w <= 0 or h <= 0:
        sys.exit(f"ERRO: --{label} com largura/altura <= 0.")
    return x, y, w, h


def probe_frame(video, at, out_jpg, left=None, right=None):
    """Extrai 1 frame (com as ROIs desenhadas, se dadas) pra inspecao visual."""
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
        sys.exit(f"ERRO ao extrair frame:\n{p.stderr[:500]}")
    return out_jpg


def video_info(video):
    """fps, largura, altura e duracao via ffprobe."""
    probe = shutil.which("ffprobe") or "ffprobe"
    p = run([probe, "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height,r_frame_rate,duration",
             "-show_entries", "format=duration", "-of", "json", video])
    if p.returncode != 0:
        sys.exit(f"ERRO no ffprobe:\n{p.stderr[:300]}")
    data = json.loads(p.stdout)
    st = data["streams"][0]
    num, _, den = st["r_frame_rate"].partition("/")
    fps = float(num) / float(den or 1)
    dur = float(st.get("duration") or data.get("format", {}).get("duration") or 0)
    return {"fps": fps, "w": int(st["width"]), "h": int(st["height"]), "dur": dur}


def measure_roi(video, roi, tag, workdir):
    """YAVG (brilho medio) da ROI, quadro a quadro, pro arquivo de log."""
    ff = ffmpeg_bin()
    x, y, w, h = roi
    out = os.path.join(workdir, f"motion_{tag}.txt")
    # O parser de filtro do ffmpeg trata ':' e '\' como sintaxe. Em path do
    # Windows ("C:\...") isso quebra o filtro — escapar antes de interpolar.
    esc = out.replace("\\", "/").replace(":", r"\:")
    # crop na ROI -> signalstats -> metadata:print despeja YAVG por frame.
    vf = f"crop={w}:{h}:{x}:{y},signalstats,metadata=print:file='{esc}'"
    p = run([ff, "-nostdin", "-y", "-i", video, "-vf", vf, "-an",
             "-f", "null", "-"])
    if p.returncode != 0 or not os.path.exists(out):
        sys.exit(f"ERRO ao medir ROI {tag} (arquivo={out}):\n"
                 f"{(p.stderr or '')[-800:]}")
    return out


def parse_motion(path):
    """Le o log do metadata=print -> (tempos, valores de YAVG)."""
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
    """Variacao quadro a quadro. Falar mexe a boca -> YAVG oscila mais.

    O clipify original compara YAVG direto, o que mistura brilho de cena com
    movimento. Usar |delta| isola o movimento e aguenta melhor iluminacao
    diferente entre os dois lados do quadro.
    """
    return [0.0] + [abs(vals[i] - vals[i - 1]) for i in range(1, len(vals))]


def smooth(v, win=15):
    """Media movel — tira o tremor de compressao."""
    out = []
    for i in range(len(v)):
        a, b = max(0, i - win // 2), min(len(v), i + win // 2 + 1)
        out.append(sum(v[a:b]) / (b - a))
    return out


def normalize(v):
    m = sum(v) / max(len(v), 1)
    return [x / m if m > 0 else 0.0 for x in v]


def speaker_timeline(t_l, v_l, v_d, fps, min_dur=1.0, margin=1.15):
    """Quem fala em cada frame -> segmentos [start, end, speaker].

    Histerese (margin): so troca de falante quando o outro passa 15% do atual.
    Sem isso o corte pisca em silencio, que e o defeito classico do metodo.
    min_dur descarta troca curta demais pra ler na tela.
    """
    n = min(len(v_l), len(v_d))
    if n == 0:
        sys.exit("ERRO: nenhuma amostra de movimento — confira as ROIs.")
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

    # Agrupa frames consecutivos do mesmo falante.
    segs, start, cur = [], 0, speaker[0]
    for i in range(1, n):
        if speaker[i] != cur:
            segs.append([start / fps, i / fps, cur])
            start, cur = i, speaker[i]
    segs.append([start / fps, n / fps, cur])

    # Absorve segmentos curtos no vizinho (evita corte epiletico).
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
    """Expressao de crop com hard cut entre os dois enquadramentos.

    A janela de crop tem a ALTURA do fonte e largura = altura*9/16, centrada
    horizontalmente no rosto do falante. So o X muda no tempo -> uma expressao
    condicional aninhada resolve, sem re-encode por segmento.
    """
    src_w, src_h = info["w"], info["h"]
    crop_w = int(src_h * target_w / target_h)  # 9:16 dentro da altura do fonte
    crop_w -= crop_w % 2
    if crop_w > src_w:
        sys.exit(f"ERRO: fonte {src_w}x{src_h} ja e mais estreito que 9:16.")

    def center_x(roi):
        cx = roi[0] + roi[2] // 2
        x = cx - crop_w // 2
        return max(0, min(x, src_w - crop_w))  # nao deixa sair do quadro

    x_l, x_r = center_x(left), center_x(right)

    # if(lt(t,T1), X1, if(lt(t,T2), X2, ...)) — hard cut, sem interpolacao.
    expr = str(x_r if segs[-1][2] else x_l)
    for start, end, spk in reversed(segs[:-1]):
        expr = f"if(lt(t,{end:.3f}),{x_r if spk else x_l},{expr})"

    return (f"crop=w={crop_w}:h={src_h}:x='{expr}':y=0,"
            f"scale={target_w}:{target_h},setsar=1"), crop_w


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("probe", help="extrai frame p/ voce achar as ROIs")
    p1.add_argument("--video", required=True)
    p1.add_argument("--at", default="5", help="segundo do frame (default 5)")
    p1.add_argument("--out", default="/tmp/facepan_probe.jpg")
    p1.add_argument("--left", help="x,y,w,h — se dado, desenha a caixa")
    p1.add_argument("--right", help="x,y,w,h — se dado, desenha a caixa")

    p2 = sub.add_parser("build", help="mede, gera timeline e filtro")
    p2.add_argument("--video", required=True)
    p2.add_argument("--left", required=True, help="ROI boca/queixo esquerda: x,y,w,h")
    p2.add_argument("--right", required=True, help="ROI boca/queixo direita: x,y,w,h")
    p2.add_argument("--min-dur", type=float, default=1.0)
    p2.add_argument("--margin", type=float, default=1.15)
    p2.add_argument("--workdir", default="/tmp/facepan")
    p2.add_argument("--out-filter", help="grava a filter chain neste arquivo")
    p2.add_argument("--json", action="store_true", help="imprime a timeline em JSON")

    a = ap.parse_args()

    if a.cmd == "probe":
        left = parse_roi(a.left, "left") if a.left else None
        right = parse_roi(a.right, "right") if a.right else None
        out = probe_frame(a.video, a.at, a.out, left, right)
        info = video_info(a.video)
        print(f"Fonte: {info['w']}x{info['h']} @ {info['fps']:.2f}fps, {info['dur']:.1f}s")
        print(f"Frame: {out}")
        print()
        print("Abra o .jpg (Read) e anote x,y,w,h da BOCA+QUEIXO de cada pessoa.")
        print("Evite maos e microfone. Depois rode 'build' com --left/--right.")
        return

    left, right = parse_roi(a.left, "left"), parse_roi(a.right, "right")
    os.makedirs(a.workdir, exist_ok=True)
    info = video_info(a.video)

    print(f"Fonte: {info['w']}x{info['h']} @ {info['fps']:.2f}fps", file=sys.stderr)
    print("Medindo ROI esquerda...", file=sys.stderr)
    f_l = measure_roi(a.video, left, "left", a.workdir)
    print("Medindo ROI direita...", file=sys.stderr)
    f_r = measure_roi(a.video, right, "right", a.workdir)

    _, v_l = parse_motion(f_l)
    _, v_r = parse_motion(f_r)
    segs = speaker_timeline(None, v_l, v_r, info["fps"], a.min_dur, a.margin)

    vf, crop_w = build_filter(segs, info, left, right)

    n_l = sum(1 for s in segs if s[2] == 0)
    print(f"{len(segs)} segmentos ({n_l} esquerda, {len(segs)-n_l} direita), "
          f"janela de crop {crop_w}px", file=sys.stderr)

    if a.json:
        print(json.dumps({"segments": segs, "filter": vf, "crop_w": crop_w},
                         indent=2))
    if a.out_filter:
        with open(a.out_filter, "w", encoding="utf-8") as f:
            f.write(vf)
        print(f"Filtro em: {a.out_filter}", file=sys.stderr)
    if not a.json and not a.out_filter:
        print(vf)


if __name__ == "__main__":
    sys.exit(main())
