set -e
WK='/mnt/c/Users/ferna/Downloads/marco-eventos-trabalho'
WH='/mnt/c/Users/ferna/.claude/skills/video-editing/assets/whoosh-lowend-260ms.wav'
sed 's/PlayResY: 1920/PlayResY: 1350/; s/,88,/,72,/; s/,60,60,400,1/,60,60,140,1/' "$WK/marco-corte1-CORTE-words.ass" > "$WK/marco-corte1-LINKEDIN45-words.ass"
sed 's/PlayResY: 1920/PlayResY: 1350/; s/,88,/,72,/; s/,60,60,400,1/,60,60,140,1/' "$WK/marco-corte2-CORTE-words.ass" > "$WK/marco-corte2-LINKEDIN45-words.ass"
cp "$WK/marco-corte1-CORTE-words.ass" /tmp/m1subs.ass
cp "$WK/marco-corte2-CORTE-words.ass" /tmp/m2subs.ass
cp "$WK/marco-corte1-LINKEDIN45-words.ass" /tmp/m1li.ass
cp "$WK/marco-corte2-LINKEDIN45-words.ass" /tmp/m2li.ass
ffmpeg -nostdin -y -loglevel error -i "$WK/marco-corte1-CORTE.mp4" -i "$WH" -filter_complex "[0:v]trim=0:5.65,setpts=PTS-STARTPTS[va];[0:v]trim=5.65:5.95,setpts=PTS-STARTPTS,zoompan=z='min(1.12,1+0.12*pow(on/8,2))':d=1:x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2':s=1080x1920:fps=30,setsar=1,fade=t=out:st=0.15:d=0.15:c=white[vb];[0:v]trim=5.95,setpts=PTS-STARTPTS,fade=t=in:st=0:d=0.15:c=white[vc];[va][vb][vc]concat=n=3:v=1:a=0[vcat];[vcat]ass=/tmp/m1subs.ass:fontsdir=/mnt/c/Windows/Fonts[vout];[1:a]adelay=5870|5870,volume=-6dB[wh];[0:a][wh]amix=inputs=2:duration=first:normalize=0[aout]" -map "[vout]" -map "[aout]" -c:v libx264 -crf 18 -preset slow -r 30 -c:a aac -b:a 192k -ar 48000 -ac 2 "$WK/marco-corte1-REELS-FINAL.mp4"
echo M1-REELS-OK
ffmpeg -nostdin -y -loglevel error -i "$WK/marco-corte2-CORTE.mp4" -vf "ass=/tmp/m2subs.ass:fontsdir=/mnt/c/Windows/Fonts" -c:v libx264 -crf 18 -preset slow -c:a copy "$WK/marco-corte2-REELS-FINAL.mp4"
echo M2-REELS-OK
ffmpeg -nostdin -y -loglevel error -i "$WK/marco-corte1-CORTE.mp4" -i "$WH" -filter_complex "[0:v]trim=0:5.65,setpts=PTS-STARTPTS[va];[0:v]trim=5.65:5.95,setpts=PTS-STARTPTS,zoompan=z='min(1.10,1+0.10*pow(on/8,2))':d=1:x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2':s=1080x1920:fps=30,setsar=1,fade=t=out:st=0.15:d=0.15:c=white[vb];[0:v]trim=5.95,setpts=PTS-STARTPTS,fade=t=in:st=0:d=0.15:c=white[vc];[va][vb][vc]concat=n=3:v=1:a=0[vcat];[vcat]split[b1][f1];[b1]scale=1080:1350:force_original_aspect_ratio=increase,crop=1080:1350,gblur=sigma=30[bg];[f1]scale=-2:1350[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,ass=/tmp/m1li.ass:fontsdir=/mnt/c/Windows/Fonts[vout];[1:a]adelay=5870|5870,volume=-9dB[wh];[0:a][wh]amix=inputs=2:duration=first:normalize=0[aout]" -map "[vout]" -map "[aout]" -c:v libx264 -crf 18 -preset slow -r 30 -c:a aac -b:a 192k -ar 48000 -ac 2 "$WK/marco-corte1-LINKEDIN45-FINAL.mp4"
echo M1-LI45-OK
ffmpeg -nostdin -y -loglevel error -i "$WK/marco-corte2-CORTE.mp4" -filter_complex "[0:v]split[b1][f1];[b1]scale=1080:1350:force_original_aspect_ratio=increase,crop=1080:1350,gblur=sigma=30[bg];[f1]scale=-2:1350[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,ass=/tmp/m2li.ass:fontsdir=/mnt/c/Windows/Fonts[vout]" -map "[vout]" -map 0:a -c:v libx264 -crf 18 -preset slow -c:a copy "$WK/marco-corte2-LINKEDIN45-FINAL.mp4"
echo M2-LI45-OK
for f in marco-corte1-REELS-FINAL marco-corte2-REELS-FINAL marco-corte1-LINKEDIN45-FINAL marco-corte2-LINKEDIN45-FINAL; do
  echo "$f: $(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$WK/$f.mp4")"
done
rm -f /tmp/m1subs.ass /tmp/m2subs.ass /tmp/m1li.ass /tmp/m2li.ass
echo RENDER-DONE
