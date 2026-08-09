set -e
SC='/mnt/c/Users/ferna/AppData/Local/Temp/claude/D--Programas-workspaces-vault/2f9d28a7-3e16-4b7f-ae6c-445b2877f0d5/scratchpad'
IN='/mnt/c/Users/ferna/Downloads/IMG_7855.MOV'
ffmpeg -nostdin -y -loglevel error -ss 42 -i "$IN" -frames:v 1 -vf "scale=1080:1920:flags=lanczos,zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p" "$SC/tm-hable.jpg"
ffmpeg -nostdin -y -loglevel error -ss 42 -i "$IN" -frames:v 1 -vf "scale=1080:1920:flags=lanczos,zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=mobius,zscale=t=bt709:m=bt709:r=tv,format=yuv420p" "$SC/tm-mobius.jpg"
echo TM-DONE
