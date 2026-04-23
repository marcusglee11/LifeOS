#!/usr/bin/env bash
# Git post-commit hook for wiki refresh.
# Install: ln -sf "$(git rev-parse --show-toplevel)/scripts/wiki/post-commit-hook.sh" \
#                  "$(git rev-parse --show-toplevel)/.git/hooks/post-commit"
#
# Only runs when docs/ files are in the commit. Appends changed paths to
# .context/wiki/_refresh_needed for later EA-driven refresh.
# No LLM calls here — works in any environment (Codex, CI, Claude Code).

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
WIKI_DIR="$REPO_ROOT/.context/wiki"
MARKER="$WIKI_DIR/_refresh_needed"

# Get files changed in the last commit that are under docs/
CHANGED_DOCS=$(git diff-tree --no-commit-id -r --name-only HEAD | grep '^docs/' || true)

if [ -z "$CHANGED_DOCS" ]; then
    exit 0
fi

if [ ! -d "$WIKI_DIR" ]; then
    exit 0
fi

# Append changed paths to marker (accumulates across commits until consumed)
echo "$CHANGED_DOCS" >> "$MARKER"
echo "[wiki] Docs changed — run: python3 scripts/wiki/refresh_wiki.py"
