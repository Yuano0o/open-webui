#!/bin/zsh
set -euo pipefail

read -rs "ANTHROPIC_API_KEY?Anthropic API Key: "
print
if [[ -z "$ANTHROPIC_API_KEY" ]]; then
  print -u2 "API Key cannot be empty."
  exit 1
fi
security add-generic-password \
  -U \
  -a "$USER" \
  -s open-webui-vision-loader \
  -w "$ANTHROPIC_API_KEY" >/dev/null
unset ANTHROPIC_API_KEY
print "Anthropic API Key was stored in macOS Keychain."
