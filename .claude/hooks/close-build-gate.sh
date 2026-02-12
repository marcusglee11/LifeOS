#!/usr/bin/env bash
# PreToolUse hook: gate git merge/push through closure checks.
# Reads Claude Code stdin JSON, extracts tool_input.command.
# Early-exits (~10ms) for non-merge/push commands.
set -euo pipefail

# Read stdin JSON from Claude Code
INPUT=$(cat)

# Extract command from tool_input.command
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)

# Early exit for non-merge/push commands (fast path)
case "${COMMAND:-}" in
    git\ merge*|git\ push*) ;;
    *) exit 0 ;;
esac

# Resolve repo root
REPO_ROOT="${CLAUDE_PROJECT_DIR:-.}"

# Run closure gate
VERDICT=$(python3 "$REPO_ROOT/scripts/workflow/closure_gate.py" --repo-root "$REPO_ROOT" 2>/dev/null) || true

# Fail-closed: if no output, block the operation
if [ -z "$VERDICT" ]; then
    cat <<'EOF'
{
  "decision": "block",
  "reason": "Closure gate produced no output (fail-closed). Run `python3 scripts/workflow/closure_gate.py` manually to diagnose."
}
EOF
    exit 2
fi

# Parse verdict
PASSED=$(echo "$VERDICT" | jq -r '.passed // empty' 2>/dev/null)
SUMMARY=$(echo "$VERDICT" | jq -r '.summary // "no summary"' 2>/dev/null)
GATE=$(echo "$VERDICT" | jq -r '.gate // "unknown"' 2>/dev/null)
REASON=$(echo "$VERDICT" | jq -r '.reason // ""' 2>/dev/null)

if [ "$PASSED" = "true" ]; then
    # Allow with context
    jq -n \
        --arg summary "$SUMMARY" \
        '{
            "decision": "allow",
            "reason": ("Closure gates passed: " + $summary)
        }'
    exit 0
else
    # Deny with reason
    jq -n \
        --arg gate "$GATE" \
        --arg reason "$REASON" \
        --arg summary "$SUMMARY" \
        '{
            "decision": "block",
            "reason": ("Closure gate failed (" + $gate + "): " + $reason)
        }'
    exit 2
fi
