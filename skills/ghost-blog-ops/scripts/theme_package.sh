#!/usr/bin/env bash
# Validate a Ghost theme folder with gscan and package it as <folder-name>.zip.
# The zip FILE NAME becomes the theme name on upload, so it must equal the
# active theme's name; this script names it after the folder and refuses to
# do otherwise. Usage: bash theme_package.sh <theme-folder> [out-dir]
set -e

THEME_DIR="${1:?usage: theme_package.sh <theme-folder> [out-dir]}"
OUT_DIR="${2:-$(dirname "$THEME_DIR")}"
NAME="$(basename "$THEME_DIR")"
# absolute path: the zip step runs inside the theme folder
ZIP="$(cd "$OUT_DIR" && pwd)/$NAME.zip"

[ -f "$THEME_DIR/package.json" ] || { echo "[fatal] $THEME_DIR has no package.json"; exit 2; }
command -v zip >/dev/null || { echo "[fatal] 'zip' not installed (apt-get install -y zip)"; exit 2; }

PKG_NAME=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1],encoding='utf-8')).get('name',''))" "$THEME_DIR/package.json" 2>/dev/null || true)
if [ -n "$PKG_NAME" ] && [ "$PKG_NAME" != "$NAME" ]; then
  echo "[warn] package.json name '$PKG_NAME' differs from folder '$NAME'; the upload will use the ZIP name '$NAME'"
fi

echo "== gscan (folder)"
npx --yes gscan "$THEME_DIR"

rm -f "$ZIP"                      # zip -r appends to an existing archive
( cd "$THEME_DIR" && zip -qr "$ZIP" . -x "node_modules/*" -x ".git/*" -x "*.zip" )

echo "== gscan (zip, -z is mandatory)"
npx --yes gscan -z "$ZIP"

echo "== ready: $ZIP  (theme name on upload: $NAME)"
