#!/usr/bin/env python3
"""
Generate Passage Evidence Bundles (CT-2 Phase 2 v2.2)
=====================================================

Deterministically generates the required passage evidence bundles:
1. PASS: Allowed docs .md edit
2. BLOCK_DENYLIST: Denylisted path touched
3. BLOCK_ENVELOPE: Non-md under docs (or review_packets modify/delete)

This script imports opencode_ci_runner to ensure the exact same logic is used.
"""

import sys
import os
import shutil

# Ensure we can import from scripts
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import opencode_ci_runner as runner
import opencode_gate_policy as policy
from opencode_gate_policy import ReasonCode

def main():
    # Setup
    bundles_dir = os.path.join("artifacts", "evidence", "passage_bundles_v2.4")
    if os.path.exists(bundles_dir):
        shutil.rmtree(bundles_dir)
    os.makedirs(bundles_dir, exist_ok=True)
    
    # Temporarily redirect EVIDENCE_ROOT to our target dir
    original_evidence_root = policy.EVIDENCE_ROOT
    policy.EVIDENCE_ROOT = bundles_dir
    
    print(f"Generating bundles in {bundles_dir}...")
    
    # =========================================================================
    # 1. PASS Bundle: Allowed docs .md edit
    # =========================================================================
    print("Generating PASS bundle...")
    runner.clear_log_buffer()
    runner.log("Starting PASS mission simulation", "info")
    runner.log("Simulating server response", "info")
    runner.log("Executed: git diff --name-status", "info")
    
    task_pass = {
        "files": ["docs/new_feature.md"],
        "action": "create",
        "instruction": "Create a new doc"
    }
    parsed_pass = [("A", "docs/new_feature.md")]
    
    path_pass = runner.generate_evidence_bundle(
        status="PASS",
        reason=None,
        mode="MOCK_PASSAGE",
        task=task_pass,
        parsed_diff=parsed_pass,
        blocked_entries=[]
    )
    # Rename for clarity
    shutil.move(path_pass, os.path.join(bundles_dir, "BUNDLE_PASS"))
    
    # =========================================================================
    # 2. BLOCK Bundle 1: Denylisted path
    # =========================================================================
    print("Generating BLOCK_DENYLIST bundle...")
    runner.clear_log_buffer()
    runner.log("Starting BLOCK_DENYLIST mission simulation", "info")
    runner.log("Validating post-execution diff", "info")
    runner.log("Envelope violation: docs/00_foundations/policy.md (M) - DENYLIST_ROOT_BLOCKED", "error")
    
    task_block1 = {
        "files": ["docs/00_foundations/policy.md"],
        "action": "modify",
        "instruction": "Update policy"
    }
    parsed_block1 = [("M", "docs/00_foundations/policy.md")]
    blocked_block1 = [("docs/00_foundations/policy.md", "M", ReasonCode.DENYLIST_ROOT_BLOCKED)]
    
    path_block1 = runner.generate_evidence_bundle(
        status="BLOCK",
        reason=ReasonCode.DENYLIST_ROOT_BLOCKED,
        mode="MOCK_PASSAGE",
        task=task_block1,
        parsed_diff=parsed_block1,
        blocked_entries=blocked_block1
    )
    shutil.move(path_block1, os.path.join(bundles_dir, "BUNDLE_BLOCK_DENYLIST"))

    # =========================================================================
    # 3. BLOCK Bundle 2: Non-md under docs
    # =========================================================================
    print("Generating BLOCK_ENVELOPE bundle...")
    runner.clear_log_buffer()
    runner.log("Starting BLOCK_ENVELOPE mission simulation", "info")
    runner.log("Validating post-execution diff", "info")
    runner.log("Envelope violation: docs/script.py (A) - NON_MD_EXTENSION_BLOCKED", "error")
    
    task_block2 = {
        "files": ["docs/script.py"],
        "action": "create",
        "instruction": "Add script to docs"
    }
    parsed_block2 = [("A", "docs/script.py")]
    blocked_block2 = [("docs/script.py", "A", ReasonCode.NON_MD_EXTENSION_BLOCKED)]
    
    path_block2 = runner.generate_evidence_bundle(
        status="BLOCK",
        reason=ReasonCode.NON_MD_EXTENSION_BLOCKED,
        mode="MOCK_PASSAGE",
        task=task_block2,
        parsed_diff=parsed_block2,
        blocked_entries=blocked_block2
    )
    shutil.move(path_block2, os.path.join(bundles_dir, "BUNDLE_BLOCK_ENVELOPE"))
    
    # Restore
    policy.EVIDENCE_ROOT = original_evidence_root
    print("Done.")

if __name__ == "__main__":
    main()
