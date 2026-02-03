#!/usr/bin/env python3
import os
import sys
import hashlib
import re

def compute_sha256(file_path):
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def validate():
    failures = []
    
    # C1: Files to check
    files = {
        "LIFEOS_STATE": "docs/11_admin/LIFEOS_STATE.md",
        "BACKLOG": "docs/11_admin/BACKLOG.md",
        "AUTONOMY_STATUS": "docs/11_admin/AUTONOMY_STATUS.md"
    }
    
    for key, path in files.items():
        if not os.path.exists(path):
            failures.append(f"FAIL {key}: {path} missing")

    if failures:
        for f in failures: print(f)
        sys.exit(1)

    # C2: Parse markers
    with open(files["LIFEOS_STATE"], "r", encoding="utf-8") as f:
        ls_content = f.read()
    with open(files["BACKLOG"], "r", encoding="utf-8") as f:
        bl_content = f.read()
    with open(files["AUTONOMY_STATUS"], "r", encoding="utf-8") as f:
        as_content = f.read()

    # LIFEOS_STATE checks
    if "## Canonical Spine" not in ls_content:
        failures.append("FAIL LIFEOS_STATE: missing '## Canonical Spine' block")
    if "docs/11_admin/BACKLOG.md" not in ls_content:
        failures.append("FAIL LIFEOS_STATE: missing link to BACKLOG.md")
    if "docs/11_admin/AUTONOMY_STATUS.md" not in ls_content:
        failures.append("FAIL LIFEOS_STATE: missing link to AUTONOMY_STATUS.md")
    
    # BACKLOG checks
    if "## Workflow Hook" not in bl_content and "Done means" not in bl_content:
        failures.append("FAIL BACKLOG: missing '## Workflow Hook' or 'Done means' block")
        
    # AUTONOMY_STATUS checks
    if "Derived view" not in as_content or "canon wins" not in as_content:
        failures.append("FAIL AUTONOMY_STATUS: missing 'Derived view' or 'canon wins' language")

    # C3: Extract baseline zip path and sha256
    # Pattern: artifacts/packets/status/Repo_Autonomy_Status_Pack__Main.zip
    zip_path_match = re.search(r'(artifacts/packets/status/Repo_Autonomy_Status_Pack__Main\.zip)', ls_content)
    if not zip_path_match:
        failures.append("FAIL LIFEOS_STATE: missing baseline zip path")
        zip_path = None
    else:
        zip_path = zip_path_match.group(1)

    # SHA extraction from LS or AS (using LS as primary for validator)
    # Flexible match for: sha256: HEX, **sha256:** `HEX`, etc.
    sha_match = re.search(r'sha256.*?\s*`?([a-fA-F0-9]{64})`?', ls_content)
    if not sha_match:
        failures.append("FAIL LIFEOS_STATE: missing sha256 for baseline pack")
        expected_sha = None
    else:
        expected_sha = sha_match.group(1) or sha_match.group(2)

    # C4: Verify zip existence
    if zip_path and not os.path.exists(zip_path):
        failures.append(f"FAIL BASELINE_PACK: {zip_path} missing")
    elif zip_path and expected_sha:
        # C5: Compute and verify SHA
        actual_sha = compute_sha256(zip_path)
        if actual_sha != expected_sha:
            failures.append(f"FAIL BASELINE_SHA: expected {expected_sha} got {actual_sha}")

    if failures:
        for f in failures: print(f)
        sys.exit(1)
    
    print("PASS canon_spine valid; baseline_sha256 matches; pack_exists")
    sys.exit(0)

if __name__ == "__main__":
    validate()
