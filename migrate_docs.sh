#!/usr/bin/env bash
set -euo pipefail

# ---- ROOTS (adjust here if your paths differ) ----

LIFE_ROOT="/mnt/c/Users/cabra/Projects/LifeOS"
DOC_ROOT="$LIFE_ROOT/docs"

COO_ROOT="/mnt/c/Users/cabra/Projects/COOProject/coo-agent"
COO_IDEAS="/mnt/c/Users/cabra/Projects/COOProject/Ideas&Planning"
COO_START="/mnt/c/Users/cabra/Projects/COOProject/ChatGPTStartingFiles"
COO_TEST="/mnt/c/Users/cabra/Projects/COOProject/UserTesting"

GOV_ROOT="/mnt/c/Users/cabra/Projects/governance-hub"
GOV_MANUALS="$GOV_ROOT/manuals"

# Ensure docs tree exists
if [ ! -d "$DOC_ROOT" ]; then
  echo "Docs root $DOC_ROOT does not exist. Run create_docs_tree.sh first."
  exit 1
fi

echo "Migrating documents into $DOC_ROOT"
echo

# Helpers
move_if_exists() {
  local src="$1"
  local dst="$2"
  if [ -f "$src" ]; then
    local dst_dir
    dst_dir="$(dirname "$dst")"
    mkdir -p "$dst_dir"
    echo "mv '$src' -> '$dst'"
    mv "$src" "$dst"
  else
    echo "SKIP (not found): $src"
  fi
}

# --------------------------------------------------
# 1. COOProject: Ideas & Planning (Alignment + PB)
# --------------------------------------------------

move_if_exists \
  "$COO_IDEAS/Alignment Layer v1.4.md" \
  "$DOC_ROOT/02_alignment/Alignment_Layer_v1.4.md"

move_if_exists \
  "$COO_IDEAS/LifeOS_Alignment_Layer_v1.0.md" \
  "$DOC_ROOT/02_alignment/LifeOS_Alignment_Layer_v1.0.md"

move_if_exists \
  "$COO_IDEAS/Antigravity_Implementation_Packet_v0_9_6.md" \
  "$DOC_ROOT/99_archive/Antigravity_Implementation_Packet_v0.9.6.md"

# --------------------------------------------------
# 2. COOProject: ChatGPTStartingFiles (COO governance + starter docs)
# --------------------------------------------------

move_if_exists \
  "$COO_START/COO_Operating_Contract.md" \
  "$DOC_ROOT/01_governance/COO_Operating_Contract_v1.0.md"

move_if_exists \
  "$COO_START/COO_Expectations_Log.md" \
  "$DOC_ROOT/01_governance/COO_Expectations_Log.md"

move_if_exists \
  "$COO_START/Architecture_Skeleton.md" \
  "$DOC_ROOT/00_foundations/Architecture_Skeleton.md"

move_if_exists \
  "$COO_START/COO Runtime — V1.1 CLEAN BUILD.md" \
  "$DOC_ROOT/03_runtime/COO_Runtime_V1.1_Clean_Build_Spec.md"

move_if_exists \
  "$COO_START/README.md" \
  "$DOC_ROOT/10_meta/COO_Clean_Build_Readme.md"

# --------------------------------------------------
# 3. COOProject: UserTesting (User Surface / Stage B)
# --------------------------------------------------

move_if_exists \
  "$COO_TEST/COO Runtime V1.1 — User Surface Implementation (Stage B + Test Harness).md" \
  "$DOC_ROOT/06_user_surface/COO_Runtime_V1.1_User_Surface_StageB_TestHarness.md"

# --------------------------------------------------
# 4. coo-agent docs root (project builder, meta, walkthrough, etc.)
# --------------------------------------------------

# Project Builder spec (clean)
move_if_exists \
  "$COO_ROOT/docs/GPTCOO_v1_1_ProjectBuilder_v0_9_FinalCleanSpec.md" \
  "$DOC_ROOT/04_project_builder/ProjectBuilder_Spec_v0.9_FinalClean.md"

# PB implementation packet v0.9.7 (if under docs/ or docs/specs/)
move_if_exists \
  "$COO_ROOT/docs/Antigravity_Implementation_Packet_v0_9_7.md" \
  "$DOC_ROOT/04_project_builder/Antigravity_Implementation_Packet_v0.9.7.md"
move_if_exists \
  "$COO_ROOT/docs/specs/Antigravity_Implementation_Packet_v0_9_7.md" \
  "$DOC_ROOT/04_project_builder/Antigravity_Implementation_Packet_v0.9.7.md"

