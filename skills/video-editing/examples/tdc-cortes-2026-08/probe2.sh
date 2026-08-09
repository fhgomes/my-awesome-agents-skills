set -e
SC='/mnt/c/Users/ferna/AppData/Local/Temp/claude/D--Programas-workspaces-vault/2f9d28a7-3e16-4b7f-ae6c-445b2877f0d5/scratchpad'
IN='/mnt/c/Users/ferna/Downloads/IMG_7855.MOV'
MAT='/mnt/c/Users/ferna/Downloads/matheus-corte1_sdd-REELS-FINAL.mp4'
ffprobe -v error -show_entries stream=codec_type,codec_name,width,height,pix_fmt,color_space,color_transfer,color_primaries,r_frame_rate,sample_rate,channels,bit_rate -of json "$MAT" > "$SC/matheus-final-probe.json"
ffmpeg -nostdin -y -loglevel error -i "$IN" -vn -ac 1 -ar 16000 -c:a pcm_s16le "$SC/ianka-16k.wav"
echo "zscale: $(ffmpeg -hide_banner -filters 2>/dev/null | grep -c zscale)"
echo "tonemap: $(ffmpeg -hide_banner -filters 2>/dev/null | grep -c ' tonemap ')"
echo PROBE2-DONE
