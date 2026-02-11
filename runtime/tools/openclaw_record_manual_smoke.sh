#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<USAGE
Usage:
  runtime/tools/openclaw_record_manual_smoke.sh --surface telegram_dm --result pass|fail --sources <file:line-range[,file:line-range...]|(none)>
USAGE
}

SURFACE=""
RESULT=""
SOURCES=""

while [ $# -gt 0 ]; do
  case "$1" in
    --surface)
      SURFACE="${2:-}"
      shift 2
      ;;
    --result)
      RESULT="${2:-}"
      shift 2
      ;;
    --sources)
      SOURCES="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [ "$SURFACE" != "telegram_dm" ]; then
  echo "surface must be telegram_dm" >&2
  exit 2
fi
if [ "$RESULT" != "pass" ] && [ "$RESULT" != "fail" ]; then
  echo "result must be pass or fail" >&2
  exit 2
fi
if [ -z "$SOURCES" ]; then
  echo "sources is required" >&2
  exit 2
fi

# Fail-closed: only allow strict source pointer tokens or literal (none).
# No spaces or free-form text are allowed.
if [ "$SOURCES" != "(none)" ]; then
  if printf '%s' "$SOURCES" | rg -q '[[:space:]]'; then
    echo "sources must not contain whitespace" >&2
    exit 2
  fi
  if ! printf '%s' "$SOURCES" | rg -q '^[A-Za-z0-9_./-]+:[0-9]+-[0-9]+(,[A-Za-z0-9_./-]+:[0-9]+-[0-9]+)*$'; then
    echo "sources must be file:line-range tokens, comma-separated" >&2
    exit 2
  fi
fi

TS_UTC="$(date -u +%Y%m%dT%H%M%SZ)"
BRANCH="$(git rev-parse --abbrev-ref HEAD)"
HEAD_SHORT="$(git rev-parse --short HEAD)"
EV_BASE="${P1_5_EVDIR:-artifacts/evidence/openclaw/p1_5/$TS_UTC}"
mkdir -p "$EV_BASE"
NOTE_PATH="$EV_BASE/manual_smoke_note.md"

{
  echo "ts_utc: $TS_UTC"
  echo "surface: $SURFACE"
  echo "result: $RESULT"
  echo "sources: $SOURCES"
  echo "verifier_context: branch=$BRANCH head=$HEAD_SHORT"
} > "$NOTE_PATH"

echo "$NOTE_PATH"
