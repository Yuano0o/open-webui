#!/bin/zsh
set -euo pipefail

REPO_ROOT="${0:A:h:h}"
LABEL="com.openwebui.vision-loader"
SOURCE="$REPO_ROOT/services/image-vision-loader/$LABEL.plist"
TARGET="$HOME/Library/LaunchAgents/$LABEL.plist"
DOMAIN="gui/$(id -u)"

mkdir -p "$HOME/Library/LaunchAgents"
if [[ -f "$TARGET" ]]; then
  cp -p "$TARGET" "$TARGET.backup.$(date +%Y%m%d-%H%M%S)"
fi
sed "s|__HOME__|$HOME|g" "$SOURCE" > "$TARGET"
plutil -lint "$TARGET" >/dev/null
launchctl bootout "$DOMAIN/$LABEL" >/dev/null 2>&1 || true
launchctl bootstrap "$DOMAIN" "$TARGET"
launchctl kickstart -k "$DOMAIN/$LABEL"
print "Installed and started $LABEL"
print "LaunchAgent: $TARGET"
