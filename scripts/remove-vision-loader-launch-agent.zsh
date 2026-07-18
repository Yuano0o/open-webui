#!/bin/zsh
set -euo pipefail

LABEL="com.openwebui.vision-loader"
TARGET="$HOME/Library/LaunchAgents/$LABEL.plist"
DOMAIN="gui/$(id -u)"

launchctl bootout "$DOMAIN/$LABEL" >/dev/null 2>&1 || true
rm -f "$TARGET"
print "Removed $LABEL"
