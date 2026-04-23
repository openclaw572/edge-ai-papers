#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

PAPER_MODE="${PAPER_MODE:-review}"
if [[ "$PAPER_MODE" != "review" && "$PAPER_MODE" != "general" ]]; then
  echo "Invalid PAPER_MODE: $PAPER_MODE (expected: review or general)" >&2
  exit 1
fi

RUN_DATE="${RUN_DATE:-$(date +%F)}"
WORKSPACE="${WORKSPACE:-/tmp/edge-ai-pipeline-$RUN_DATE}"
MAX_PARALLEL="${MAX_PARALLEL:-2}"
SKIP_YOUTUBE="${SKIP_YOUTUBE:-0}"
SKIP_PUSH="${SKIP_PUSH:-0}"

cmd=(python3 scripts/run_notebooklm_pipeline.py --mode "$PAPER_MODE" --run-date "$RUN_DATE" --workspace "$WORKSPACE" --max-parallel "$MAX_PARALLEL")

if [[ "$SKIP_YOUTUBE" == "1" ]]; then
  cmd+=(--skip-youtube)
fi
if [[ "$SKIP_PUSH" == "1" ]]; then
  cmd+=(--skip-push)
fi

printf 'Running scheduled pipeline with PAPER_MODE=%s RUN_DATE=%s\n' "$PAPER_MODE" "$RUN_DATE"
exec "${cmd[@]}"
