#!/usr/bin/env bash
# Write a Ghost SEO setting straight into MySQL, then restart Ghost so the in-memory cache reloads.
# Needed because Ghost integration tokens cannot write /settings/ or /custom_theme_settings/
# (Ghost 6 answers 403 NoPermissionError; Ghost 5 NotImplementedError).
#
#   ghost-setting.sh site   <key> <value>            # settings table, SEO keys only (see SITE_KEYS)
#   ghost-setting.sh custom <key> <value> [theme]    # custom_theme_settings (theme defaults to the active one)
#   ghost-setting.sh show   <key>                    # current value (settings only for SEO keys)
#
# Environment:
#   GHOST_MYSQL_CONTAINER (default ghost-db)   GHOST_CONTAINER (default ghost)   GHOST_DB (default ghost)
#   GHOST_DB_USER (default root; prefer the ghost app user, it already owns the ghost database)
#   GHOST_URL (default https://localhost, used to wait for the restart; -k only for localhost)
#   MYSQL_PWD or MYSQL_PWD_FILE: host-side password, only if the container lacks MYSQL_ROOT_PASSWORD in its env
#   DRY_RUN=1 prints the SQL instead of running it; nothing is written, nothing restarts
# Safety: the `settings` table also holds secrets (Stripe, members, email). `site`/`show` accept only the
# SEO allowlist; any key that looks like a credential is refused in every mode. Values go in as hex
# literals (no escaping, independent of sql_mode); theme names are validated. The previous value is
# appended to $GHOST_SETTINGS_BACKUP (default ~/ghost-settings-backup.tsv, created 0600) before each write.
set -euo pipefail
umask 077

