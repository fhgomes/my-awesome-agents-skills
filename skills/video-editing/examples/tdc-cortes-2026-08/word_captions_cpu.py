# -*- coding: utf-8 -*-
"""Variante CPU do word_captions.py da skill video-editing (GPU ocupada por jogo).

Diferenças vs. original:
- device=cpu int8 (escolha consciente: LoL usando a GTX 1650; 70s de audio)
- dump de -words.json (palavras cruas p/ planejar pontos de corte)
- --segments "a-b,c-d": remapeia palavras do timeline ORIGINAL p/ o timeline
  do corte concatenado (transcreve 1x o original, deriva legendas do corte
  sem re-transcrever a emenda — evita alucinacao de fronteira e cold open
  engolido, ver receita 5 da skill).
"""
import argparse
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")


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
    ap.add_argument("--words-json", default=None,
                    help="pula a transcricao e usa este JSON de palavras")
    ap.add_argument("--segments", default=None,
                    help='ex.: "41.52-47.50,25.20-56.00" — remapeia p/ timeline do corte')
    args = ap.parse_args()

    if args.words_json:
        with open(args.words_json, encoding="utf-8") as jf:
            words = json.load(jf)
        print(f"[words] {len(words)} palavras de {args.words_json}", flush=True)
    else:
        from faster_whisper import WhisperModel
        t0 = time.perf_counter()
        model = WhisperModel("large-v3", device="cpu", compute_type="int8",
                             cpu_threads=max(4, os.cpu_count() or 4))
        print(f"[load] large-v3 cpu int8 em {time.perf_counter() - t0:.1f}s", flush=True)
        t1 = time.perf_counter()
        seg_iter, info = model.transcribe(
            args.video, language=args.language, vad_filter=True,
            beam_size=args.beam, initial_prompt=args.prompt, word_timestamps=True)
        print(f"[audio] {info.duration:.1f}s", flush=True)
        words = []
        for seg in seg_iter:
            for w in seg.words or []:
                words.append({"start": round(w.start, 3), "end": round(w.end, 3),
                              "word": w.word})
        took = time.perf_counter() - t1
        print(f"[done] {took:.1f}s | {len(words)} palavras | "
              f"{info.duration / took:.2f}x tempo real", flush=True)
        jpath = os.path.join(args.out_dir, f"{args.base}-words.json")
        with open(jpath, "w", encoding="utf-8") as jf:
            json.dump(words, jf, ensure_ascii=False, indent=1)
        print(f"[out] {jpath}", flush=True)

    if args.segments:
        segs = []
        for part in args.segments.split(","):
            a, b = part.split("-")
            segs.append((float(a), float(b)))
        mapped = []
        offset = 0.0
        for a, b in segs:
            for w in words:
                mid = (w["start"] + w["end"]) / 2
                if a <= mid < b:
                    mapped.append({"start": round(max(0.0, w["start"] - a) + offset, 3),
                                   "end": round(min(b - a, w["end"] - a) + offset, 3),
                                   "word": w["word"]})
            offset += b - a
        words = mapped
        print(f"[segments] {len(segs)} trechos -> {len(words)} palavras, "
              f"timeline {offset:.2f}s", flush=True)

    if not words:
        print("[fatal] nenhuma palavra", flush=True)
        sys.exit(2)

    blocks = group_words(words, args.max_words, args.max_dur)
    if not args.no_upper:
        blocks = [(s, e, t.upper()) for s, e, t in blocks]
    print(f"[blocks] {len(blocks)} blocos", flush=True)

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
