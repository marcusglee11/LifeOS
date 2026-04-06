#!/usr/bin/env bash
# dispatch_opencode.sh — Worktree-first OpenCode dispatch wrapper.
#
# Usage:
#   dispatch_opencode.sh <topic> <task>
#
# Exit codes:
#   0  — OpenCode and sprint-close emission succeeded
#   1  — Usage error
#   2  — Could not determine worktree path from start_build.py output
#   3  — Worktree path does not exist
#   4  — Worktree path resolves to primary repo root (isolation failure)
#   5  — Task prompt does not contain exactly one valid backlog task ID
#   6  — Sprint-close packet emission failed

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REAL_REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
REPO_ROOT="${LIFEOS_DISPATCH_REPO_ROOT:-$REAL_REPO_ROOT}"
PYTHON_ROOT="${LIFEOS_DISPATCH_PYTHON_ROOT:-$REAL_REPO_ROOT}"

if [[ $# -lt 2 ]]; then
    echo "Usage: $0 <topic> <task>" >&2
    exit 1
fi

TOPIC="$1"
TASK="$2"
TASK_IDS="$(printf '%s\n' "$TASK" | grep -oE 'T-[0-9]{3,}' | sort -u || true)"
TASK_ID_COUNT="$(printf '%s\n' "$TASK_IDS" | sed '/^$/d' | wc -l | tr -d ' ')"
if [[ "$TASK_ID_COUNT" != "1" ]]; then
    echo "ERROR: Task prompt must contain exactly one backlog task ID like T-030." >&2
    exit 5
fi

TASK_REF="$(printf '%s\n' "$TASK_IDS" | sed -n '1p')"
if [[ ! -f "$REPO_ROOT/config/tasks/backlog.yaml" ]] || ! grep -q "^- id: $TASK_REF\$" "$REPO_ROOT/config/tasks/backlog.yaml"; then
    echo "ERROR: Task ID $TASK_REF was not found in config/tasks/backlog.yaml." >&2
    exit 5
fi

ORDER_ID="ORD-${TASK_REF}-$(date -u +%Y%m%dT%H%M%SZ)"

if [[ -n "${LIFEOS_DISPATCH_WORKTREE_PATH:-}" ]]; then
    WORKTREE_PATH="$LIFEOS_DISPATCH_WORKTREE_PATH"
else
    WORKTREE_OUTPUT="$(python3 "$SCRIPT_DIR/start_build.py" "$TOPIC" 2>&1)" || true
    echo "$WORKTREE_OUTPUT"
    WORKTREE_PATH="$(echo "$WORKTREE_OUTPUT" | grep -oP 'Worktree ready at:\s*\K.+' | head -1)"
    if [[ -z "$WORKTREE_PATH" ]]; then
        WORKTREE_PATH="$(echo "$WORKTREE_OUTPUT" | grep -oP 'Worktree path already exists:\s*\K.+' | head -1)"
    fi
    if [[ -z "$WORKTREE_PATH" ]]; then
        echo "ERROR: Could not determine worktree path from start_build.py output." >&2
        exit 2
    fi
fi

WORKTREE_PATH="$(echo "$WORKTREE_PATH" | xargs)"
if [[ ! -d "$WORKTREE_PATH" ]]; then
    echo "ERROR: Worktree path does not exist: $WORKTREE_PATH" >&2
    exit 3
fi

REAL_WORKTREE="$(realpath "$WORKTREE_PATH")"
REAL_REPO_ROOT="$(realpath "$REPO_ROOT")"
if [[ "$REAL_WORKTREE" == "$REAL_REPO_ROOT" ]]; then
    echo "ERROR: Worktree path resolves to primary repo root — isolation failure." >&2
    exit 4
fi

set +e
if [[ -n "${LIFEOS_DISPATCH_PROVIDER_EXIT_CODE:-}" ]]; then
    OPENCODE_EXIT="$LIFEOS_DISPATCH_PROVIDER_EXIT_CODE"
else
    (
        cd "$WORKTREE_PATH"
        opencode run "$TASK"
    )
    OPENCODE_EXIT=$?
fi
set -e

OUTCOME="blocked"
if [[ "$OPENCODE_EXIT" == "0" ]]; then
    OUTCOME="success"
fi

set +e
python3 "$SCRIPT_DIR/emit_sprint_close_packet.py" \
    --repo-root "$REPO_ROOT" \
    --python-root "$PYTHON_ROOT" \
    --order-id "$ORDER_ID" \
    --task-ref "$TASK_REF" \
    --agent "opencode" \
    --outcome "$OUTCOME" \
    --sync-check-result "skipped"
SPRINT_EXIT=$?
set -e

FINAL_EXIT="$OPENCODE_EXIT"
if [[ "$SPRINT_EXIT" != "0" ]]; then
    FINAL_EXIT=6
fi

python3 "$SCRIPT_DIR/emit_dispatch_receipt.py" \
    --topic "$TOPIC" \
    --worktree "$WORKTREE_PATH" \
    --exit-code "$FINAL_EXIT" \
    --repo-root "$REPO_ROOT" \
    --python-root "$PYTHON_ROOT" || true

if [[ "$SPRINT_EXIT" != "0" ]]; then
    echo "ERROR: Sprint-close packet emission failed." >&2
fi

exit "$FINAL_EXIT"
