#!/usr/bin/env python3
"""Typographic social cover (1200x630) and square icon (512) for a site with no photography.

  python3 og_cover.py --brand "TECH BLOG" --author "JANE DOE" \
      --line1 "Ship faster." --line2 "Break less." \
      --domain blog.example.com --tags architecture,ai,leadership --out ./out

Fonts: Inter + JetBrains Mono are downloaded once into --fonts-dir (default ./fonts) from
their GitHub releases, verified against pinned SHA-256; pass --no-download to require them present.
Colors default to a dark theme (#0a0a0a bg, #e2e8f0 text, #3b82f6 accent); override with flags.
Requires Pillow.
"""
import argparse
import hashlib
import os
import subprocess
import sys
import zipfile

from PIL import Image, ImageDraw, ImageFont

# zips pinned by SHA-256 (fail closed); to bump a font version update URL and hash together
INTER = ('https://github.com/rsms/inter/releases/download/v4.1/Inter-4.1.zip',
         '9883fdd4a49d4fb66bd8177ba6625ef9a64aa45899767dde3d36aa425756b11e',
         {'extras/ttf/Inter-Black.ttf': 'Inter-Black.ttf', 'extras/ttf/Inter-Bold.ttf': 'Inter-Bold.ttf',
          'extras/ttf/Inter-Regular.ttf': 'Inter-Regular.ttf'})
MONO = ('https://github.com/JetBrains/JetBrainsMono/releases/download/v2.304/JetBrainsMono-2.304.zip',
        '6f6376c6ed2960ea8a963cd7387ec9d76e3f629125bc33d1fdcd7eb7012f7bbf',
        {'fonts/ttf/JetBrainsMono-Bold.ttf': 'JetBrainsMono-Bold.ttf',
         'fonts/ttf/JetBrainsMono-Regular.ttf': 'JetBrainsMono-Regular.ttf'})


def hexrgb(s):
    s = s.lstrip('#')
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def ensure_fonts(d, download):
    os.makedirs(d, exist_ok=True)
    for url, sha, members in (INTER, MONO):
        if all(os.path.exists(os.path.join(d, v)) for v in members.values()):
            continue
        if not download:
            sys.exit(f'fonts missing in {d}; drop {", ".join(members.values())} there or allow download')
        z = os.path.join(d, os.path.basename(url))
        subprocess.run(['curl', '-fsSL', '--max-time', '300', '-o', z, '--', url], check=True)
        with open(z, 'rb') as fh:
            got = hashlib.sha256(fh.read()).hexdigest()
        if got != sha:
            os.remove(z)
            sys.exit(f'checksum mismatch for {url}\n  got      {got}\n  expected {sha}\nrefusing to unpack; verify upstream or drop the TTFs in {d} and use --no-download')
        with zipfile.ZipFile(z) as zf:
            for src, dst in members.items():
                with zf.open(src) as fi, open(os.path.join(d, dst), 'wb') as fo:
                    fo.write(fi.read())
        os.remove(z)


def logo_grid(d, x, y, size, color, stroke, inner_ratio=0.52):
    d.rounded_rectangle([x, y, x + size, y + size], radius=size * 0.1, outline=color, width=stroke)
    inner = size * inner_ratio
    ox, oy = x + (size - inner) / 2, y + (size - inner) / 2
    cell, gap = inner * 7 / 24, inner * 4 / 24
    r = max(2, int(inner * 0.04))
    for i in (0, 1):
        for j in (0, 1):
            cx, cy = ox + i * (cell + gap), oy + j * (cell + gap)
            d.rounded_rectangle([cx, cy, cx + cell, cy + cell], radius=r, fill=color)


def spaced(d, xy, text, font, fill, spacing):
    x, y = xy
    for ch in text:
        d.text((x, y), ch, font=font, fill=fill)
        x += d.textlength(ch, font=font) + spacing


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--brand', required=True)
    ap.add_argument('--author', required=True)
    ap.add_argument('--line1', required=True)
    ap.add_argument('--line2', default='')
    ap.add_argument('--domain', required=True)
    ap.add_argument('--tags', default='')
    ap.add_argument('--tagline', default='')
    ap.add_argument('--status', default='', help='optional right-aligned mono text in the top bar')
    ap.add_argument('--bg', default='#0a0a0a')
    ap.add_argument('--fg', default='#e2e8f0')
    ap.add_argument('--muted', default='#94a3b8')
    ap.add_argument('--accent', default='#3b82f6')
    ap.add_argument('--border', default='#1e293b')
    ap.add_argument('--out', default='./out')
    ap.add_argument('--fonts-dir', default='./fonts')
    ap.add_argument('--no-download', action='store_true')
    a = ap.parse_args()

    ensure_fonts(a.fonts_dir, not a.no_download)
    F = lambda name, size: ImageFont.truetype(os.path.join(a.fonts_dir, name), size)  # noqa: E731
    BG, FG, MUTED, ACCENT, BORDER = map(hexrgb, (a.bg, a.fg, a.muted, a.accent, a.border))
    os.makedirs(a.out, exist_ok=True)

    W, H = 1200, 630
    im = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 3], fill=ACCENT)
    mono = F('JetBrainsMono-Regular.ttf', 22)
    d.text((72, 44), '>_ ' + a.domain, font=mono, fill=MUTED)
    if a.status:
        d.text((W - 72, 44), a.status, font=mono, fill=MUTED, anchor='ra')
    d.line([72, 88, W - 72, 88], fill=BORDER, width=1)
    logo_grid(d, 72, 150, 92, FG, 6)
    spaced(d, (192, 152), a.brand, F('Inter-Black.ttf', 44), FG, 4)
    spaced(d, (192, 208), a.author, F('Inter-Bold.ttf', 26), MUTED, 5)
    head = F('Inter-Black.ttf', 72)
    d.text((72, 300), a.line1, font=head, fill=FG)
    if a.line2:
        d.text((72, 386), a.line2, font=head, fill=ACCENT)
    x = 72
    tagf = F('JetBrainsMono-Bold.ttf', 20)
    for t in [t for t in a.tags.split(',') if t]:
        w = d.textlength(t, font=tagf) + 28
        d.rounded_rectangle([x, 530, x + w, 570], radius=3, outline=BORDER, width=2)
        d.text((x + 14, 538), t, font=tagf, fill=MUTED)
        x += w + 14
    if a.tagline:
        d.text((W - 72, 540), a.tagline, font=F('Inter-Regular.ttf', 22), fill=MUTED, anchor='ra')
    cover = os.path.join(a.out, 'og-cover.png')
    im.save(cover, optimize=True)

    ic = Image.new('RGB', (512, 512), BG)
    d = ImageDraw.Draw(ic)
    logo_grid(d, 56, 56, 400, FG, 28, inner_ratio=0.58)
    icon = os.path.join(a.out, 'icon-512.png')
    ic.save(icon, optimize=True)
    for f in (cover, icon):
        print(f, os.path.getsize(f) // 1024, 'KB')


if __name__ == '__main__':
    main()
