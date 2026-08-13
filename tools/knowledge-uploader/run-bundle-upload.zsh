#!/bin/zsh
# Upload a prepared Markdown/CSV knowledge bundle into an Open WebUI
# knowledge base (text only; images are handled by run-image-upload.zsh).
#
# Usage: ./run-bundle-upload.zsh <source-dir> <knowledge-name-or-id> [--dry-run|--retries N|--retry-delay SECONDS]
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
SOURCE="${1:?Usage: $0 <source-dir> <knowledge-name-or-id> [options]}"
KNOWLEDGE="${2:?Usage: $0 <source-dir> <knowledge-name-or-id> [options]}"
shift 2

if [[ " $* " != *" --dry-run "* && -z "${OPEN_WEBUI_API_KEY:-}" ]]; then
  OPEN_WEBUI_API_KEY="$(security find-generic-password -a "$USER" -s open-webui-batch-uploader -w 2>/dev/null || true)"
  if [[ -z "$OPEN_WEBUI_API_KEY" ]]; then
    print -u2 "Open WebUI API Key is missing. Run:"
    print -u2 "  $SCRIPT_DIR/store-open-webui-api-key.zsh"
    exit 1
  fi
  export OPEN_WEBUI_API_KEY
fi

python3 "$SCRIPT_DIR/batch_upload_knowledge_bundle.py" \
  --source "$SOURCE" \
  --knowledge "$KNOWLEDGE" \
  "$@"
