set -e
WK='/mnt/c/Users/ferna/Downloads/ianka-ingles-trabalho'
WH='/mnt/c/Users/ferna/.claude/skills/video-editing/assets/whoosh-lowend-260ms.wav'
cp "$WK/ianka-ingles-CORTE-words.ass" /tmp/isubs.ass

ffmpeg -nostdin -y -loglevel error -i "$WK/ianka-ingles-CORTE.mp4" -i "$WH" -filter_complex \
"[0:v]trim=0:4.95,setpts=PTS-STARTPTS[va];\
[0:v]trim=4.95:5.25,setpts=PTS-STARTPTS,zoompan=z='min(1.12,1+0.12*pow(on/8,2))':d=1:x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2':s=1080x1920:fps=30,setsar=1,fade=t=out:st=0.15:d=0.15:c=white[vb];\
[0:v]trim=5.25,setpts=PTS-STARTPTS,fade=t=in:st=0:d=0.15:c=white[vc];\
[va][vb][vc]concat=n=3:v=1:a=0[vcat];\
[vcat]ass=/tmp/isubs.ass:fontsdir=/mnt/c/Windows/Fonts[vout];\
[1:a]adelay=5170|5170,volume=-6dB[wh];\
[0:a][wh]amix=inputs=2:duration=first:normalize=0[aout]" \
-map "[vout]" -map "[aout]" \
-c:v libx264 -crf 18 -preset slow -r 30 \
-c:a aac -b:a 192k -ar 48000 -ac 2 "$WK/ianka-ingles-REELS-FINAL.mp4"

ffprobe -v error -show_entries format=duration -of default=nw=1 "$WK/ianka-ingles-REELS-FINAL.mp4"
rm -f /tmp/isubs.ass
echo REELS-DONE
