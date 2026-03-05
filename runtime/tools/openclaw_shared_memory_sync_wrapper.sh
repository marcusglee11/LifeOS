#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "ERROR: usage: $0 --instance <id> [--job-type <type>] [-- <sync-args...>]" >&2
  exit 2
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
sync_script="$script_dir/openclaw_shared_memory_sync.sh"
if [ ! -x "$sync_script" ]; then
  echo "ERROR: missing executable sync script: $sync_script" >&2
  exit 127
fi

exec "$sync_script" "$@"
