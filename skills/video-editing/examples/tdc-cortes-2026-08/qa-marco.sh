set -e
WK='/mnt/c/Users/ferna/Downloads/marco-eventos-trabalho'
SC='/mnt/c/Users/ferna/AppData/Local/Temp/claude/D--Programas-workspaces-vault/2f9d28a7-3e16-4b7f-ae6c-445b2877f0d5/scratchpad'
ffmpeg -nostdin -y -loglevel error -ss 2  -i "$WK/marco-corte1-REELS-FINAL.mp4" -frames:v 1 "$SC/qa-m1-hook.jpg"
ffmpeg -nostdin -y -loglevel error -ss 10 -i "$WK/marco-corte1-REELS-FINAL.mp4" -frames:v 1 "$SC/qa-m1-quest.jpg"
ffmpeg -nostdin -y -loglevel error -ss 12 -i "$WK/marco-corte2-REELS-FINAL.mp4" -frames:v 1 "$SC/qa-m2-body.jpg"
echo QA-MARCO-DONE
