#!/bin/bash
# Edge AI Paper Research Automation Script
# Runs every 3 days to search and generate paper reports

set -e

WORKSPACE="/home/aaron/.openclaw/workspace"
cd "$WORKSPACE"

echo "=== Edge AI Paper Research Started ==="
echo "Date: $(date)"

# Create daily memory log
TODAY=$(date +%Y-%m-%d)
MEMORY_FILE="$WORKSPACE/memory/$TODAY.md"

if [ ! -f "$MEMORY_FILE" ]; then
  echo "# Daily Memory - $TODAY" > "$MEMORY_FILE"
  echo "" >> "$MEMORY_FILE"
fi

# Run paper researcher skill via OpenClaw
echo "Starting paper research..."
openclaw exec "Use paper-researcher skill to find 2 papers (1 Edge AI, 1 Edge AI Security), generate reports, update website, and push to GitHub" >> "$MEMORY_FILE" 2>&1

# Notify completion
echo "Paper research completed successfully!"
echo "=== Edge AI Paper Research Finished ==="
