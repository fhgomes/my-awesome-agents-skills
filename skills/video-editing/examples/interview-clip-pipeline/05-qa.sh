#!/usr/bin/env bash
# QA without watching the whole thing: frames at known moments (hook, flash,
# zoomed body, end), a spectrogram around the cut to see the whoosh, and the
# delivery check (profile / pix_fmt) that catches the yuv444p trap.
set -e

OUT="${OUT:-/path/to/output-folder}"
NAME="${NAME:-clip1}"
HOOK_LEN="${HOOK_LEN:-5.25}"
QA="${QA:-$OUT/qa}"
R="$OUT/$NAME-REELS-FINAL.mp4"
L="$OUT/$NAME-LINKEDIN-FINAL.mp4"

mkdir -p "$QA"
FLASH=$(awk "BEGIN{print $HOOK_LEN-0.07}")     # inside the white flash
ZOOM=$(awk "BEGIN{print $HOOK_LEN-0.20}")      # mid zoom
BODY=$(awk "BEGIN{print $HOOK_LEN+0.75}")      # first body frame after the fade-in
SPEC_FROM=$(awk "BEGIN{print $HOOK_LEN-0.75}")
SPEC_TO=$(awk "BEGIN{print $HOOK_LEN+0.75}")
END=$(awk "BEGIN{print $(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$R")-0.2}")

ffmpeg -nostdin -y -loglevel error -ss 1.0     -i "$R" -frames:v 1 "$QA/r-hook.jpg"
ffmpeg -nostdin -y -loglevel error -ss "$ZOOM"  -i "$R" -frames:v 1 "$QA/r-zoom.jpg"
ffmpeg -nostdin -y -loglevel error -ss "$FLASH" -i "$R" -frames:v 1 "$QA/r-flash.jpg"
ffmpeg -nostdin -y -loglevel error -ss "$BODY"  -i "$R" -frames:v 1 "$QA/r-body.jpg"
ffmpeg -nostdin -y -loglevel error -ss "$END"   -i "$R" -frames:v 1 "$QA/r-end.jpg"
ffmpeg -nostdin -y -loglevel error -ss "$SPEC_FROM" -to "$SPEC_TO" -i "$R" \
  -filter_complex "[0:a]showspectrumpic=s=800x400:legend=1[o]" -map "[o]" -frames:v 1 "$QA/r-spectrum.png"

if [ -f "$L" ]; then
  ffmpeg -nostdin -y -loglevel error -ss "$FLASH" -i "$L" -frames:v 1 "$QA/l-flash.jpg"
  ffmpeg -nostdin -y -loglevel error -ss "$BODY"  -i "$L" -frames:v 1 "$QA/l-body.jpg"
fi

# Delivery check: must be profile=High|Main|Baseline and pix_fmt=yuv420p
for f in "$R" "$L"; do
  [ -f "$f" ] || continue
  echo "== $f"
  ffprobe -v error -select_streams v:0 -show_entries stream=profile,pix_fmt,width,height -of default=noprint_wrappers=1 "$f"
done
echo QA-DONE
