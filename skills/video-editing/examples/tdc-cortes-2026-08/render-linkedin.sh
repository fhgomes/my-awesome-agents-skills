set -e
WK='/mnt/c/Users/ferna/Downloads/ianka-ingles-trabalho'
WH='/mnt/c/Users/ferna/.claude/skills/video-editing/assets/whoosh-lowend-260ms.wav'
sed 's/PlayResY: 1920/PlayResY: 1080/; s/,88,/,64,/; s/,60,60,400,1/,60,60,90,1/' \
  "$WK/ianka-ingles-CORTE-words.ass" > "$WK/ianka-ingles-LINKEDIN-words.ass"
cp "$WK/ianka-ingles-LINKEDIN-words.ass" /tmp/lisubs.ass

ffmpeg -nostdin -y -loglevel error -i "$WK/ianka-ingles-CORTE.mp4" -i "$WH" -filter_complex \
"[0:v]trim=0:4.95,setpts=PTS-STARTPTS[va];\
[0:v]trim=4.95:5.25,setpts=PTS-STARTPTS,zoompan=z='min(1.10,1+0.10*pow(on/8,2))':d=1:x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2':s=1080x1920:fps=30,setsar=1,fade=t=out:st=0.15:d=0.15:c=white[vb];\
[0:v]trim=5.25,setpts=PTS-STARTPTS,fade=t=in:st=0:d=0.15:c=white[vc];\
[va][vb][vc]concat=n=3:v=1:a=0[vcat];\
[vcat]split[b1][f1];\
[b1]scale=1080:1080:force_original_aspect_ratio=increase,crop=1080:1080,gblur=sigma=30[bg];\
[f1]scale=-2:1080[fg];\
[bg][fg]overlay=(W-w)/2:(H-h)/2,ass=/tmp/lisubs.ass:fontsdir=/mnt/c/Windows/Fonts[vout];\
[1:a]adelay=5170|5170,volume=-9dB[wh];\
[0:a][wh]amix=inputs=2:duration=first:normalize=0[aout]" \
-map "[vout]" -map "[aout]" \
-c:v libx264 -crf 18 -preset slow -r 30 \
-c:a aac -b:a 192k -ar 48000 -ac 2 "$WK/ianka-ingles-LINKEDIN-FINAL.mp4"

ffprobe -v error -show_entries format=duration -of default=nw=1 "$WK/ianka-ingles-LINKEDIN-FINAL.mp4"
rm -f /tmp/lisubs.ass
echo LINKEDIN-DONE