MODE=${1:-}; KEY=${2:-}; VAL=${3:-}
MYSQLC=${GHOST_MYSQL_CONTAINER:-ghost-db}; GHOSTC=${GHOST_CONTAINER:-ghost}; DB=${GHOST_DB:-ghost}
DBUSER=${GHOST_DB_USER:-root}
BACKUP=${GHOST_SETTINGS_BACKUP:-$HOME/ghost-settings-backup.tsv}
URL=${GHOST_URL:-https://localhost}
DRY=${DRY_RUN:-0}
HOST_PW=${MYSQL_PWD:-}
[ -n "$HOST_PW" ] || [ -z "${MYSQL_PWD_FILE:-}" ] || HOST_PW=$(<"$MYSQL_PWD_FILE")
SITE_KEYS='^(title|description|meta_title|meta_description|og_title|og_description|og_image|twitter_title|twitter_description|twitter_image|cover_image|icon|logo)$'

[ -n "$MODE" ] && [ -n "$KEY" ] || { sed -n 2,19p "$0"; exit 2; }
[[ "$KEY" =~ ^[a-z0-9_]+$ ]] || { echo "key must match ^[a-z0-9_]+$"; exit 2; }
[[ "$KEY" =~ (secret|private|password|token|hash|session|api_key) ]] && { echo "refusing: '$KEY' looks like a credential"; exit 2; }

sql() {
  if [ "$DRY" = 1 ]; then echo "SQL>> $(cat)" >&2; echo 1; return; fi
  if [ -n "$HOST_PW" ]; then
    MYSQL_PWD="$HOST_PW" docker exec -i -e MYSQL_PWD "$MYSQLC" mysql -u "$DBUSER" -N "$DB"   # -e NAME inherits, never on argv
  else
    docker exec -i "$MYSQLC" sh -c 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysql -u "$0" -N "$1"' "$DBUSER" "$DB"
  fi
}
hex() { printf '%s' "$1" | od -An -v -tx1 | tr -d ' \n'; }

if [ "$MODE" = show ]; then
  if [[ "$KEY" =~ $SITE_KEYS ]]; then
    echo "settings.$KEY = $(echo "SELECT \`value\` FROM settings WHERE \`key\`='$KEY';" | sql)"
  else
    echo "settings.$KEY = (not an SEO key, not shown)"
  fi
  echo "custom_theme_settings.$KEY = $(echo "SELECT CONCAT(theme,' : ',IFNULL(\`value\`,'NULL')) FROM custom_theme_settings WHERE \`key\`='$KEY';" | sql)"
  exit 0
fi

# value format checks for the keys this skill installs (empty is always allowed = feature off)
case "$KEY" in
  ga4_measurement_id)  [[ -z "$VAL" || "$VAL" =~ ^G-[A-Z0-9]{6,12}$ ]] || { echo "ga4 id must look like G-XXXXXXXXXX"; exit 2; } ;;
  meta_pixel_id)       [[ -z "$VAL" || "$VAL" =~ ^[0-9]{6,20}$ ]] || { echo "pixel id must be numeric"; exit 2; } ;;
  *_site_verification|facebook_domain_verification)
                       [[ -z "$VAL" || "$VAL" =~ ^[A-Za-z0-9_=-]{8,120}$ ]] || { echo "verification code has unexpected characters"; exit 2; } ;;
  cover_image|og_image|twitter_image|icon)
                       [[ -z "$VAL" || "$VAL" =~ ^https?://[^[:space:]\'\"]+$ ]] || { echo "$KEY must be an http(s) URL"; exit 2; } ;;
esac
if [ -z "$VAL" ]; then V="''"; else V="CONVERT(UNHEX('$(hex "$VAL")') USING utf8mb4)"; fi

case "$MODE" in
  site)
    [[ "$KEY" =~ $SITE_KEYS ]] || { echo "refusing: settings.$KEY is outside the SEO allowlist (edit SITE_KEYS on purpose)"; exit 2; }
    OLD=$(echo "SELECT \`value\` FROM settings WHERE \`key\`='$KEY';" | sql)
    printf '%s\tsettings\t%s\t%s\n' "$(date -Is)" "$KEY" "$OLD" >> "$BACKUP"
    N=$(echo "UPDATE settings SET \`value\`=$V, updated_at=NOW() WHERE \`key\`='$KEY'; SELECT ROW_COUNT();" | sql)
    ;;
  custom)
    THEME=${4:-$(echo 'SELECT `value` FROM settings WHERE `key`="active_theme";' | sql)}
    [[ "$THEME" =~ ^[A-Za-z0-9._-]+$ ]] || { echo "theme must match ^[A-Za-z0-9._-]+$"; exit 2; }
    OLD=$(echo "SELECT IFNULL(\`value\`,'NULL') FROM custom_theme_settings WHERE \`key\`='$KEY' AND theme='$THEME';" | sql)
    printf '%s\tcustom_theme_settings/%s\t%s\t%s\n' "$(date -Is)" "$THEME" "$KEY" "$OLD" >> "$BACKUP"
    N=$(echo "UPDATE custom_theme_settings SET \`value\`=$V WHERE \`key\`='$KEY' AND theme='$THEME'; SELECT ROW_COUNT();" | sql)
    ;;
  *) echo "mode must be site | custom | show"; exit 2;;
esac

[ "$DRY" = 1 ] && { echo "dry run: nothing written, nothing restarted"; exit 0; }
N=$(printf '%s' "$N" | tail -n1)
[ "${N:-0}" = 1 ] || { echo "UPDATE touched ${N:-0} rows (key or theme wrong?); NOT restarting Ghost"; exit 1; }
echo "previous value saved to $BACKUP; restarting $GHOSTC so the settings cache reloads"
docker restart "$GHOSTC" >/dev/null
K=(); case "$URL" in *localhost*|*127.0.0.1*) K=(-k);; esac
for i in $(seq 1 40); do sleep 1; curl -sf "${K[@]}" -o /dev/null "$URL/" && { echo "up after ${i}s"; exit 0; }; done
echo "Ghost did not answer within 40s; check: docker logs --tail 50 $GHOSTC"; exit 1
