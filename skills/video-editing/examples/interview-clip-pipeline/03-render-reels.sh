#!/usr/bin/env bash
# Reels 9:16 final: hook -> content transition (animated zoom 100->112% over the
# last 0.3 s of the hook, white flash PER SEGMENT, low-end whoosh peaking on the
# cut) + word-level .ass burned in the same filter chain.
#
# Requires: $OUT/$NAME-CUT.mp4 (from 02-cut.sh) and $OUT/$NAME-CUT-words.ass
# (from word_captions_map.py --segments ...). HOOK_LEN is the hook duration
# printed by 02-cut.sh. All arithmetic is pre-computed with awk (bc may be
# missing on WSL).
set -e

OUT="${OUT:-/path/to/output-folder}"
NAME="${NAME:-clip1}"
HOOK_LEN="${HOOK_LEN:-5.25}"                       # seconds, from 02-cut.sh
SKILL="${SKILL:-$(cd "$(dirname "$0")/../.." && pwd)}"
WHOOSH="$SKILL/assets/whoosh-lowend-260ms.wav"     # internal peak at ~80 ms
WHOOSH_DB="${WHOOSH_DB:-  -6}"                     # -6 dB reads as "perceptible"; -12 as "subtle"
FONTS_DIR="${FONTS_DIR:-/mnt/c/Windows/Fonts}"     # WSL: Windows fonts for libass

ZOOM_START=$(awk "BEGIN{print $HOOK_LEN-0.30}")    # zoom runs over the last 0.3 s of the hook
ADELAY=$(awk "BEGIN{printf \"%d\", ($HOOK_LEN-0.08)*1000}")   # peak lands on the cut frame

cp "$OUT/$NAME-CUT-words.ass" "/tmp/$NAME-subs.ass"

ffmpeg -nostdin -y -loglevel error -i "$OUT/$NAME-CUT.mp4" -i "$WHOOSH" -filter_complex \
"[0:v]trim=0:$ZOOM_START,setpts=PTS-STARTPTS[va];\
[0:v]trim=$ZOOM_START:$HOOK_LEN,setpts=PTS-STARTPTS,zoompan=z='min(1.12,1+0.12*pow(on/8,2))':d=1:x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2':s=1080x1920:fps=30,setsar=1,fade=t=out:st=0.15:d=0.15:c=white[vb];\
[0:v]trim=$HOOK_LEN,setpts=PTS-STARTPTS,fade=t=in:st=0:d=0.15:c=white[vc];\
[va][vb][vc]concat=n=3:v=1:a=0[vcat];\
[vcat]ass=/tmp/$NAME-subs.ass:fontsdir=$FONTS_DIR,format=yuv420p[vout];\
[1:a]adelay=$ADELAY|$ADELAY,volume=${WHOOSH_DB// /}dB[wh];\
[0:a][wh]amix=inputs=2:duration=first:normalize=0[aout]" \
-map "[vout]" -map "[aout]" \
-c:v libx264 -crf 18 -preset slow -r 30 -pix_fmt yuv420p -profile:v high \
-c:a aac -b:a 192k -ar 48000 -ac 2 -movflags +faststart "$OUT/$NAME-REELS-FINAL.mp4"

ffprobe -v error -show_entries format=duration -of default=nw=1 "$OUT/$NAME-REELS-FINAL.mp4"
rm -f "/tmp/$NAME-subs.ass"
echo REELS-DONE
