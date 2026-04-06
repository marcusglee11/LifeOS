#!/usr/bin/env bash
# Idempotently installs LifeOS WSL session hooks into ~/.bashrc.
# Run once from the repo root: bash scripts/setup/install_wsl_hooks.sh
set -euo pipefail

MARKER="# LifeOS COO gateway auto-start (managed by install_wsl_hooks.sh)"
BASHRC="$HOME/.bashrc"
BUILD_REPO="$(cd "$(dirname "$0")/../.." && pwd)"

if grep -qF "$MARKER" "$BASHRC" 2>/dev/null; then
  echo "WSL hooks already installed in $BASHRC — nothing to do."
  exit 0
fi

cat >> "$BASHRC" << HOOK

$MARKER
_lifeos_ensure_gateway() {
  local repo="$BUILD_REPO"
  local port="\${OPENCLAW_GATEWAY_PORT:-18789}"
  # 2s timeout prevents blocking shell startup if openclaw is slow or absent
  if ! timeout 2s openclaw gateway --port "\$port" probe --json 2>/dev/null | grep -q '"ok":true'; then
    ( cd "\$repo" && runtime/tools/openclaw_gateway_ensure.sh >/dev/null 2>&1 ) &
    disown
  fi
}
command -v openclaw >/dev/null 2>&1 && _lifeos_ensure_gateway
HOOK

echo "Installed WSL gateway hook in $BASHRC (BUILD_REPO=$BUILD_REPO)"
echo "Reload with: source $BASHRC"
