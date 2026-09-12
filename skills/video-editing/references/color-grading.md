# Color grading in ffmpeg (for interview cuts)

Written from scratch for this pipeline. The color-science ideas are domain
knowledge (free); the numbers here were **measured on one machine** on
2026-08-09, not copied. Filters verified on BOTH builds: WSL 4.4.2 and
Windows 7.1.

Scope: real talk/interview footage (phone, iPhone HLG, event camera). Does not
cover creative grading for fiction — our goal is to **look natural and
consistent**, not "cinematic".

## When NOT to grade

Start here, because it is the right answer for most cuts:

- **Footage already well exposed** → leave it alone. A bad grade is worse than none.
- **A single cut, with no intercut sources** → nobody has a reference to compare against.
- **If the problem is exposure / wrong white balance**, that is *correction*, not
  grading — fix it and stop. Grading is the aesthetic layer that comes after.

The case that genuinely calls for grading here: **joining footage from
different cameras/moments in the same cut** (cold open from one take, body
from another). Then the inconsistency jumps out and the correction earns its keep.

## Chain order (it matters)

Each filter operates on the previous one's output, so the order changes the result:

```
1. tonemap/zscale     — only for HLG/HDR (see the iPhone recipe below)
2. colortemperature   — fix the white balance first
3. colorbalance       — shift color per range (shadows/mids/highlights)
4. curves             — shape contrast
5. eq                 — final contrast/saturation tweak
6. lut3d              — creative LUT LAST, on top of an already-corrected image
```

Rule of thumb: **correct before you stylize**. A LUT on top of a wrong white
balance multiplies the error instead of hiding it.

## The filters we use

| Filter | What for | Parameters |
|---|---|---|
| `eq` | contrast, saturation, brightness, gamma | `contrast=1.0:saturation=1.0:brightness=0.0:gamma=1.0` |
| `colorbalance` | color per tonal range | `rs/gs/bs` shadows · `rm/gm/bm` mids · `rh/gh/bh` highlights (−1..1) |
| `curves` | tone curve | `all='0/0 0.5/0.5 1/1'` or `red=`/`green=`/`blue=` |
| `colortemperature` | white balance | `temperature=6500` neutral · **lower = warmer** |
| `lut3d` | applies a .cube | `lut3d='file.cube'` |
| `normalize` | stretches the histogram | `blackpt=black:whitept=white` |

⚠️ `colortemperature` is counter-intuitive: the parameter is the temperature of
the scene's LIGHT, so **lowering the number warms the image**. `temperature=5000`
comes out warmer than `6500`, not cooler.

All of them exist in WSL's 4.4.2 and Windows' 7.1 (verified 2026-08-09).

## Recipes (measured, not guessed)

Reference values measured on `testsrc2` — the U column is the blue-difference
channel, which is where temperature shows up objectively (lower U = less blue =
warmer). Measured neutral: **Y=124.7 U=127.4 V=125.2**.

### Warm / welcoming — `Y=125.5 U=123.5` (−3.9 U, warmer)

```
colorbalance=rs=0.06:gs=0.02:bs=-0.04:rh=0.05:gh=0.01:bh=-0.03,eq=contrast=1.05:saturation=1.08
```

For testimonials, personal stories, connection-oriented content.

### Cool / technical — `Y=123.5 U=128.6` (+1.1 U, cooler)

```
colorbalance=rs=-0.03:bs=0.06:rh=-0.02:bh=0.04,eq=contrast=1.06:saturation=0.95
```

For technical content, especially when the cut includes a dark-IDE screenshot.

### Punch (high contrast) — `Y=123.0`, crushed shadows

```
curves=all='0/0 0.15/0.08 0.5/0.52 0.85/0.92 1/1',eq=contrast=1.15:saturation=1.2
```

Grabs attention in the feed. ⚠️ **Measures more aggressive than it looks** — see
the skin section before using it on a close-up.

### Muted / serious — `Y=121.2`, washed contrast

```
curves=all='0/0.04 0.25/0.22 0.5/0.47 0.75/0.73 1/0.94',eq=contrast=1.03:saturation=0.75
```

Lifts the black (0/0.04) and holds back the white (1/0.94): the documentary
"faded" look.

## Skin: the deciding test

