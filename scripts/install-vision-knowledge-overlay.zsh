#!/bin/zsh
set -euo pipefail

REPO_ROOT="${0:A:h:h}"
APP_SUPPORT="$HOME/Library/Application Support/open-webui"
PYTHON="$APP_SUPPORT/python/bin/python"
BACKUP_ROOT="$APP_SUPPORT/vision-knowledge-backups/$(date +%Y%m%d-%H%M%S)"
SERVICE_TARGET="$APP_SUPPORT/vision-loader"

if [[ ! -x "$PYTHON" ]]; then
  print -u2 "Open WebUI Desktop Python runtime was not found."
  exit 1
fi
SITE_PACKAGES="$($PYTHON -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')"
RUNTIME="$SITE_PACKAGES/open_webui"
if [[ ! -d "$RUNTIME" ]]; then
  print -u2 "Open WebUI Desktop package was not found: $RUNTIME"
  exit 1
fi

VERSION="$($PYTHON -c "import importlib.metadata; print(importlib.metadata.version('open-webui'))")"
if [[ "$VERSION" != "0.10.2" ]]; then
  print -u2 "Refusing to patch Open WebUI $VERSION; this overlay targets 0.10.2."
  exit 1
fi
mkdir -p "$BACKUP_ROOT/original" "$BACKUP_ROOT/created"
for relative in \
  routers/files.py \
  routers/retrieval.py \
  utils/middleware.py \
  retrieval/utils.py \
  retrieval/source_identity.py \
  retrieval/loaders/image_vision.py \
  retrieval/vision.py; do
  source_file="$RUNTIME/$relative"
  if [[ -e "$source_file" ]]; then
    mkdir -p "$BACKUP_ROOT/original/${relative:h}"
    cp -p "$source_file" "$BACKUP_ROOT/original/$relative"
  else
    mkdir -p "$BACKUP_ROOT/created/${relative:h}"
    : > "$BACKUP_ROOT/created/$relative"
  fi
done

if [[ -d "$SERVICE_TARGET" ]]; then
  cp -R "$SERVICE_TARGET" "$BACKUP_ROOT/vision-loader"
fi

mkdir -p "$RUNTIME/retrieval/loaders"
cp -p "$REPO_ROOT/backend/open_webui/routers/files.py" "$RUNTIME/routers/files.py"
cp -p "$REPO_ROOT/backend/open_webui/routers/retrieval.py" "$RUNTIME/routers/retrieval.py"
cp -p "$REPO_ROOT/backend/open_webui/utils/middleware.py" "$RUNTIME/utils/middleware.py"
cp -p "$REPO_ROOT/backend/open_webui/retrieval/utils.py" "$RUNTIME/retrieval/utils.py"
cp -p "$REPO_ROOT/backend/open_webui/retrieval/source_identity.py" \
  "$RUNTIME/retrieval/source_identity.py"
cp -p "$REPO_ROOT/backend/open_webui/retrieval/loaders/image_vision.py" "$RUNTIME/retrieval/loaders/image_vision.py"
cp -p "$REPO_ROOT/backend/open_webui/retrieval/vision.py" "$RUNTIME/retrieval/vision.py"

rm -rf "$SERVICE_TARGET"
mkdir -p "$SERVICE_TARGET"
cp -R "$REPO_ROOT/services/image-vision-loader/src" "$SERVICE_TARGET/src"
cp -p "$REPO_ROOT/services/image-vision-loader/run-local.zsh" "$SERVICE_TARGET/run-local.zsh"
cp -p "$REPO_ROOT/services/image-vision-loader/store-key-in-keychain.zsh" \
  "$SERVICE_TARGET/store-key-in-keychain.zsh"
chmod 700 "$SERVICE_TARGET/run-local.zsh" "$SERVICE_TARGET/store-key-in-keychain.zsh"

print -r -- "$BACKUP_ROOT" > "$APP_SUPPORT/vision-knowledge-current-backup"
print "Overlay installed for Open WebUI $VERSION"
print "Backup: $BACKUP_ROOT"
print "Vision loader: $SERVICE_TARGET/run-local.zsh"
