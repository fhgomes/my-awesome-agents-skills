#!/usr/bin/env python3
"""
pepper_avatar_build.py — transforma o acervo de referencias da Pepper em humores de avatar.

Faz, nesta ordem:
  1. baixa do Drive as imagens da pasta do lote (as que faltarem) para avatars/src/<lote>/
  2. acha o rosto de cada uma (Haar cascade) e grava as caixas em avatars/faces_<lote>.json
  3. recorta 512x512 centrado no rosto para avatars/crop/<slug>.png
  4. regenera avatars/moods.json cruzando com a reference-library (papeis, reference_id, ficha)

O recorte varia com o enquadramento (ZOOM): avatar nativo entra inteiro, meio-corpo mostra o
tronco (4.5 alturas de rosto), corpo inteiro vai ate a cintura (4.0). Nao e pra ser sempre close —
variacao de distancia e o que faz o rodizio parecer vivo. Ajuste fino por imagem no faces_<lote>.json.

A deteccao precisa de OpenCV 4.x, que NAO esta instalado no host. Rode com um python de venv:
    python3 -m venv /tmp/cvenv && /tmp/cvenv/bin/pip install "opencv-python-headless<5"
    ./pepper_avatar_build.py --lote v7 --folder <drive_folder_id> --cv-python /tmp/cvenv/bin/python

Sem --cv-python o passo 2 e pulado: ele reaproveita faces_<lote>.json. Rosto que o cascade nao
achar (ou achar errado) entra a mao no faces_<lote>.json, em % da largura/altura:
    "arquivo.png": {"centro_x_pct": 45.0, "centro_y_pct": 8.4, "altura_rosto_pct": 9.0,
                    "fonte": "conferido a mao"}
Depois de recortar, CONFIRA — gere a folha de contato com --contato e olhe. Rosto fora do circulo
e o unico erro que o usuario ve.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request

sys.path.insert(0, "/home/unando/.openclaw/workspace")
import google_api as G  # noqa: E402

BASE = "/home/unando/.openclaw/workspaces/pepper/avatars"
LIB = "/home/unando/.openclaw/workspaces/pepper/reference-library/pepper_reference_library.json"
SAIDA = 512
# Zoom padrao por enquadramento: (lado do quadrado em alturas de rosto, onde o centro do rosto cai).
# Nem toda bolinha de perfil precisa ser close: o avatar nativo entra inteiro, o meio-corpo mostra
# tronco, o corpo inteiro vai ate a cintura. Sobrescreva por imagem no faces_<lote>.json com
# "lado_em_rostos", "rosto_y" ou "recorte": "inteiro".
ZOOM = {
    "avatar": None,               # ja e quadrado e composto como avatar: usa a imagem inteira
    "meio-corpo": (4.5, 0.36),
    "corpo-inteiro": (4.0, 0.38),
}
ZOOM_PADRAO = (4.0, 0.38)

# tag/colecao -> papel. O papel e o que o sorteio do pepper_avatar.py consulta.
PAPEIS = {
    "foco": {"tablet", "notebook_or_planner", "whiteboard_briefing", "teaching_or_explaining",
             "desk_leaning_pose", "phone", "pen_or_stationery_gesture", "adjusting_glasses"},
    "cozy": {"coffee_mug", "sofa_or_lounge_seating", "cozy_lounge_editorial", "window_side"},
    "moleca": {"playful_moleca", "wink_or_tongue_out", "anime_editorial", "dreamy_or_encantada",
               "knowing_smile"},
    "evento": {"event_ready", "one_shoulder_dresses", "metallic_heels", "fashion_forward_black",
               "edgy_or_fashion_forward"},
    "bronca": {"stern_or_mock_scolding", "raised_index_finger"},
}


def baixar(folder_id, destino):
    os.makedirs(destino, exist_ok=True)
    tok = G.get_access_token()
    q = urllib.parse.quote(f"'{folder_id}' in parents and trashed=false")
    arquivos, page = [], None
    while True:
        url = (f"https://www.googleapis.com/drive/v3/files?q={q}"
               "&fields=nextPageToken,files(id,name,size)&pageSize=200")
        if page:
            url += "&pageToken=" + page
        r = G.api_request(url)
        arquivos += r.get("files", [])
        page = r.get("nextPageToken")
        if not page:
            break
    novos = 0
    for f in arquivos:
        if not f["name"].lower().endswith(".png"):
            continue
        alvo = os.path.join(destino, f["name"])
        if os.path.exists(alvo) and os.path.getsize(alvo) == int(f.get("size", 0)):
            continue
        req = urllib.request.Request(
            f"https://www.googleapis.com/drive/v3/files/{f['id']}?alt=media",
            headers={"Authorization": f"Bearer {tok}"})
        with urllib.request.urlopen(req, timeout=180) as resp, open(alvo, "wb") as out:
            out.write(resp.read())
        novos += 1
    print(f"[drive] {len(arquivos)} arquivos na pasta, {novos} baixados agora")


DETECTA = r'''
import cv2, glob, json, os, sys
src, saida = sys.argv[1], sys.argv[2]
faces = [cv2.CascadeClassifier(cv2.data.haarcascades + f) for f in
         ("haarcascade_frontalface_default.xml", "haarcascade_frontalface_alt2.xml",
          "haarcascade_frontalface_alt.xml")]
olhos = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_eye_tree_eyeglasses.xml")
out = {}
for p in sorted(glob.glob(os.path.join(src, "*.png"))):
    img = cv2.imread(p); H, W = img.shape[:2]
    big = cv2.resize(img[:int(H*0.45), :], None, fx=3, fy=3)
    g = cv2.equalizeHist(cv2.cvtColor(big, cv2.COLOR_BGR2GRAY))
    melhor = None
    for c in faces:
        for (x, y, w, h) in c.detectMultiScale(g, 1.05, 5, minSize=(80, 80)):
            # olhos dentro da caixa: derruba quadro na parede, planta, almofada
            if len(olhos.detectMultiScale(g[y:y+h, x:x+w], 1.05, 4,
                                          minSize=(int(w*0.1), int(h*0.1)))) < 1:
                continue
            cand = (w*h, (x/3+w/6)/W*100, (y/3+h/6)/H*100, (h/3)/H*100)
            if melhor is None or cand[0] > melhor[0]:
                melhor = cand
    out[os.path.basename(p)] = None if melhor is None else {
        "centro_x_pct": round(melhor[1], 2), "centro_y_pct": round(melhor[2], 2),
        "altura_rosto_pct": round(melhor[3], 2), "fonte": "haar cascade"}
json.dump(out, open(saida, "w"), indent=1)
print("[rosto] achados:", sum(1 for v in out.values() if v), "de", len(out))
print("[rosto] SEM rosto (resolva a mao):", [k for k, v in out.items() if not v])
'''


def detectar(cv_python, src, arquivo_faces):
    anterior = {}
    if os.path.exists(arquivo_faces):
        anterior = json.load(open(arquivo_faces)).get("rostos", {})
    tmp = arquivo_faces + ".novo"
    subprocess.run([cv_python, "-c", DETECTA, src, tmp], check=True)
    novos = json.load(open(tmp))
    os.remove(tmp)
    # o que foi conferido a mao manda sobre o cascade
    for k, v in anterior.items():
        if v and v.get("fonte") == "conferido a mao":
            novos[k] = v
    json.dump({"_meta": {"uso": "recorte quadrado, rosto a 42% do topo, lado = 3x a altura do rosto"},
               "rostos": novos}, open(arquivo_faces, "w"), ensure_ascii=False, indent=1)


def enquadramento_de(nome):
    return ("avatar" if "-avatar-" in nome else
            "meio-corpo" if "-meio-corpo-" in nome else "corpo-inteiro")


def slug_de(nome):
    s = re.sub(r"^pepper_ref_\d{3}-(?:avatar|meio-corpo|corpo-inteiro)-", "", nome)
    return re.sub(r"_v\d+\.png$", "", s)


def recortar(src, arquivo_faces):
    from PIL import Image
    rostos = json.load(open(arquivo_faces))["rostos"]
    os.makedirs(os.path.join(BASE, "crop"), exist_ok=True)
    feitos, pulados = 0, []
    for nome in sorted(os.listdir(src)):
        if not nome.endswith(".png"):
            continue
        im = Image.open(os.path.join(src, nome)).convert("RGB")
        W, H = im.size
        r = rostos.get(nome) or {}
        zoom = ZOOM.get(enquadramento_de(nome), ZOOM_PADRAO)
        inteiro = r.get("recorte") == "inteiro" or (zoom is None and W == H)
        if inteiro:
            caixa = (0, 0, W, H) if W == H else None
        elif not r.get("altura_rosto_pct"):
            pulados.append(nome)
            continue
        else:
            lado_rostos, rosto_y = zoom or ZOOM_PADRAO
            lado_rostos = r.get("lado_em_rostos", lado_rostos)
            rosto_y = r.get("rosto_y", rosto_y)
            cx, cy = W * r["centro_x_pct"] / 100, H * r["centro_y_pct"] / 100
            lado = min(lado_rostos * H * r["altura_rosto_pct"] / 100, W, H)
            left = max(0, min(cx - lado / 2, W - lado))
            top = max(0, min(cy - lado * rosto_y, H - lado))
            caixa = (int(left), int(top), int(left + lado), int(top + lado))
        if caixa is None:
            pulados.append(nome)
            continue
        (im.crop(caixa).resize((SAIDA, SAIDA), Image.LANCZOS)
           .save(os.path.join(BASE, "crop", slug_de(nome) + ".png")))
        feitos += 1
    print(f"[recorte] {feitos} recortados", f"| pulados: {pulados}" if pulados else "")


def manifesto(src, lote):
    lib = json.load(open(LIB))
    ent = {e["reference_id"]: e for e in lib["entries"]}
    cols = lib["collections"]
    antigo = {}
    if os.path.exists(os.path.join(BASE, "moods.json")):
        antigo = json.load(open(os.path.join(BASE, "moods.json"))).get("humores", {})

    novo = {}
    for nome in sorted(os.listdir(src)):
        m = re.match(r"(pepper_ref_\d{3})", nome)
        if not m or not nome.endswith(".png"):
            continue
        rid = m.group(1)
        slug = slug_de(nome)
        if not os.path.exists(os.path.join(BASE, "crop", slug + ".png")):
            continue
        e = ent.get(rid, {})
        c = {k for k, v in cols.items() if rid in v}
        t = set(e.get("category_tags", []))
        papeis = [p for p, sinais in PAPEIS.items()
                  if (t | c) & sinais and (p != "foco" or "glasses" in t or "adjusting_glasses" in c)]
        if "whiteboard_briefing" in c or any("whiteboard" in x for x in t):
            papeis.append("briefing")
        if "avatars_and_profile_crops" in c:
            papeis.append("perfil")
        novo[slug] = {"arquivo": slug + ".png", "reference_id": rid,
                      "nome": e.get("reference_name"), "quando_usar": e.get("quick_use_note"),
                      "enquadramento": enquadramento_de(nome),
                      "papeis": sorted(set(papeis)) or ["geral"], "colecoes": sorted(c),
                      "drive_url": e.get("drive_url"), "origem": f"canonicas {lote}"}
    # preserva humores de lotes anteriores cujo arquivo ainda existe (inclui os legados v5)
    for slug, ficha in antigo.items():
        if slug not in novo and os.path.exists(os.path.join(BASE, "crop", ficha["arquivo"])):
            novo[slug] = ficha
    json.dump({"_meta": {"total": len(novo), "lote": lote,
                         "fonte": "reference-library + avatars/src/" + lote,
                         "recorte": f"quadrado {SAIDA}x{SAIDA}; zoom por enquadramento {ZOOM}"},
               "humores": novo}, open(os.path.join(BASE, "moods.json"), "w"),
              ensure_ascii=False, indent=2)
    print(f"[manifesto] {len(novo)} humores em {BASE}/moods.json")


def contato(destino):
    """Folha de contato dos recortes, em circulo, do jeito que o Discord mostra."""
    from PIL import Image, ImageDraw
    crops = sorted(os.listdir(os.path.join(BASE, "crop")))
    T, COLS = 150, 7
    linhas = (len(crops) + COLS - 1) // COLS
    sh = Image.new("RGB", (COLS * T, linhas * (T + 14)), "white")
    d = ImageDraw.Draw(sh)
    for i, q in enumerate(crops):
        th = Image.open(os.path.join(BASE, "crop", q)).resize((T, T))
        m = Image.new("L", (T, T), 0)
        ImageDraw.Draw(m).ellipse((0, 0, T, T), fill=255)
        b = Image.new("RGB", (T, T), (235, 235, 235))
        b.paste(th, (0, 0), m)
        x, y = (i % COLS) * T, (i // COLS) * (T + 14)
        sh.paste(b, (x, y))
        d.text((x + 3, y + T + 1), q[:20], fill="black")
    sh.save(destino)
    print(f"[contato] {destino} — olhe antes de dar por pronto")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lote", default="v6", help="nome do lote (vira avatars/src/<lote>/)")
    ap.add_argument("--folder", help="id da pasta no Drive; sem isso, nao baixa nada")
    ap.add_argument("--cv-python", help="python de um venv com opencv-python-headless<5")
    ap.add_argument("--contato", metavar="ARQUIVO.png", help="gera a folha de contato e sai")
    a = ap.parse_args()

    src = os.path.join(BASE, "src", a.lote)
    faces = os.path.join(BASE, f"faces_{a.lote}.json")

    if a.contato:
        contato(a.contato)
        return
    if a.folder:
        baixar(a.folder, src)
    if not os.path.isdir(src):
        sys.exit(f"nao achei {src} — passe --folder para baixar o lote")
    if a.cv_python:
        detectar(a.cv_python, src, faces)
    elif not os.path.exists(faces):
        sys.exit(f"sem {faces} e sem --cv-python: nao tenho como achar os rostos")
    recortar(src, faces)
    manifesto(src, a.lote)


if __name__ == "__main__":
    main()
