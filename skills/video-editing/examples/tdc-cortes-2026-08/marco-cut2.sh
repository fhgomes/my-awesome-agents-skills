set -e
IN='/mnt/c/Users/ferna/Downloads/VID-20260425-WA0003.mp4'
WK='/mnt/c/Users/ferna/Downloads/marco-eventos-trabalho'
FC='[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=30[bg];[0:v]scale=-2:1920[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2[v]'
mkdir -p /tmp/mwork && cd /tmp/mwork
ffmpeg -nostdin -y -loglevel error -i "$IN" -ss 146.05 -to 152.00 -filter_complex "$FC" -map '[v]' -map 0:a   -c:v libx264 -preset slow -crf 18 -r 30 -c:a aac -b:a 192k -ar 48000 -ac 2 p1.mp4
ffmpeg -nostdin -y -loglevel error -i "$IN" -ss 20.00 -to 30.45 -filter_complex "$FC" -map '[v]' -map 0:a   -c:v libx264 -preset slow -crf 18 -r 30 -c:a aac -b:a 192k -ar 48000 -ac 2 p2.mp4
ffmpeg -nostdin -y -loglevel error -i "$IN" -ss 52.24 -to 63.70 -filter_complex "$FC" -map '[v]' -map 0:a   -c:v libx264 -preset slow -crf 18 -r 30 -c:a aac -b:a 192k -ar 48000 -ac 2 p3.mp4
ffmpeg -nostdin -y -loglevel error -i "$IN" -ss 76.30 -to 134.20 -filter_complex "$FC" -map '[v]' -map 0:a   -c:v libx264 -preset slow -crf 18 -r 30 -c:a aac -b:a 192k -ar 48000 -ac 2 p4.mp4
ffmpeg -nostdin -y -loglevel error -i "$IN" -ss 209.50 -to 216.40 -af 'afade=t=out:st=6.65:d=0.25' -filter_complex "$FC" -map '[v]' -map 0:a   -c:v libx264 -preset slow -crf 18 -r 30 -c:a aac -b:a 192k -ar 48000 -ac 2 p5.mp4
printf "file 'p1.mp4'
file 'p2.mp4'
file 'p3.mp4'
file 'p4.mp4'
file 'p5.mp4'
" > m1.txt
ffmpeg -nostdin -y -loglevel error -f concat -safe 0 -i m1.txt -c copy "$WK/marco-corte1-CORTE.mp4"
ffmpeg -nostdin -y -loglevel error -i "$IN" -ss 20.00 -to 30.45 -filter_complex "$FC" -map '[v]' -map 0:a   -c:v libx264 -preset slow -crf 18 -r 30 -c:a aac -b:a 192k -ar 48000 -ac 2 q0.mp4
ffmpeg -nostdin -y -loglevel error -i "$IN" -ss 134.50 -to 168.28 -filter_complex "$FC" -map '[v]' -map 0:a   -c:v libx264 -preset slow -crf 18 -r 30 -c:a aac -b:a 192k -ar 48000 -ac 2 q1.mp4
ffmpeg -nostdin -y -loglevel error -i "$IN" -ss 209.50 -to 216.40 -af 'afade=t=out:st=6.65:d=0.25' -filter_complex "$FC" -map '[v]' -map 0:a   -c:v libx264 -preset slow -crf 18 -r 30 -c:a aac -b:a 192k -ar 48000 -ac 2 q2.mp4
printf "file 'q0.mp4'
file 'q1.mp4'
file 'q2.mp4'
" > m2.txt
ffmpeg -nostdin -y -loglevel error -f concat -safe 0 -i m2.txt -c copy "$WK/marco-corte2-CORTE.mp4"
echo "m1: $(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$WK/marco-corte1-CORTE.mp4")"
echo "m2: $(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$WK/marco-corte2-CORTE.mp4")"
rm -rf /tmp/mwork
echo CUT-DONE
