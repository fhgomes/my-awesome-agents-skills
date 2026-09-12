#!/usr/bin/env bash
# HDR (iPhone HLG) -> SDR: render ONE frame with two tonemap operators and
# compare them by eye before committing to a full encode.
set -e

IN="${IN:-/path/to/ORIGINAL-HLG.MOV}"
WORK="${WORK:-/path/to/work-folder}"
FRAME_AT="${FRAME_AT:-42}"

mkdir -p "$WORK"

ffmpeg -nostdin -y -loglevel error -ss "$FRAME_AT" -i "$IN" -frames:v 1 \
  -vf "scale=1080:1920:flags=lanczos,zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p" \
  "$WORK/tm-hable.jpg"
ffmpeg -nostdin -y -loglevel error -ss "$FRAME_AT" -i "$IN" -frames:v 1 \
  -vf "scale=1080:1920:flags=lanczos,zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=mobius,zscale=t=bt709:m=bt709:r=tv,format=yuv420p" \
  "$WORK/tm-mobius.jpg"
echo TM-DONE
