#!/usr/bin/env bash
# Supervisor for stage 02. The MLX process is occasionally killed mid-run on
# this machine; stage 02 checkpoints, so retrying simply resumes.
set -u
WORK="$1"; PY="${2:-./venv/bin/python}"; MAX="${3:-30}"
for i in $(seq 1 "$MAX"); do
  if [ -f "$WORK/langmap.json" ] && [ "$WORK/langmap.json" -nt "$WORK/vad.json" ]; then
    echo "langmap.json complete after $((i-1)) attempt(s)"; exit 0
  fi
  echo "=== attempt $i ==="
  "$PY" -u youtube/bilingual_cut/02_langid.py --work "$WORK" \
      --checkpoint-every 40 --batch 16 2>&1 \
    | grep -v "frames/s\|Fetching\|resource_tracker\|warnings.warn"
  sleep 2
done
echo "gave up after $MAX attempts"; exit 1
