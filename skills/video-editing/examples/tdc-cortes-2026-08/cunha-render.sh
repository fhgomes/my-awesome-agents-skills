set -e
WK='/mnt/c/Users/ferna/Downloads/cunha-mercado-trabalho'
WH='/mnt/c/Users/ferna/.claude/skills/video-editing/assets/whoosh-lowend-260ms.wav'

sed 's/PlayResY: 1920/PlayResY: 1080/; s/,88,/,64,/; s/,60,60,400,1/,60,60,90,1/' \
  "$WK/cunha-corte1-CORTE-words.ass" > "$WK/cunha-corte1-LINKEDIN-words.ass"
sed 's/PlayResY: 1920/PlayResY: 1080/; s/,88,/,64,/; s/,60,60,400,1/,60,60,90,1/' \
  "$WK/cunha-corte2-CORTE-words.ass" > "$WK/cunha-corte2-LINKEDIN-words.ass"
cp "$WK/cunha-corte1-CORTE-words.ass" /tmp/c1subs.ass
cp "$WK/cunha-corte2-CORTE-words.ass" /tmp/c2subs.ass
cp "$WK/cunha-corte1-LINKEDIN-words.ass" /tmp/c1li.ass
cp "$WK/cunha-corte2-LINKEDIN-words.ass" /tmp/c2li.ass

ffmpeg -nostdin -y -loglevel error -i "$WK/cunha-corte1-CORTE.mp4" -i "$WH" -filter_complex \
"[0:v]trim=0:3.30,setpts=PTS-STARTPTS[va];\
[0:v]trim=3.30:3.60,setpts=PTS-STARTPTS,zoompan=z='min(1.12,1+0.12*pow(on/8,2))':d=1:x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2':s=1080x1920:fps=30,setsar=1,fade=t=out:st=0.15:d=0.15:c=white[vb];\
[0:v]trim=3.60,setpts=PTS-STARTPTS,fade=t=in:st=0:d=0.15:c=white[vc];\
[va][vb][vc]concat=n=3:v=1:a=0[vcat];\
[vcat]ass=/tmp/c1subs.ass:fontsdir=/mnt/c/Windows/Fonts[vout];\
[1:a]adelay=3520|3520,volume=-6dB[wh];\
[0:a][wh]amix=inputs=2:duration=first:normalize=0[aout]" \
-map "[vout]" -map "[aout]" -c:v libx264 -crf 18 -preset slow -r 30 \
-c:a aac -b:a 192k -ar 48000 -ac 2 "$WK/cunha-corte1-REELS-FINAL.mp4"
echo C1-REELS-OK

ffmpeg -nostdin -y -loglevel error -i "$WK/cunha-corte1-CORTE.mp4" -i "$WH" -filter_complex \
"[0:v]trim=0:3.30,setpts=PTS-STARTPTS[va];\
[0:v]trim=3.30:3.60,setpts=PTS-STARTPTS,zoompan=z='min(1.10,1+0.10*pow(on/8,2))':d=1:x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2':s=1080x1920:fps=30,setsar=1,fade=t=out:st=0.15:d=0.15:c=white[vb];\
[0:v]trim=3.60,setpts=PTS-STARTPTS,fade=t=in:st=0:d=0.15:c=white[vc];\
[va][vb][vc]concat=n=3:v=1:a=0[vcat];\
[vcat]split[b1][f1];\
[b1]scale=1080:1080:force_original_aspect_ratio=increase,crop=1080:1080,gblur=sigma=30[bg];\
[f1]scale=-2:1080[fg];\
[bg][fg]overlay=(W-w)/2:(H-h)/2,ass=/tmp/c1li.ass:fontsdir=/mnt/c/Windows/Fonts[vout];\
[1:a]adelay=3520|3520,volume=-9dB[wh];\
[0:a][wh]amix=inputs=2:duration=first:normalize=0[aout]" \
-map "[vout]" -map "[aout]" -c:v libx264 -crf 18 -preset slow -r 30 \
-c:a aac -b:a 192k -ar 48000 -ac 2 "$WK/cunha-corte1-LINKEDIN-FINAL.mp4"
echo C1-LINKEDIN-OK

ffmpeg -nostdin -y -loglevel error -i "$WK/cunha-corte2-CORTE.mp4" \
-vf "ass=/tmp/c2subs.ass:fontsdir=/mnt/c/Windows/Fonts" \
-c:v libx264 -crf 18 -preset slow -c:a copy "$WK/cunha-corte2-REELS-FINAL.mp4"
echo C2-REELS-OK

ffmpeg -nostdin -y -loglevel error -i "$WK/cunha-corte2-CORTE.mp4" -filter_complex \
"[0:v]split[b1][f1];\
[b1]scale=1080:1080:force_original_aspect_ratio=increase,crop=1080:1080,gblur=sigma=30[bg];\
[f1]scale=-2:1080[fg];\
[bg][fg]overlay=(W-w)/2:(H-h)/2,ass=/tmp/c2li.ass:fontsdir=/mnt/c/Windows/Fonts[vout]" \
-map "[vout]" -map 0:a -c:v libx264 -crf 18 -preset slow -c:a copy "$WK/cunha-corte2-LINKEDIN-FINAL.mp4"
echo C2-LINKEDIN-OK

for f in cunha-corte1-REELS-FINAL cunha-corte1-LINKEDIN-FINAL cunha-corte2-REELS-FINAL cunha-corte2-LINKEDIN-FINAL; do
  echo "$f: $(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$WK/$f.mp4")"
done
rm -f /tmp/c1subs.ass /tmp/c2subs.ass /tmp/c1li.ass /tmp/c2li.ass
echo CUNHA-RENDER-DONE
