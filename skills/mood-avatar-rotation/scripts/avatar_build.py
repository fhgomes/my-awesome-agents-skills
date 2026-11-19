#!/usr/bin/env python3
"""
avatar_build.py — turn a character's reference library into avatar moods.

In this order:
  1. downloads the batch folder's images from Google Drive (only missing ones) into
     <base>/src/<batch>/
  2. finds the face in each one (Haar cascade) and writes the boxes to <base>/faces_<batch>.json
  3. crops 512x512 around the face into <base>/crop/<slug>.png
  4. regenerates <base>/moods.json by joining with the reference library (roles, reference_id,
     entry metadata)

The crop varies with the framing (ZOOM): a native avatar goes in whole, half-body shows the torso
(4.5 face heights), full-body goes down to the waist (4.0). It is not meant to be always a close-up
— variation in distance is what makes the rotation feel alive. Fine-tune per image in
faces_<batch>.json.

Detection needs OpenCV 4.x. If the host does not have it, run it from a throwaway venv:
    python3 -m venv /tmp/cvenv && /tmp/cvenv/bin/pip install "opencv-python-headless<5"
    ./avatar_build.py --base path/to/avatars --library path/to/reference-library.json \\
        --batch v7 --folder <drive_folder_id> --cv-python /tmp/cvenv/bin/python

Without --cv-python step 2 is skipped and faces_<batch>.json is reused. A face the cascade does not
find (or finds wrong) is entered by hand in faces_<batch>.json, as % of width/height:
    "file.png": {"center_x_pct": 45.0, "center_y_pct": 8.4, "face_height_pct": 9.0,
                 "source": "hand-checked"}
After cropping, CHECK — generate the contact sheet with --contact-sheet and look at it. A face
outside the circle is the only error the user sees.

Configuration (CLI flag or environment variable):
  --base       / AVATAR_BASE         avatars directory (default: ./avatars)
  --library    / AVATAR_LIBRARY      reference-library JSON (entries + collections)
  --ref-pattern / AVATAR_REF_PATTERN regex for the reference_id at the start of each filename
  GOOGLE_DRIVE_TOKEN                 OAuth access token with Drive read scope (only for --folder),
                                     e.g. from `gcloud auth print-access-token`

Requires Pillow for cropping and the contact sheet.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request

OUTPUT_SIZE = 512
# Default zoom per framing: (square side in face heights, where the face center falls from the top).
# Not every profile bubble needs to be a close-up: the native avatar goes in whole, half-body shows
# the torso, full-body goes down to the waist. Override per image in faces_<batch>.json with
# "side_in_faces", "face_y" or "crop": "full".
ZOOM = {
    "avatar": None,               # already square and composed as an avatar: use the whole image
    "half-body": (4.5, 0.36),
    "full-body": (4.0, 0.38),
}
DEFAULT_ZOOM = (4.0, 0.38)

# tag/collection -> role. The role is what the rotation script's draw consults.
# These are example signals; adapt them to the tag vocabulary of your own library.
ROLES = {
    "focus": {"tablet", "notebook_or_planner", "whiteboard_briefing", "teaching_or_explaining",
              "desk_leaning_pose", "phone", "pen_or_stationery_gesture", "adjusting_glasses"},
    "cozy": {"coffee_mug", "sofa_or_lounge_seating", "cozy_lounge_editorial", "window_side"},
    "playful": {"playful", "wink_or_tongue_out", "anime_editorial", "dreamy_or_enchanted",
                "knowing_smile"},
    "event": {"event_ready", "one_shoulder_dresses", "metallic_heels", "fashion_forward_black",
              "edgy_or_fashion_forward"},
    "scolding": {"stern_or_mock_scolding", "raised_index_finger"},
}

BASE = os.environ.get("AVATAR_BASE", "avatars")
LIBRARY = os.environ.get("AVATAR_LIBRARY", "")
REF_PATTERN = os.environ.get("AVATAR_REF_PATTERN", r"(?:[A-Za-z0-9]+_)?ref_\d{3}")


def drive_request(url, token):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def download(folder_id, dest):
    token = os.environ.get("GOOGLE_DRIVE_TOKEN")
    if not token:
        sys.exit("GOOGLE_DRIVE_TOKEN is not set — export an OAuth access token with Drive read "
                 "scope, or drop --folder and put the PNGs in the batch folder yourself")
    os.makedirs(dest, exist_ok=True)
    q = urllib.parse.quote(f"'{folder_id}' in parents and trashed=false")
    files, page = [], None
    while True:
        url = (f"https://www.googleapis.com/drive/v3/files?q={q}"
               "&fields=nextPageToken,files(id,name,size)&pageSize=200")
        if page:
            url += "&pageToken=" + page
        r = drive_request(url, token)
        files += r.get("files", [])
        page = r.get("nextPageToken")
        if not page:
            break
    new = 0
    for f in files:
        if not f["name"].lower().endswith(".png"):
            continue
        target = os.path.join(dest, f["name"])
        if os.path.exists(target) and os.path.getsize(target) == int(f.get("size", 0)):
            continue
        req = urllib.request.Request(
            f"https://www.googleapis.com/drive/v3/files/{f['id']}?alt=media",
            headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req, timeout=180) as resp, open(target, "wb") as out:
            out.write(resp.read())
        new += 1
    print(f"[drive] {len(files)} files in the folder, {new} downloaded now")


DETECT = r'''
import cv2, glob, json, os, sys
src, output = sys.argv[1], sys.argv[2]
faces = [cv2.CascadeClassifier(cv2.data.haarcascades + f) for f in
         ("haarcascade_frontalface_default.xml", "haarcascade_frontalface_alt2.xml",
          "haarcascade_frontalface_alt.xml")]
eyes = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_eye_tree_eyeglasses.xml")
out = {}
for p in sorted(glob.glob(os.path.join(src, "*.png"))):
    img = cv2.imread(p); H, W = img.shape[:2]
    big = cv2.resize(img[:int(H*0.45), :], None, fx=3, fy=3)
    g = cv2.equalizeHist(cv2.cvtColor(big, cv2.COLOR_BGR2GRAY))
    best = None
    for c in faces:
        for (x, y, w, h) in c.detectMultiScale(g, 1.05, 5, minSize=(80, 80)):
            # eyes inside the box: rejects wall frames, plants, cushions
            if len(eyes.detectMultiScale(g[y:y+h, x:x+w], 1.05, 4,
                                         minSize=(int(w*0.1), int(h*0.1)))) < 1:
                continue
            cand = (w*h, (x/3+w/6)/W*100, (y/3+h/6)/H*100, (h/3)/H*100)
            if best is None or cand[0] > best[0]:
                best = cand
    out[os.path.basename(p)] = None if best is None else {
        "center_x_pct": round(best[1], 2), "center_y_pct": round(best[2], 2),
        "face_height_pct": round(best[3], 2), "source": "haar cascade"}
json.dump(out, open(output, "w"), indent=1)
print("[face] found:", sum(1 for v in out.values() if v), "of", len(out))
print("[face] NO face (resolve by hand):", [k for k, v in out.items() if not v])
'''


def detect(cv_python, src, faces_file):
    previous = {}
    if os.path.exists(faces_file):
        previous = json.load(open(faces_file)).get("faces", {})
    tmp = faces_file + ".new"
    subprocess.run([cv_python, "-c", DETECT, src, tmp], check=True)
    new = json.load(open(tmp))
    os.remove(tmp)
    # what was checked by hand wins over the cascade
    for k, v in previous.items():
        if v and v.get("source") == "hand-checked":
            new[k] = v
    json.dump({"_meta": {"usage": "square crop around the face; zoom per framing (see ZOOM in "
                                  "avatar_build.py), per-image overrides: side_in_faces, face_y, "
                                  "crop=full"},
               "faces": new}, open(faces_file, "w"), ensure_ascii=False, indent=1)


def framing_of(name):
    return ("avatar" if "-avatar-" in name else
            "half-body" if "-half-body-" in name else "full-body")


def slug_of(name):
    s = re.sub(rf"^{REF_PATTERN}-(?:avatar|half-body|full-body)-", "", name)
    return re.sub(r"_v\d+\.png$", "", s)


def crop(src, faces_file):
    from PIL import Image
    faces = json.load(open(faces_file))["faces"]
    os.makedirs(os.path.join(BASE, "crop"), exist_ok=True)
    done, skipped = 0, []
    for name in sorted(os.listdir(src)):
        if not name.endswith(".png"):
            continue
        im = Image.open(os.path.join(src, name)).convert("RGB")
        W, H = im.size
        r = faces.get(name) or {}
        zoom = ZOOM.get(framing_of(name), DEFAULT_ZOOM)
        whole = r.get("crop") == "full" or (zoom is None and W == H)
        if whole:
            box = (0, 0, W, H) if W == H else None
        elif not r.get("face_height_pct"):
            skipped.append(name)
            continue
        else:
            side_faces, face_y = zoom or DEFAULT_ZOOM
            side_faces = r.get("side_in_faces", side_faces)
            face_y = r.get("face_y", face_y)
            cx, cy = W * r["center_x_pct"] / 100, H * r["center_y_pct"] / 100
            side = min(side_faces * H * r["face_height_pct"] / 100, W, H)
            left = max(0, min(cx - side / 2, W - side))
            top = max(0, min(cy - side * face_y, H - side))
            box = (int(left), int(top), int(left + side), int(top + side))
        if box is None:
            skipped.append(name)
            continue
        (im.crop(box).resize((OUTPUT_SIZE, OUTPUT_SIZE), Image.LANCZOS)
           .save(os.path.join(BASE, "crop", slug_of(name) + ".png")))
        done += 1
    print(f"[crop] {done} cropped", f"| skipped: {skipped}" if skipped else "")


def manifest(src, batch):
    if not LIBRARY:
        sys.exit("no reference library — pass --library path/to/reference-library.json "
                 "or set AVATAR_LIBRARY")
    lib = json.load(open(LIBRARY))
    entries = {e["reference_id"]: e for e in lib["entries"]}
    cols = lib["collections"]
    old = {}
    if os.path.exists(os.path.join(BASE, "moods.json")):
        old = json.load(open(os.path.join(BASE, "moods.json"))).get("moods", {})

    new = {}
    for name in sorted(os.listdir(src)):
        m = re.match(rf"({REF_PATTERN})", name)
        if not m or not name.endswith(".png"):
            continue
        rid = m.group(1)
        slug = slug_of(name)
        if not os.path.exists(os.path.join(BASE, "crop", slug + ".png")):
            continue
        e = entries.get(rid, {})
        c = {k for k, v in cols.items() if rid in v}
        t = set(e.get("category_tags", []))
        roles = [p for p, signals in ROLES.items()
                 if (t | c) & signals and (p != "focus" or "glasses" in t or "adjusting_glasses" in c)]
        if "whiteboard_briefing" in c or any("whiteboard" in x for x in t):
            roles.append("briefing")
        if "avatars_and_profile_crops" in c:
            roles.append("profile")
        new[slug] = {"file": slug + ".png", "reference_id": rid,
                     "name": e.get("reference_name"), "when_to_use": e.get("quick_use_note"),
                     "framing": framing_of(name),
                     "roles": sorted(set(roles)) or ["general"], "collections": sorted(c),
                     "drive_url": e.get("drive_url"), "origin": f"canonicals {batch}"}
    # keep moods from earlier batches whose file still exists (including hand-made legacy crops)
    for slug, entry in old.items():
        if slug not in new and os.path.exists(os.path.join(BASE, "crop", entry["file"])):
            new[slug] = entry
    json.dump({"_meta": {"total": len(new), "batch": batch,
                         "source": "reference-library + src/" + batch,
                         "crop": f"square {OUTPUT_SIZE}x{OUTPUT_SIZE}; zoom per framing {ZOOM}"},
               "moods": new}, open(os.path.join(BASE, "moods.json"), "w"),
              ensure_ascii=False, indent=2)
    print(f"[manifest] {len(new)} moods in {BASE}/moods.json")


def contact_sheet(dest):
    """Contact sheet of the crops, in a circle, the way Discord shows them."""
    from PIL import Image, ImageDraw
    crops = sorted(os.listdir(os.path.join(BASE, "crop")))
    T, COLS = 150, 7
    rows = (len(crops) + COLS - 1) // COLS
    sh = Image.new("RGB", (COLS * T, rows * (T + 14)), "white")
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
    sh.save(dest)
    print(f"[contact] {dest} — look at it before calling it done")


def main():
    global BASE, LIBRARY, REF_PATTERN
    ap = argparse.ArgumentParser(
        description="Turn a character's reference library into square avatar crops + moods.json.")
    ap.add_argument("--base", default=BASE,
                    help="avatars directory (default: $AVATAR_BASE or ./avatars)")
    ap.add_argument("--library", default=LIBRARY,
                    help="reference-library JSON with entries + collections ($AVATAR_LIBRARY)")
    ap.add_argument("--ref-pattern", default=REF_PATTERN,
                    help="regex for the reference_id prefix of each filename ($AVATAR_REF_PATTERN)")
    ap.add_argument("--batch", default="v1", help="batch name (becomes <base>/src/<batch>/)")
    ap.add_argument("--folder", help="Drive folder id; without it, nothing is downloaded "
                                     "(needs $GOOGLE_DRIVE_TOKEN)")
    ap.add_argument("--cv-python", help="python from a venv with opencv-python-headless<5")
    ap.add_argument("--contact-sheet", metavar="FILE.png",
                    help="generate the contact sheet and exit")
    a = ap.parse_args()
    BASE, LIBRARY, REF_PATTERN = a.base, a.library, a.ref_pattern

    src = os.path.join(BASE, "src", a.batch)
    faces = os.path.join(BASE, f"faces_{a.batch}.json")

    if a.contact_sheet:
        contact_sheet(a.contact_sheet)
        return
    if a.folder:
        download(a.folder, src)
    if not os.path.isdir(src):
        sys.exit(f"{src} not found — pass --folder to download the batch")
    if a.cv_python:
        detect(a.cv_python, src, faces)
    elif not os.path.exists(faces):
        sys.exit(f"no {faces} and no --cv-python: no way to find the faces")
    crop(src, faces)
    manifest(src, a.batch)


if __name__ == "__main__":
    main()