# PB patched spec (history -> archive)
move_if_exists \
  "$COO_ROOT/docs/GPTCOO_v1_1_ProjectBuilder_v0_9_PatchedSpec.md" \
  "$DOC_ROOT/99_archive/ProjectBuilder_Spec_v0.9_PatchHistory.md"

# Council review packet for Antigravity
move_if_exists \
  "$COO_ROOT/docs/Antigravity_Council_Review_Packet_Spec_v1.0.md" \
  "$DOC_ROOT/01_governance/Antigravity_Council_Review_Packet_Spec_v1.0.md"

# Meta docs
move_if_exists \
  "$COO_ROOT/docs/CODE_REVIEW_STATUS.md" \
  "$DOC_ROOT/10_meta/CODE_REVIEW_STATUS.md"

move_if_exists \
  "$COO_ROOT/docs/governance_digest.md" \
  "$DOC_ROOT/10_meta/governance_digest.md"

move_if_exists \
  "$COO_ROOT/docs/IMPLEMENTATION_PLAN.md" \
  "$DOC_ROOT/10_meta/IMPLEMENTATION_PLAN.md"

move_if_exists \
  "$COO_ROOT/docs/TASKS.md" \
  "$DOC_ROOT/10_meta/TASKS.md"

move_if_exists \
  "$COO_ROOT/docs/Review_Packet_Reminder.md" \
  "$DOC_ROOT/10_meta/Review_Packet_Reminder.md"

move_if_exists \
  "$COO_ROOT/docs/WALKTHROUGH.md" \
  "$DOC_ROOT/03_runtime/WALKTHROUGH.md"

move_if_exists \
  "$COO_ROOT/docs/ARCHITECTUREold.md" \
  "$DOC_ROOT/99_archive/ARCHITECTUREold.md"

# --------------------------------------------------
# 5. coo-agent docs/specs (runtime spec + impl + index + COOSpec)
# --------------------------------------------------

move_if_exists \
  "$COO_ROOT/docs/specs/COO_RUNTIME_SPECIFICATION_v1.0.md" \
  "$DOC_ROOT/03_runtime/COO_Runtime_Spec_v1.0.md"

move_if_exists \
  "$COO_ROOT/docs/specs/IMPLEMENTATION PACKET v1.0.md" \
  "$DOC_ROOT/03_runtime/COO_Runtime_Implementation_Packet_v1.0.md"

move_if_exists \
  "$COO_ROOT/docs/specs/Spec_Canon_Index.md" \
  "$DOC_ROOT/03_runtime/COO_Runtime_Spec_Index_v1.0.md"

# COOSpec master (wherever it lives under coo-agent/docs)
move_if_exists \
  "$COO_ROOT/docs/COOSpecv1.0Final.md" \
  "$DOC_ROOT/03_runtime/COO_Runtime_Core_Spec_v1.0.md"
move_if_exists \
  "$COO_ROOT/docs/specs/COOSpecv1.0Final.md" \
  "$DOC_ROOT/03_runtime/COO_Runtime_Core_Spec_v1.0.md"

# Mission Orchestrator architecture
move_if_exists \
  "$COO_ROOT/docs/ARCHITECTURE.md" \
  "$DOC_ROOT/05_agents/COO_Agent_Mission_Orchestrator_Arch_v0.7_Aligned.md"

# --------------------------------------------------
# 6. governance-hub (council + manuals + prompts v1.0)
# --------------------------------------------------

# Council invocation spec
move_if_exists \
  "$GOV_ROOT/Council_Invoke.md" \
  "$DOC_ROOT/01_governance/Council_Invocation_Runtime_Binding_Spec_v1.0.md"

# Governance runtime manual
move_if_exists \
  "$GOV_MANUALS/governance_runtime_manual_v1.0.md" \
  "$DOC_ROOT/08_manuals/Governance_Runtime_Manual_v1.0.md"

# Prompt library (copy entire v1.0 tree if desired)
if [ -d "$GOV_ROOT/prompts/v1.0" ]; then
  mkdir -p "$DOC_ROOT/09_prompts"
  echo "Copying prompts v1.0 -> $DOC_ROOT/09_prompts/v1.0"
  cp -r "$GOV_ROOT/prompts/v1.0" "$DOC_ROOT/09_prompts/"
else
  echo "SKIP (prompt dir not found): $GOV_ROOT/prompts/v1.0"
fi

echo
echo "Migration script completed. Review the output above to confirm moves."
echo "You can now treat /LifeOS/docs as your single authoritative docs tree."
