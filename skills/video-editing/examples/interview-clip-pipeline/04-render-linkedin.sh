#!/usr/bin/env bash
# LinkedIn final from the SAME 9:16 cut: 1:1 (1080x1080) by default, or 4:5
# (1080x1350) with RATIO=45. Reuses the 9:16 .ass via sed (keeps the QA
# corrections — never re-transcribe), softer transition (zoom 10%, whoosh -9 dB).
# Zoom + flash are applied BEFORE the layout so the flash covers the whole frame.
set -e

OUT="${OUT:-/path/to/output-folder}"
NAME="${NAME:-clip1}"
HOOK_LEN="${HOOK_LEN:-5.25}"
RATIO="${RATIO:-11}"                               # 11 = 1:1, 45 = 4:5
SKILL="${SKILL:-$(cd "$(dirname "$0")/../.." && pwd)}"
WHOOSH="$SKILL/assets/whoosh-lowend-260ms.wav"
FONTS_DIR="${FONTS_DIR:-/mnt/c/Windows/Fonts}"

if [ "$RATIO" = "45" ]; then
  H=1350; SED='s/PlayResY: 1920/PlayResY: 1350/; s/,88,/,72,/; s/,60,60,400,1/,60,60,140,1/'; TAG=LINKEDIN45
else
  H=1080; SED='s/PlayResY: 1920/PlayResY: 1080/; s/,88,/,64,/; s/,60,60,400,1/,60,60,90,1/';  TAG=LINKEDIN
fi

ZOOM_START=$(awk "BEGIN{print $HOOK_LEN-0.30}")
ADELAY=$(awk "BEGIN{printf \"%d\", ($HOOK_LEN-0.08)*1000}")

sed "$SED" "$OUT/$NAME-CUT-words.ass" > "$OUT/$NAME-$TAG-words.ass"
cp "$OUT/$NAME-$TAG-words.ass" "/tmp/$NAME-li.ass"

ffmpeg -nostdin -y -loglevel error -i "$OUT/$NAME-CUT.mp4" -i "$WHOOSH" -filter_complex \
"[0:v]trim=0:$ZOOM_START,setpts=PTS-STARTPTS[va];\
[0:v]trim=$ZOOM_START:$HOOK_LEN,setpts=PTS-STARTPTS,zoompan=z='min(1.10,1+0.10*pow(on/8,2))':d=1:x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2':s=1080x1920:fps=30,setsar=1,fade=t=out:st=0.15:d=0.15:c=white[vb];\
[0:v]trim=$HOOK_LEN,setpts=PTS-STARTPTS,fade=t=in:st=0:d=0.15:c=white[vc];\
[va][vb][vc]concat=n=3:v=1:a=0[vcat];\
[vcat]split[b1][f1];\
[b1]scale=1080:$H:force_original_aspect_ratio=increase,crop=1080:$H,gblur=sigma=30[bg];\
[f1]scale=-2:$H[fg];\
[bg][fg]overlay=(W-w)/2:(H-h)/2,ass=/tmp/$NAME-li.ass:fontsdir=$FONTS_DIR,format=yuv420p[vout];\
[1:a]adelay=$ADELAY|$ADELAY,volume=-9dB[wh];\
[0:a][wh]amix=inputs=2:duration=first:normalize=0[aout]" \
-map "[vout]" -map "[aout]" \
-c:v libx264 -crf 18 -preset slow -r 30 -pix_fmt yuv420p -profile:v high \
-c:a aac -b:a 192k -ar 48000 -ac 2 -movflags +faststart "$OUT/$NAME-$TAG-FINAL.mp4"

ffprobe -v error -show_entries format=duration -of default=nw=1 "$OUT/$NAME-$TAG-FINAL.mp4"
rm -f "/tmp/$NAME-li.ass"
echo LINKEDIN-DONE
