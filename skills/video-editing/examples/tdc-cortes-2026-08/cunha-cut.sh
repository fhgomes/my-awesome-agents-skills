set -e
IN='/mnt/c/Users/ferna/Downloads/VID_20260723_095828.mp4'
WK='/mnt/c/Users/ferna/Downloads/cunha-mercado-trabalho'
mkdir -p /tmp/cwork && cd /tmp/cwork
ffmpeg -nostdin -y -loglevel error -i "$IN" -ss 46.00 -to 49.60   -c:v libx264 -preset slow -crf 18 -r 30 -c:a aac -b:a 192k -ar 48000 -ac 2 c1p1.mp4
ffmpeg -nostdin -y -loglevel error -i "$IN" -ss 4.65 -to 73.80   -c:v libx264 -preset slow -crf 18 -r 30 -c:a aac -b:a 192k -ar 48000 -ac 2 c1p2.mp4
printf "file 'c1p1.mp4'
file 'c1p2.mp4'
" > c1.txt
ffmpeg -nostdin -y -loglevel error -f concat -safe 0 -i c1.txt -c copy "$WK/cunha-corte1-CORTE.mp4"
ffmpeg -nostdin -y -loglevel error -i "$IN" -ss 4.65 -to 14.83   -c:v libx264 -preset slow -crf 18 -r 30 -c:a aac -b:a 192k -ar 48000 -ac 2 c2p0.mp4
ffmpeg -nostdin -y -loglevel error -i "$IN" -ss 73.95 -to 82.85   -c:v libx264 -preset slow -crf 18 -r 30 -c:a aac -b:a 192k -ar 48000 -ac 2 c2p1.mp4
ffmpeg -nostdin -y -loglevel error -i "$IN" -ss 84.05 -to 111.30 -af 'afade=t=out:st=27.00:d=0.25'   -c:v libx264 -preset slow -crf 18 -r 30 -c:a aac -b:a 192k -ar 48000 -ac 2 c2p2.mp4
printf "file 'c2p0.mp4'
file 'c2p1.mp4'
file 'c2p2.mp4'
" > c2.txt
ffmpeg -nostdin -y -loglevel error -f concat -safe 0 -i c2.txt -c copy "$WK/cunha-corte2-CORTE.mp4"
echo "c1: $(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$WK/cunha-corte1-CORTE.mp4")"
echo "c2: $(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$WK/cunha-corte2-CORTE.mp4")"
rm -rf /tmp/cwork
echo CUT-DONE
