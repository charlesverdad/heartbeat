#!/bin/bash
# Weekly sermon-to-blog automation
# Runs every Sunday at 8pm Sydney time via crontab
# Finds the latest Heartbeat Church sermon, transcribes it, generates a blog post,
# and publishes as a Ghost draft.

set -euo pipefail

REPO_DIR="/Users/charles/work/heartbeat"
LOG_DIR="$REPO_DIR/logs"
LOG_FILE="$LOG_DIR/sermon-blog-$(date +%Y-%m-%d).log"

mkdir -p "$LOG_DIR"

echo "=== Sermon-to-blog run: $(date) ===" >> "$LOG_FILE"

# Load environment (Ghost API keys, etc.)
set -a
source "$REPO_DIR/.env"
set +a

# Run claude with the sermon-to-blog prompt
/Users/charles/.local/bin/claude -p \
  --allowedTools 'Bash,Read,Write,Edit,Glob,Grep,Agent,Skill' \
  "Run /sermon-to-blog latest" \
  2>&1 | tee -a "$LOG_FILE"

echo "=== Finished: $(date) ===" >> "$LOG_FILE"
