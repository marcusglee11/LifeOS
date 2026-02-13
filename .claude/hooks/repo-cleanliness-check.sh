#!/usr/bin/env bash
# Stop hook: warn about repo cleanliness (informational, never blocks).
set -euo pipefail

INPUT=$(cat)
CWD=$(echo "$INPUT" | jq -r '.cwd // empty' 2>/dev/null)
REPO_ROOT="${CWD:-${CLAUDE_PROJECT_DIR:-.}}"

PORCELAIN=$(git -C "$REPO_ROOT" status --porcelain=v1 2>/dev/null || true)

if [ -z "$PORCELAIN" ]; then
    echo '{"continue":true}'
    exit 0
fi

DIRTY_COUNT=$(echo "$PORCELAIN" | wc -l | tr -d ' ')

cat <<EOF
{
  "continue": true,
  "systemMessage": "REPO DIRTY: $DIRTY_COUNT uncommitted file(s). Run 'git status' to review. Commit, stash, or explain in your handoff."
}
EOF
exit 0
