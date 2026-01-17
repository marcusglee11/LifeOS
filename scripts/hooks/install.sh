#!/bin/bash
#
# Install LifeOS Git Hooks
#
# Run this script to install the workflow enforcement hooks:
#   ./scripts/hooks/install.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOKS_DIR="$(git rev-parse --git-dir)/hooks"

echo "📦 Installing LifeOS Git Hooks..."

# Install pre-commit hook
if [ -f "$SCRIPT_DIR/pre-commit" ]; then
    cp "$SCRIPT_DIR/pre-commit" "$HOOKS_DIR/pre-commit"
    chmod +x "$HOOKS_DIR/pre-commit"
    echo "✅ Installed: pre-commit"
fi

echo ""
echo "🎉 Done! Git workflow hooks are now active."
echo ""
echo "To test: try committing on main (should be blocked)"
echo "To bypass: use --no-verify flag (logged as emergency)"
