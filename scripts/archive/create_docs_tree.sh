#!/usr/bin/env bash
set -euo pipefail

# Root of the unified LifeOS repo (as seen from WSL)
LIFE_ROOT="/mnt/c/Users/cabra/Projects/LifeOS"
DOC_ROOT="$LIFE_ROOT/docs"

echo "Creating LifeOS docs tree under: $DOC_ROOT"

# Create root docs directory
mkdir -p "$DOC_ROOT"

# Ordered category folders
dirs=(
  "00_foundations"
  "01_governance"
  "02_alignment"
  "03_runtime"
  "04_project_builder"
  "05_agents"
  "06_user_surface"
  "07_productisation"
  "08_manuals"
  "09_prompts"
  "10_meta"
  "99_archive"
)

for d in "${dirs[@]}"; do
  echo "  - $d"
  mkdir -p "$DOC_ROOT/$d"
done

# Optional root README
README_PATH="$LIFE_ROOT/README.md"
if [ ! -f "$README_PATH" ]; then
  cat > "$README_PATH" << 'EOF'
This repository contains the authoritative documentation for the LifeOS system.

All specifications, governance rules, alignment layers, runtime contracts,
and engineering packets live in /docs/.

Anything outside /docs/ is non-authoritative and may be deprecated.
EOF
  echo "Created root README at: $README_PATH"
else
  echo "Root README already exists at: $README_PATH (leaving unchanged)"
fi

echo "Docs tree creation complete."
