#!/usr/bin/env bash
# Variant of 02-cut.sh for a LOW-RES HORIZONTAL source: apply the 9:16 blurred
# pad while cutting each segment (one encode instead of two). Supports N
# segments; concat without re-encoding.
set -e

IN="${IN:-/path/to/ORIGINAL-horizontal.mp4}"
OUT="${OUT:-/path/to/output-folder}"
NAME="${NAME:-clip2}"

# "from-to" pairs on the ORIGINAL timeline, in order of appearance in the clip.
# First pair = cold open (hook). Placeholders — set yours.
SEGMENTS="${SEGMENTS:-146.05-152.00,52.24-63.70,76.30-134.20}"

FC='[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=30[bg];[0:v]scale=-2:1920[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,format=yuv420p[v]'
ENC=(-c:v libx264 -preset slow -crf 18 -r 30 -c:a aac -b:a 192k -ar 48000 -ac 2)

mkdir -p "$OUT" /tmp/work-$NAME && cd /tmp/work-$NAME
: > list.txt
i=0
IFS=',' read -ra PAIRS <<< "$SEGMENTS"
for pair in "${PAIRS[@]}"; do
  from="${pair%-*}"; to="${pair#*-}"; i=$((i+1))
  extra=()
  if [ "$i" -eq "${#PAIRS[@]}" ]; then   # fade the audio out on the last segment
    extra=(-af "afade=t=out:st=$(awk "BEGIN{print $to-$from-0.25}"):d=0.25")
  fi
  ffmpeg -nostdin -y -loglevel error -i "$IN" -ss "$from" -to "$to" -filter_complex "$FC" \
    -map '[v]' -map 0:a "${extra[@]}" "${ENC[@]}" "s$i.mp4"
  echo "file 's$i.mp4'" >> list.txt
  echo "S$i-OK ($from-$to)"
done

ffmpeg -nostdin -y -loglevel error -f concat -safe 0 -i list.txt -c copy -movflags +faststart "$OUT/$NAME-CUT.mp4"
echo "duration: $(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$OUT/$NAME-CUT.mp4")"
# Speech level of the body, to calibrate the whoosh volume later
ffmpeg -nostdin -i "$OUT/$NAME-CUT.mp4" -vn -af volumedetect -f null - 2>&1 | grep -E 'mean_volume|max_volume'
cd / && rm -rf /tmp/work-$NAME
echo CUT-DONE
