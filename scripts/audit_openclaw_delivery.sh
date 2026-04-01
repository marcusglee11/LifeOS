#!/usr/bin/env bash
# Audit OpenClaw cron jobs for unsafe message delivery configurations
# Exit code 0 = safe, 1 = unsafe configs found

set -euo pipefail

CRON_FILE="${HOME}/.openclaw/cron/jobs.json"

if [ ! -f "$CRON_FILE" ]; then
  echo "✓ No OpenClaw cron jobs file found (safe)"
  exit 0
fi

echo "Auditing OpenClaw cron jobs for unsafe delivery configurations..."
echo

# Check if jq is available
if ! command -v jq &> /dev/null; then
  echo "ERROR: jq not installed. Install with: sudo apt-get install jq"
  exit 2
fi

# Find jobs with delivery mode != "none"
UNSAFE=$(jq -r '.jobs[] | select(.delivery.mode != "none" and .delivery.mode != null) | .id' "$CRON_FILE" || echo "")

if [ -z "$UNSAFE" ]; then
  echo "✓ All cron jobs have safe delivery configuration (mode=none)"
  echo
  jq -r '.jobs[] | "  - \(.name) (ID: \(.id[:8])...) - enabled=\(.enabled) delivery.mode=\(.delivery.mode // "none")"' "$CRON_FILE"
  exit 0
else
  echo "❌ UNSAFE: Found cron jobs with active delivery:"
  echo
  for job_id in $UNSAFE; do
    jq -r --arg id "$job_id" '.jobs[] | select(.id == $id) | "  - \(.name) (ID: \(.id[:8])...)\n    enabled: \(.enabled)\n    delivery: \(.delivery | @json)"' "$CRON_FILE"
    echo
  done
  echo "Fix with:"
  for job_id in $UNSAFE; do
    echo "  openclaw cron edit $job_id --no-deliver"
  done
  exit 1
fi
