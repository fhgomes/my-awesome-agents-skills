set -e
WK='/mnt/c/Users/ferna/Downloads/marco-eventos-trabalho'
WH='/mnt/c/Users/ferna/.claude/skills/video-editing/assets/whoosh-lowend-260ms.wav'
cp "$WK/marco-corte1-CORTE-words.ass" /tmp/m1subs.ass
cp "$WK/marco-corte2-CORTE-words.ass" /tmp/m2subs.ass

ffmpeg -nostdin -y -loglevel error -i "$WK/marco-corte1-CORTE.mp4" -i "$WH" -filter_complex \
"[0:v]trim=0:5.65,setpts=PTS-STARTPTS[va];\
[0:v]trim=5.65:5.95,setpts=PTS-STARTPTS,zoompan=z='min(1.12,1+0.12*pow(on/8,2))':d=1:x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2':s=1080x1920:fps=30,setsar=1,fade=t=out:st=0.15:d=0.15:c=white[vb];\
[0:v]trim=5.95,setpts=PTS-STARTPTS,fade=t=in:st=0:d=0.15:c=white[vc];\
[va][vb][vc]concat=n=3:v=1:a=0[vcat];\
[vcat]ass=/tmp/m1subs.ass:fontsdir=/mnt/c/Windows/Fonts[vout];\
[1:a]adelay=5870|5870,volume=-6dB[wh];\
[0:a][wh]amix=inputs=2:duration=first:normalize=0[aout]" \
-map "[vout]" -map "[aout]" -c:v libx264 -crf 18 -preset slow -r 30 \
-c:a aac -b:a 192k -ar 48000 -ac 2 "$WK/marco-corte1-REELS-FINAL.mp4"
echo M1-REELS-OK

ffmpeg -nostdin -y -loglevel error -i "$WK/marco-corte2-CORTE.mp4" \
-vf "ass=/tmp/m2subs.ass:fontsdir=/mnt/c/Windows/Fonts" \
-c:v libx264 -crf 18 -preset slow -c:a copy "$WK/marco-corte2-REELS-FINAL.mp4"
echo M2-REELS-OK

echo "m1: $(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$WK/marco-corte1-REELS-FINAL.mp4")"
echo "m2: $(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$WK/marco-corte2-REELS-FINAL.mp4")"
rm -f /tmp/m1subs.ass /tmp/m2subs.ass
echo MARCO-RENDER-DONE
