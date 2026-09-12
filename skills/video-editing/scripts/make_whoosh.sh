set -e
# Usage: make_whoosh.sh [OUT_DIR] [REFERENCE_CLIP]
#   OUT_DIR         where whoosh_raw.wav is written (default: current directory)
#   REFERENCE_CLIP  optional cut whose voice level calibrates the whoosh (step 1 is skipped without it)
OUT="${1:-.}"
IN_REF="${2:-}"

# 1) Voice level around the cut (3.0-4.2s) to calibrate the whoosh
if [ -n "$IN_REF" ]; then
  ffmpeg -nostdin -hide_banner -ss 3.0 -t 1.2 -i "$IN_REF" \
    -vn -af volumedetect -f null - 2>&1 | grep -E "mean_volume|max_volume"
fi

# 2) Low-end whoosh, 260ms: pink noise lowpass 900Hz + envelope (in 70ms, out 170ms)
#    + a tiny low hit (sine 95Hz, fast decay) mixed in at the peak (t=80ms)
ffmpeg -nostdin -y -loglevel error -filter_complex \
"anoisesrc=color=pink:duration=0.26:sample_rate=48000:seed=7,highpass=f=80,lowpass=f=900,afade=t=in:st=0:d=0.07:curve=tri,afade=t=out:st=0.09:d=0.17:curve=exp,volume=6dB[wh];\
sine=frequency=95:duration=0.12:sample_rate=48000,afade=t=in:st=0:d=0.01,afade=t=out:st=0.02:d=0.10:curve=exp,adelay=70|70,volume=3dB[hit];\
[wh][hit]amix=inputs=2:duration=longest:normalize=0,alimiter=limit=0.9,aformat=channel_layouts=stereo" \
"$OUT/whoosh_raw.wav"
echo WHOOSH_RAW_OK
