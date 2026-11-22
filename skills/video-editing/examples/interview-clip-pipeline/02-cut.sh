#!/usr/bin/env bash
# Frame-accurate cut: cold open (hook) + main take, re-encoded with identical
# parameters and concatenated without re-encoding.
# Cut points come from the word-level JSON (word_captions_map.py) so that each
# boundary sits on a real word boundary.
set -e

IN="${IN:-/path/to/ORIGINAL.mp4}"
OUT="${OUT:-/path/to/output-folder}"
NAME="${NAME:-clip1}"

# Segments on the ORIGINAL timeline, in seconds (placeholders — set yours).
# *_TO = the END of the last word (Whisper `end`). The script adds TAIL_PAD so
# the word can finish before the next segment/transition (SKILL.md section 2.1:
# Whisper ends come early and "dry" cuts were a recurring problem).
HOOK_FROM="${HOOK_FROM:-41.40}";  HOOK_TO="${HOOK_TO:-46.65}"
BODY_FROM="${BODY_FROM:-14.42}";  BODY_TO="${BODY_TO:-55.66}"
TAIL_PAD="${TAIL_PAD:-0.4}"        # 0.3 to 0.5 s; use 0.5 for Portuguese speech; lower it only if the next word starts sooner
HOOK_TO=$(awk "BEGIN{print $HOOK_TO+$TAIL_PAD}")
BODY_TO=$(awk "BEGIN{print $BODY_TO+$TAIL_PAD}")
echo "padded out-points: hook $HOOK_FROM-$HOOK_TO, body $BODY_FROM-$BODY_TO (use these in word_captions_map.py --segments)"

# Optional HDR->SDR correction for iPhone HLG sources (leave empty for SDR).
# TM='scale=1080:1920:flags=lanczos,zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p'
TM="${TM:-}"
VF_ARGS=(); [ -n "$TM" ] && VF_ARGS=(-vf "$TM")

ENC=(-c:v libx264 -preset slow -crf 18 -r 30 -pix_fmt yuv420p -c:a aac -b:a 192k -ar 48000 -ac 2)

mkdir -p "$OUT" /tmp/work-$NAME && cd /tmp/work-$NAME

# -ss/-to AFTER -i = frame-accurate on the original timeline
ffmpeg -nostdin -y -loglevel error -i "$IN" -ss "$HOOK_FROM" -to "$HOOK_TO" "${VF_ARGS[@]}" "${ENC[@]}" p1.mp4
echo P1-OK
ffmpeg -nostdin -y -loglevel error -i "$IN" -ss "$BODY_FROM" -to "$BODY_TO" "${VF_ARGS[@]}" \
  -af "afade=t=out:st=$(awk "BEGIN{print $BODY_TO-$BODY_FROM-0.12}"):d=0.12" "${ENC[@]}" p2.mp4   # fade only inside the tail
echo P2-OK

printf "file 'p1.mp4'\nfile 'p2.mp4'\n" > concat.txt
ffmpeg -nostdin -y -loglevel error -f concat -safe 0 -i concat.txt -c copy -movflags +faststart "$OUT/$NAME-CUT.mp4"

echo "duration: $(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$OUT/$NAME-CUT.mp4")"
echo "hook length (for the transition scripts): $(awk "BEGIN{print $HOOK_TO-$HOOK_FROM}")"
cd / && rm -rf /tmp/work-$NAME
echo CUT-DONE
