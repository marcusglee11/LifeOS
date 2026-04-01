#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
python3 "$REPO_ROOT/scripts/workflow/test_router.py" --repo-root "$REPO_ROOT" "$@"

