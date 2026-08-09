set -e
OUT=/mnt/c/Users/ferna/Downloads
SP='/mnt/c/Users/ferna/AppData/Local/Temp/claude/D--Programas-workspaces-vault/e227e2bf-ec82-4f46-83a5-b9cbccf22d09/scratchpad'

# 1) Nivel da voz ao redor do corte (3.0-4.2s) para calibrar o whoosh
ffmpeg -nostdin -hide_banner -ss 3.0 -t 1.2 -i "$OUT/matheus-sdd-CORTE.mp4" \
  -vn -af volumedetect -f null - 2>&1 | grep -E "mean_volume|max_volume"

# 2) Whoosh low-end 260ms: ruido rosa lowpass 900Hz + envelope (in 70ms, out 170ms)
#    + tiny hit grave (sine 95Hz, decay rapido) somado no pico (t=80ms)
ffmpeg -nostdin -y -loglevel error -filter_complex \
"anoisesrc=color=pink:duration=0.26:sample_rate=48000:seed=7,highpass=f=80,lowpass=f=900,afade=t=in:st=0:d=0.07:curve=tri,afade=t=out:st=0.09:d=0.17:curve=exp,volume=6dB[wh];\
sine=frequency=95:duration=0.12:sample_rate=48000,afade=t=in:st=0:d=0.01,afade=t=out:st=0.02:d=0.10:curve=exp,adelay=70|70,volume=3dB[hit];\
[wh][hit]amix=inputs=2:duration=longest:normalize=0,alimiter=limit=0.9,aformat=channel_layouts=stereo" \
"$SP/whoosh_raw.wav"
echo WHOOSH_RAW_OK
