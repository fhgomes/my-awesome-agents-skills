set -e
IN1='/mnt/c/Users/ferna/Downloads/IMG_7855.MOV'
IN2='/mnt/c/Users/ferna/Downloads/IMG_7855 (2).MOV'
SC='/mnt/c/Users/ferna/AppData/Local/Temp/claude/D--Programas-workspaces-vault/2f9d28a7-3e16-4b7f-ae6c-445b2877f0d5/scratchpad'
ffprobe -v error -show_format -show_streams -of json "$IN1" > "$SC/probe1.json"
ffprobe -v error -show_format -show_streams -of json "$IN2" > "$SC/probe2.json"
ffmpeg -nostdin -y -loglevel error -ss 5 -i "$IN1" -frames:v 1 "$SC/file1-t5.jpg"
ffmpeg -nostdin -y -loglevel error -ss 42 -i "$IN1" -frames:v 1 "$SC/file1-t42.jpg"
ffmpeg -nostdin -y -loglevel error -ss 5 -i "$IN2" -frames:v 1 "$SC/file2-t5.jpg"
echo PROBE-DONE
