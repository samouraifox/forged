#!/usr/bin/env bash
set -euo pipefail

MODEL="${MODEL:-$HOME/models/NousResearch_Hermes-4-14B-Q6_K.gguf}"
CTX="${CTX:-65536}"
PORT="${PORT:-8080}"
HOST="${HOST:-127.0.0.1}"

if [ ! -f "$MODEL" ]; then
  echo "Model not found at $MODEL" >&2
  exit 1
fi

exec llama-server \
  -m "$MODEL" \
  -c "$CTX" \
  --rope-scaling yarn --yarn-orig-ctx 32768 \
  --cache-type-k q8_0 --cache-type-v q8_0 \
  -ngl 999 \
  --jinja \
  --temp 0.4 \
  --host "$HOST" --port "$PORT"
