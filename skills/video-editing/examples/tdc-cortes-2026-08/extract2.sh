set -e
SC='/mnt/c/Users/ferna/AppData/Local/Temp/claude/D--Programas-workspaces-vault/2f9d28a7-3e16-4b7f-ae6c-445b2877f0d5/scratchpad'
C='/mnt/c/Users/ferna/Downloads/VID_20260723_095828.mp4'
M='/mnt/c/Users/ferna/Downloads/VID-20260425-WA0003.mp4'
ffprobe -v error -show_format -show_streams -of json "$C" > "$SC/cunha-probe.json"
ffprobe -v error -show_format -show_streams -of json "$M" > "$SC/marco-probe.json"
ffmpeg -nostdin -y -loglevel error -i "$C" -vn -ac 1 -ar 16000 -c:a pcm_s16le "$SC/cunha-16k.wav"
ffmpeg -nostdin -y -loglevel error -i "$M" -vn -ac 1 -ar 16000 -c:a pcm_s16le "$SC/marco-16k.wav"
ffmpeg -nostdin -y -loglevel error -ss 30 -i "$C" -frames:v 1 "$SC/cunha-t30.jpg"
ffmpeg -nostdin -y -loglevel error -ss 30 -i "$M" -frames:v 1 "$SC/marco-t30.jpg"
echo EXTRACT2-DONE
