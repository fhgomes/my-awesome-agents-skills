#!/usr/bin/env bash
# Probe the source, extract one frame to LOOK at (orientation, exposure) and a
# 16 kHz mono WAV for transcription. Run as a file: bash 00-probe.sh
set -e

IN="${IN:-/path/to/ORIGINAL.mp4}"        # source video
WORK="${WORK:-/path/to/work-folder}"     # where probes/frames/wav go
FRAME_AT="${FRAME_AT:-30}"               # second to grab the inspection frame

mkdir -p "$WORK"

ffprobe -v error -show_format -show_streams -of json "$IN" > "$WORK/probe.json"
ffmpeg -nostdin -y -loglevel error -ss "$FRAME_AT" -i "$IN" -frames:v 1 "$WORK/frame-t${FRAME_AT}.jpg"
ffmpeg -nostdin -y -loglevel error -i "$IN" -vn -ac 1 -ar 16000 -c:a pcm_s16le "$WORK/audio-16k.wav"

# Capability checks on THIS ffmpeg build (filters differ between versions)
echo "zscale : $(ffmpeg -hide_banner -filters 2>/dev/null | grep -c zscale)"
echo "tonemap: $(ffmpeg -hide_banner -filters 2>/dev/null | grep -c ' tonemap ')"
echo "zoompan in_time: $(ffmpeg -hide_banner -h filter=zoompan 2>/dev/null | grep -ci in_time)"
echo PROBE-DONE
