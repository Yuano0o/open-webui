#!/bin/zsh
set -euo pipefail

APP_SUPPORT="$HOME/Library/Application Support/open-webui"
PYTHON="$APP_SUPPORT/python/bin/python"
BACKUP_ROOT="${1:-}"

launchctl bootout "gui/$(id -u)/com.openwebui.vision-loader" >/dev/null 2>&1 || true
rm -f "$HOME/Library/LaunchAgents/com.openwebui.vision-loader.plist"

if [[ ! -x "$PYTHON" ]]; then
  print -u2 "Open WebUI Desktop Python runtime was not found."
  exit 1
fi
SITE_PACKAGES="$($PYTHON -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')"
RUNTIME="$SITE_PACKAGES/open_webui"

if [[ -z "$BACKUP_ROOT" && -f "$APP_SUPPORT/vision-knowledge-current-backup" ]]; then
  BACKUP_ROOT="$(<"$APP_SUPPORT/vision-knowledge-current-backup")"
fi
if [[ -z "$BACKUP_ROOT" || ! -d "$BACKUP_ROOT" ]]; then
  print -u2 "Usage: $0 /path/to/vision-knowledge-backup"
  exit 1
fi

if [[ -d "$BACKUP_ROOT/original" ]]; then
  while IFS= read -r original; do
    relative="${original#$BACKUP_ROOT/original/}"
    mkdir -p "$RUNTIME/${relative:h}"
    cp -p "$original" "$RUNTIME/$relative"
  done < <(find "$BACKUP_ROOT/original" -type f -print)
fi
if [[ -d "$BACKUP_ROOT/created" ]]; then
  while IFS= read -r marker; do
    relative="${marker#$BACKUP_ROOT/created/}"
    rm -f "$RUNTIME/$relative"
  done < <(find "$BACKUP_ROOT/created" -type f -print)
fi

rm -rf "$APP_SUPPORT/vision-loader"
if [[ -d "$BACKUP_ROOT/vision-loader" ]]; then
  cp -R "$BACKUP_ROOT/vision-loader" "$APP_SUPPORT/vision-loader"
fi
print "Restored Open WebUI runtime from: $BACKUP_ROOT"
print "The backup itself was not deleted."
