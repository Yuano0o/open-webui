#!/bin/zsh
set -euo pipefail

SERVICE_DIR="${0:A:h}"
PYTHON="${OPEN_WEBUI_PYTHON:-$HOME/Library/Application Support/open-webui/python/bin/python}"

if [[ ! -x "$PYTHON" ]]; then
  print -u2 "Open WebUI Python was not found: $PYTHON"
  exit 1
fi

if [[ -z "${OPEN_WEBUI_API_KEY:-}" ]]; then
  OPEN_WEBUI_API_KEY="$(
    security find-generic-password \
      -a "$USER" \
      -s open-webui-batch-uploader \
      -w 2>/dev/null || true
  )"
fi
if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
  ANTHROPIC_API_KEY="$(security find-generic-password -a "$USER" -s open-webui-vision-loader -w 2>/dev/null || true)"
fi
if [[ -z "${ANTHROPIC_API_KEY:-}" && -z "$OPEN_WEBUI_API_KEY" ]]; then
  print -u2 "Neither an Open WebUI nor Anthropic API key is available."
  exit 1
fi

export OPEN_WEBUI_API_KEY
export ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}"
export PYTHONPATH="$SERVICE_DIR/src${PYTHONPATH:+:$PYTHONPATH}"
exec "$PYTHON" -m uvicorn image_vision_loader.main:app --host 127.0.0.1 --port "${PORT:-8765}"
