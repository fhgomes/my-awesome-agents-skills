set -e
IN='/mnt/c/Users/ferna/Downloads/IMG_7855.MOV'
WK='/mnt/c/Users/ferna/Downloads/ianka-ingles-trabalho'
TM='scale=1080:1920:flags=lanczos,zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p'
mkdir -p /tmp/iwork && cd /tmp/iwork

ffmpeg -nostdin -y -loglevel error -i "$IN" -ss 41.40 -to 46.65 -vf "$TM" \
  -c:v libx264 -preset slow -crf 18 -r 30 \
  -c:a aac -b:a 192k -ar 48000 -ac 2 p1.mp4
echo P1-OK
ffmpeg -nostdin -y -loglevel error -i "$IN" -ss 14.42 -to 55.66 -vf "$TM" \
  -c:v libx264 -preset slow -crf 18 -r 30 \
  -c:a aac -b:a 192k -ar 48000 -ac 2 p2.mp4
echo P2-OK

printf "file 'p1.mp4'\nfile 'p2.mp4'\n" > concat.txt
ffmpeg -nostdin -y -loglevel error -f concat -safe 0 -i concat.txt -c copy "$WK/ianka-ingles-CORTE.mp4"
ffprobe -v error -show_entries format=duration -of default=nw=1 "$WK/ianka-ingles-CORTE.mp4"
echo "zoompan-vars: $(ffmpeg -hide_banner -h filter=zoompan 2>/dev/null | grep -ci in_time)"
rm -rf /tmp/iwork
echo CUT-DONE
