#!/usr/bin/env bash
# dispatch_codex.sh — Worktree-first Codex dispatch wrapper.
#
# Ensures Codex always runs in an isolated worktree, never in the primary repo.
# Worktree creation is a hard gate, not a soft instruction.
#
# Usage:
#   dispatch_codex.sh <topic> <task>
#
#   topic  — short slug for the branch/worktree (e.g. "coo-1a-backlog")
#   task   — full task prompt to pass to Codex (quote it)
#
# Examples:
#   dispatch_codex.sh coo-1a-backlog "Build the backlog module per plan"
#   dispatch_codex.sh fix-parser "Fix YAML parser to match spec at config/parser.yaml"
#
# Creates: build/<topic> branch + .worktrees/<topic> worktree
# Then:    codex exec --sandbox workspace-write -C <worktree_path> "<task>"
#
# Exit codes:
#   0  — Codex exited 0
#   1  — Usage error
#   2  — Could not determine worktree path from start_build.py output
#   3  — Worktree path does not exist
#   4  — Worktree path resolves to primary repo root (isolation failure)
#   N  — Codex exit code (propagated)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

if [[ $# -lt 2 ]]; then
    echo "Usage: $0 <topic> <task>" >&2
    echo "" >&2
    echo "  topic  — short slug (e.g. 'coo-1a-backlog')" >&2
    echo "  task   — full task prompt (quote it)" >&2
    exit 1
fi

TOPIC="$1"
TASK="$2"

# ------------------------------------------------------------------
# Step 1: Create isolated worktree via start_build.py
# ------------------------------------------------------------------
echo ">> [dispatch_codex] Creating worktree for topic: $TOPIC"
WORKTREE_OUTPUT="$(python3 "$SCRIPT_DIR/start_build.py" "$TOPIC" 2>&1)" || true
echo "$WORKTREE_OUTPUT"

# ------------------------------------------------------------------
# Step 2: Extract worktree path from start_build.py output
# ------------------------------------------------------------------
WORKTREE_PATH="$(echo "$WORKTREE_OUTPUT" | grep -oP 'Worktree ready at:\s*\K.+' | head -1)"

# Handle "already exists" case — extract path from error message
if [[ -z "$WORKTREE_PATH" ]]; then
    WORKTREE_PATH="$(echo "$WORKTREE_OUTPUT" | grep -oP 'Worktree path already exists:\s*\K.+' | head -1)"
    if [[ -n "$WORKTREE_PATH" ]]; then
        echo ">> [dispatch_codex] Worktree already exists — reusing: $WORKTREE_PATH"
    fi
fi

if [[ -z "$WORKTREE_PATH" ]]; then
    echo "" >&2
    echo "ERROR: Could not determine worktree path from start_build.py output." >&2
    echo "       Aborting — do NOT run Codex without an isolated worktree." >&2
    exit 2
fi
WORKTREE_PATH="$(echo "$WORKTREE_PATH" | xargs)"  # trim whitespace

# ------------------------------------------------------------------
# Step 3: Safety checks
# ------------------------------------------------------------------
if [[ ! -d "$WORKTREE_PATH" ]]; then
    echo "ERROR: Worktree path does not exist: $WORKTREE_PATH" >&2
    exit 3
fi

# Reject if worktree resolves to the primary repo root
REAL_WORKTREE="$(realpath "$WORKTREE_PATH")"
REAL_REPO_ROOT="$(realpath "$REPO_ROOT")"
if [[ "$REAL_WORKTREE" == "$REAL_REPO_ROOT" ]]; then
    echo "ERROR: Worktree path resolves to primary repo root — isolation failure." >&2
    echo "       repo root: $REAL_REPO_ROOT" >&2
    echo "       worktree:  $REAL_WORKTREE" >&2
    echo "       Aborting — do NOT run Codex in the primary repo." >&2
    exit 4
fi

echo ">> [dispatch_codex] Worktree isolated at: $WORKTREE_PATH"
echo ">> [dispatch_codex] Dispatching to Codex..."
echo ""

# ------------------------------------------------------------------
# Step 4: Dispatch to Codex in the isolated worktree
# ------------------------------------------------------------------
# Disable errexit around codex invocation so non-zero exits do not
# terminate the shell before we capture CODEX_EXIT and emit the receipt.
set +e
codex exec --sandbox workspace-write -C "$WORKTREE_PATH" "$TASK"
CODEX_EXIT=$?
set -e

# ------------------------------------------------------------------
# Step 5: Emit invocation receipt (audit trail)
# ------------------------------------------------------------------
python3 "$SCRIPT_DIR/emit_dispatch_receipt.py" \
    --topic "$TOPIC" \
    --worktree "$WORKTREE_PATH" \
    --exit-code "$CODEX_EXIT" \
    --repo-root "$REPO_ROOT" || true  # receipt failure must not mask Codex exit

exit $CODEX_EXIT
