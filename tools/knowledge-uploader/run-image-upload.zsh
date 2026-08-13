#!/bin/zsh
# Upload figures/tables from a prepared asset directory into an Open WebUI
# knowledge base, going through a local vision-description pipeline first.
#
# Usage: ./run-image-upload.zsh <source-dir> <knowledge-name-or-id> [--dry-run|--limit N|--only figures|tables]
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
SOURCE="${1:?Usage: $0 <source-dir> <knowledge-name-or-id> [options]}"
KNOWLEDGE="${2:?Usage: $0 <source-dir> <knowledge-name-or-id> [options]}"
shift 2

dry_run=false
for argument in "$@"; do
  if [[ "$argument" == "--dry-run" ]]; then
    dry_run=true
  fi
done

if [[ "$dry_run" == false && -z "${OPEN_WEBUI_API_KEY:-}" ]]; then
  OPEN_WEBUI_API_KEY="$(
    security find-generic-password \
      -a "$USER" \
      -s open-webui-batch-uploader \
      -w 2>/dev/null || true
  )"
  if [[ -z "$OPEN_WEBUI_API_KEY" ]]; then
    print -u2 "Open WebUI API Key is missing. Run:"
    print -u2 "  $SCRIPT_DIR/store-open-webui-api-key.zsh"
    exit 1
  fi
  export OPEN_WEBUI_API_KEY
fi

python3 "$SCRIPT_DIR/batch_upload_images_to_knowledge.py" \
  --source "$SOURCE" \
  --knowledge "$KNOWLEDGE" \
  "$@"
