#!/bin/zsh
set -euo pipefail

read -rs "OPEN_WEBUI_API_KEY?Open WebUI API Key: "
print
if [[ -z "$OPEN_WEBUI_API_KEY" ]]; then
  print -u2 "API Key cannot be empty."
  exit 1
fi
security add-generic-password \
  -U \
  -a "$USER" \
  -s open-webui-batch-uploader \
  -w "$OPEN_WEBUI_API_KEY" >/dev/null
unset OPEN_WEBUI_API_KEY
print "Open WebUI API Key was stored in macOS Keychain."
