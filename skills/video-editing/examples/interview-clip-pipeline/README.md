# Example — interview clip pipeline (cold open + question + answer)

A parameterized version of the pipeline used to turn a recorded interview
into short-form clips for Reels (9:16) and LinkedIn (1:1 / 4:5). These are
**reference scripts, not a turnkey tool**: every script starts with a block
of variables (input file, work folder, cut points) that you must set for your
footage. Timestamps below are placeholders.

All scripts are meant to run in a Linux shell (WSL works) with ffmpeg + libass.
Pass them to bash **as files, never through a pipe** (see rule 2 of the skill).

## Pipeline (in execution order)

1. **Probe + inspection frames** — `00-probe.sh`: ffprobe as JSON, one frame
   to LOOK at the real orientation/quality, and a 16 kHz mono WAV for
   transcription.
2. **HDR → SDR test (iPhone HLG only)** — `01-tonemap-test.sh`: renders one
   frame with `hable` and one with `mobius` so you can pick the operator.
3. **Word-level transcription, once, on the ORIGINAL** —
   `../../scripts/word_captions_map.py`: produces `-words.json` with per-word
   timestamps. `--segments "a-b,c-d"` derives the captions of each clip by
   remapping the timeline, without re-transcribing the splice (no boundary
   hallucination, the cold open is never swallowed, N clips = 1
   transcription). The same timestamps plan the cut points on word boundaries.
4. **Frame-accurate segment cut + concat** — `02-cut.sh` (optionally with the
   HDR tonemap chain) and `02b-cut-blurpad.sh` (low-res horizontal source →
   9:16 blurred pad applied while cutting): each segment is re-encoded with
   identical parameters (`-ss/-to` after `-i`) and concatenated without
   re-encoding.
5. **Hook → content transition + caption burn** — `03-render-reels.sh` (9:16)
   and `04-render-linkedin.sh` (1:1, with a 4:5 variant): animated zoom
   100→112% (`zoompan` with per-frame easing) + white flash **per segment**
   (fade out/in before concat, never on the global timeline) + low-end whoosh
   aligned to the cut frame (`../../assets/whoosh-lowend-260ms.wav`), with the
   `.ass` burned in the same filter chain. The LinkedIn version reuses the 9:16
   `.ass` via sed.
6. **QA by frames** — `05-qa.sh`: frames at known timestamps (hook, flash,
   body, end) plus `showspectrumpic` to validate the whoosh without listening,
   and the delivery `ffprobe` check (profile / pix_fmt).

## Source particularities

- **iPhone 4K HLG (HDR)**: the pipeline uses **tonemap hable** (zscale linear →
  tonemap → bt709) for SDR output without washed-out colors — see the `TM`
  variable in `02-cut.sh`.
- **Low-res / horizontal source**: 9:16 canvas with **blur pad** (blurred
  `gblur` background + centered overlay) — see `02b-cut-blurpad.sh`.

## Files

| File | Role |
|---|---|
| `00-probe.sh` | probe JSON, inspection frame, 16 kHz WAV |
| `01-tonemap-test.sh` | hable vs mobius (HDR → SDR) on one frame |
| `02-cut.sh` | frame-accurate cuts + concat (optional HDR tonemap) |
| `02b-cut-blurpad.sh` | same, with 9:16 blur pad applied during the cut |
| `03-render-reels.sh` | zoom + flash + whoosh transition + `.ass` burn, 9:16 |
| `04-render-linkedin.sh` | 1:1 (and 4:5) layout from the 9:16 cut, reusing the `.ass` |
| `05-qa.sh` | visual QA frames, spectrogram, delivery ffprobe check |
