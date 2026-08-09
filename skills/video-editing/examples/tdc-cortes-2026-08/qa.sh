set -e
WK='/mnt/c/Users/ferna/Downloads/ianka-ingles-trabalho'
SC='/mnt/c/Users/ferna/AppData/Local/Temp/claude/D--Programas-workspaces-vault/2f9d28a7-3e16-4b7f-ae6c-445b2877f0d5/scratchpad'
R="$WK/ianka-ingles-REELS-FINAL.mp4"
L="$WK/ianka-ingles-LINKEDIN-FINAL.mp4"
ffmpeg -nostdin -y -loglevel error -ss 1.0  -i "$R" -frames:v 1 "$SC/qa-r-1.jpg"
ffmpeg -nostdin -y -loglevel error -ss 5.18 -i "$R" -frames:v 1 "$SC/qa-r-flash.jpg"
ffmpeg -nostdin -y -loglevel error -ss 5.05 -i "$R" -frames:v 1 "$SC/qa-r-zoom.jpg"
ffmpeg -nostdin -y -loglevel error -ss 6.0  -i "$R" -frames:v 1 "$SC/qa-r-body.jpg"
ffmpeg -nostdin -y -loglevel error -ss 34.8 -i "$R" -frames:v 1 "$SC/qa-r-end.jpg"
ffmpeg -nostdin -y -loglevel error -ss 20.0 -i "$L" -frames:v 1 "$SC/qa-l-body.jpg"
ffmpeg -nostdin -y -loglevel error -ss 5.18 -i "$L" -frames:v 1 "$SC/qa-l-flash.jpg"
ffmpeg -nostdin -y -loglevel error -ss 4.5 -to 6.0 -i "$R" -filter_complex "[0:a]showspectrumpic=s=800x400:legend=1[o]" -map "[o]" -frames:v 1 "$SC/qa-r-spectrum.png"
echo QA-DONE