Skin is where the eye spots a wrong grade instantly. The classic reference is
the vectorscope "skin tone line" (~123°, between red and yellow).

**Three skin tones were measured before and after each grade** (chroma vector
angle; what matters is the DEVIATION, not the absolute value):

| Tone | Neutral | Warm | Punch | `saturation=1.3` |
|---|---|---|---|---|
| Medium (#C68642) | 139.8° | 141.6° (+1.8) | **143.3° (+3.5)** | 141.1° (+1.3) |
| Light (#F1C27D) | 144.9° | 146.0° (+1.1) | **154.8° (+9.9)** | 146.0° (+1.1) |
| Dark (#8D5524) | 137.0° | 139.3° (+2.3) | **133.1° (−3.9)** | 138.8° (+1.8) |

What this shows — worth more than any memorized rule:

1. **The warm grade is safe** — it shifts ≤2.3° on every tone. Go ahead.
2. **Punch is the dangerous one, and unevenly so**: almost 10° on light skin,
   and it pulls dark skin the OPPOSITE way (−3.9°). In other words, it doesn't
   "saturate more", it **distorts hue differently depending on the tone** — two
   participants with different skin end up misaligned with each other.
3. **The curve is the culprit, not the saturation**: `saturation=1.3` on its own
   shifts only ~1.5°, less than the whole punch. The common rule "don't go past
   1.2 saturation" aims at the wrong target — what twists skin is the contrast
   curve.

**Rule of thumb from this**: on a close-up of a person, prefer the warm grade or
nothing. If you must use punch, **soften the curve before touching saturation** —
swapping `0.15/0.08 ... 0.85/0.92` for `0.15/0.11 ... 0.85/0.90` removes a good
part of the deviation (measured):

| Tone | Original punch | Soft punch |
|---|---|---|
| Medium | +3.5° | +2.9° |
| Light | +9.9° | **+6.2°** |
| Dark | −3.9° | **−1.3°** |

The gain is exactly where it hurt most (light and dark skin). Soft version:

```
curves=all='0/0 0.15/0.11 0.5/0.52 0.85/0.90 1/1',eq=contrast=1.15:saturation=1.2
```

And always extract a frame and LOOK (rule 5) — numbers don't replace eyes.

## iPhone HDR/HLG → SDR

The most common "wrong color" case here isn't grading, it's **HLG delivered as
if it were SDR** — it comes out washed and grayish. See the HDR example in
`examples/`; the chain:

```
zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p
```

`hable` preserves highlights better than `reinhard`. `desat=0` avoids the
desaturation tonemapping usually introduces. This is **correction**; it runs
before any grade.

## .cube LUT

```bash
# LUT at 70% (blended with the original) — validated on both builds 2026-08-09
ffmpeg -nostdin -y -i in.mp4 -filter_complex \
  "split[a][b];[b]lut3d='my.cube'[g];[a][g]blend=all_mode=normal:all_opacity=0.7" \
  -c:a copy out.mp4
```

- A LUT at 100% almost always overdoes it; **0.6-0.8 is the useful range**.
- Correct (white balance/exposure) FIRST; the LUT is the last layer.
- **One LUT per video.** Switching between scenes breaks the consistency that
  the grade was supposed to fix in the first place.
- Test on a frame with skin before running the whole video.

## Are burned-in captions still readable?

A dark grade reduces the text's contrast against the background. Our captions
use a black outline, which already protects a lot — but after a "muted"-style
grade (which lifts black to 0.04) it's worth checking a frame with a caption
over the brightest area of the video.

Reference: 4.5:1 is the minimum contrast for text (WCAG AA). In practice the
honest check here is visual — extract the frame and look.

## Recommended workflow

```bash
# 1) reference frame BEFORE grading the whole video (saves a render)
ffmpeg -nostdin -y -ss 10 -i IN.mp4 -frames:v 1 /tmp/before.png

# 2) test the grade on the frame
ffmpeg -nostdin -y -i /tmp/before.png -vf "<CHAIN>" /tmp/after.png

# 3) LOOK at both (Read). Only then run the whole video.
# 4) grade together with captions and format = ONE encode
```

Adjust in small steps (±0.05) and re-check. A good grade is one nobody notices.
