#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  runtime/tools/openclaw_onboard_operator.sh --candidate-ref <non-secret-ref> [--note <text>]

Purpose:
  Produce a controlled, auditable onboarding checklist without writing raw operator identifiers.
  The script records only a SHA256 fingerprint of the provided reference.
USAGE
}

CANDIDATE_REF=""
NOTE=""
STATE_DIR="${OPENCLAW_STATE_DIR:-$HOME/.openclaw}"
TS_UTC="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_DIR="${OPENCLAW_ONBOARD_OUT_DIR:-$STATE_DIR/onboarding/$TS_UTC}"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --candidate-ref)
      CANDIDATE_REF="${2:-}"
      shift 2
      ;;
    --note)
      NOTE="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [ -z "$CANDIDATE_REF" ]; then
  echo "ERROR: --candidate-ref is required" >&2
  exit 2
fi

# Prevent accidental leakage of obvious raw IDs/usernames/chats.
if printf '%s' "$CANDIDATE_REF" | rg -q '[@:+]|[0-9]{6,}'; then
  echo "BLOCKED: candidate-ref appears to contain raw identifier data; provide a neutral internal reference label." >&2
  exit 1
fi

if ! mkdir -p "$OUT_DIR" 2>/dev/null; then
  OUT_DIR="/tmp/openclaw-onboarding/$TS_UTC"
  mkdir -p "$OUT_DIR"
fi

hash="$(printf '%s' "$CANDIDATE_REF" | sha256sum | awk '{print $1}')"
branch="$(git rev-parse --abbrev-ref HEAD)"
head="$(git rev-parse --short HEAD)"
plan="$OUT_DIR/onboarding_plan.md"

{
  echo "# OpenClaw Operator Onboarding Plan"
  echo
  echo "- ts_utc: $TS_UTC"
  echo "- candidate_ref_sha256: $hash"
  echo "- branch: $branch"
  echo "- head: $head"
  if [ -n "$NOTE" ]; then
    echo "- note: $NOTE"
  fi
  echo
  echo "## Required Changes (Manual, Auditable)"
  echo "1. Add candidate to \`commands.ownerAllowFrom\` only if owner privileges are required."
  echo "2. Add candidate to per-channel \`channels.<channel>.allowFrom\` lists explicitly (no wildcards)."
  echo "3. Keep \`commands.useAccessGroups=true\`."
  echo "4. Keep Telegram \`requireMention=true\`, non-empty \`mentionPatterns\`, and \`replyToMode=first\`."
  echo "5. Run verifiers:"
  echo "   - \`runtime/tools/openclaw_multiuser_posture_assert.py --json\`"
  echo "   - \`runtime/tools/openclaw_verify_multiuser_posture.sh\`"
  echo
  echo "## Approval"
  echo "- Reviewer: ____________________"
  echo "- Decision: APPROVE / REJECT"
  echo "- Date (UTC): __________________"
} > "$plan"

printf '%s\n' "$plan"

