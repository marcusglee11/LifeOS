#!/usr/bin/env bash
# Git post-commit hook for wiki refresh.
# Install: ln -sf "$(git rev-parse --show-toplevel)/scripts/wiki/post-commit-hook.sh" \
#                  "$(git rev-parse --show-toplevel)/.git/hooks/post-commit"
#
# Only runs when docs/ files are in the commit. Writes _pending_diff.patch
# for human review — does NOT auto-commit wiki changes.

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
WIKI_REFRESH="$REPO_ROOT/scripts/wiki/refresh_wiki.py"

# Get files changed in the last commit that are under docs/
CHANGED_DOCS=$(git diff-tree --no-commit-id -r --name-only HEAD | grep '^docs/' || true)

if [ -z "$CHANGED_DOCS" ]; then
    exit 0
fi

if [ ! -f "$WIKI_REFRESH" ]; then
    echo "[wiki] refresh_wiki.py not found — skipping wiki refresh" >&2
    exit 0
fi

if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
    echo "[wiki] ANTHROPIC_API_KEY not set — skipping wiki refresh" >&2
    exit 0
fi

echo "[wiki] docs/ changed — refreshing wiki pages..."
# shellcheck disable=SC2086
python3 "$WIKI_REFRESH" --changed-files $CHANGED_DOCS || {
    echo "[wiki] refresh_wiki.py failed — check .context/wiki/ for partial output" >&2
}
