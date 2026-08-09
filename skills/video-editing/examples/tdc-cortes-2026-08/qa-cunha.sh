set -e
WK='/mnt/c/Users/ferna/Downloads/cunha-mercado-trabalho'
SC='/mnt/c/Users/ferna/AppData/Local/Temp/claude/D--Programas-workspaces-vault/2f9d28a7-3e16-4b7f-ae6c-445b2877f0d5/scratchpad'
ffmpeg -nostdin -y -loglevel error -ss 1.5  -i "$WK/cunha-corte1-REELS-FINAL.mp4" -frames:v 1 "$SC/qa-c1-hook.jpg"
ffmpeg -nostdin -y -loglevel error -ss 3.55 -i "$WK/cunha-corte1-REELS-FINAL.mp4" -frames:v 1 "$SC/qa-c1-flash.jpg"
ffmpeg -nostdin -y -loglevel error -ss 8.0  -i "$WK/cunha-corte1-REELS-FINAL.mp4" -frames:v 1 "$SC/qa-c1-quest.jpg"
ffmpeg -nostdin -y -loglevel error -ss 40.0 -i "$WK/cunha-corte1-REELS-FINAL.mp4" -frames:v 1 "$SC/qa-c1-body.jpg"
ffmpeg -nostdin -y -loglevel error -ss 8.0  -i "$WK/cunha-corte1-LINKEDIN-FINAL.mp4" -frames:v 1 "$SC/qa-c1-li.jpg"
ffmpeg -nostdin -y -loglevel error -ss 5.0  -i "$WK/cunha-corte2-REELS-FINAL.mp4" -frames:v 1 "$SC/qa-c2-body.jpg"
echo QA-CUNHA-DONE
