#!/bin/bash
#
# backup-vm.sh - Full backup of HB-Pulse (v1) from vm1, run from your Mac.
#
# Pulls a pg_dump of the pulse database and a tarball of /data/hb-pulse/uploads
# over SSH. Read-only on the VM. Optional: the API backup (bin/pulse-v1-backup.mjs)
# is the main path; this adds the full DB (users, ACLs, history) and image files.
# HOST defaults to the tunnel name; set HOST=vmadmin@<public ip> and SSH_KEY to go direct.
#
# Usage: manifests/hb-pulse/backup-vm.sh [outDir]
# Default outDir: backups/pulse-v1/vm-<timestamp> (gitignored).

set -euo pipefail

HOST="${HOST:-vm1.heartbeatchurch.com.au}"
SSH_OPTS=(${SSH_KEY:+-i "$SSH_KEY"})
ssh() { command ssh ${SSH_OPTS[@]+"${SSH_OPTS[@]}"} "$@"; }
OUT="${1:-backups/pulse-v1/vm-$(date +%Y%m%d-%H%M%S)}"
mkdir -p "$OUT"

echo "Dumping database..."
ssh "$HOST" 'docker exec pulse-db pg_dump -U pulse -Fc pulse' > "$OUT/pulse.dump"

echo "Dumping database (plain SQL, for reading)..."
ssh "$HOST" 'docker exec pulse-db pg_dump -U pulse pulse' | gzip > "$OUT/pulse.sql.gz"

echo "Archiving uploads..."
ssh "$HOST" 'sudo tar -C /data/hb-pulse -czf - uploads' > "$OUT/uploads.tar.gz"

echo "Recording app version..."
ssh "$HOST" 'docker inspect pulse --format "{{.Config.Image}}"' > "$OUT/image.txt"

# Sanity checks: count tables with data and archived files.
gunzip -c "$OUT/pulse.sql.gz" | grep -c "^COPY public\." | xargs echo "tables with data:" || true
tar -tzf "$OUT/uploads.tar.gz" | grep -vc '/$' | xargs echo "upload files:" || true
ls -lh "$OUT"
