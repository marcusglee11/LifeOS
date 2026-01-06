#!/usr/bin/env python3
import os
import glob
import hashlib
import zipfile
import subprocess
import sys
import shutil
from pathlib import Path
from datetime import datetime

# --- Configuration ---
REPO_ROOT = Path(__file__).parent.parent
BUNDLE_DIR = REPO_ROOT / "artifacts" / "ct2"
BUNDLE_DIR.mkdir(parents=True, exist_ok=True)

PACKET_SRC = REPO_ROOT / "artifacts/plans/CT2_Activation_Packet_DocSteward_G3.md"
RAW_LOG_SRC = REPO_ROOT / "artifacts/plans/Execution_Evidence_CT2_Raw.txt"
LEDGER_DIR = REPO_ROOT / "artifacts/ledger/dl_doc"

def compute_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()

def main():
    print("[BUILDER] Starting CT-2 Bundle Build...")
    
    # 1. Collect Artifacts
    artifacts = []
    
    if not PACKET_SRC.exists():
        print(f"[ERROR] Packet not found: {PACKET_SRC}")
        sys.exit(1)
    artifacts.append(PACKET_SRC)
    
    if not RAW_LOG_SRC.exists():
        print(f"[ERROR] Raw log not found: {RAW_LOG_SRC}")
        sys.exit(1)
    artifacts.append(RAW_LOG_SRC)
    
    # Collect Ledgers (Recent ones only or all? User implied repo-relative collection)
    # The audit check looks for specific patterns. We'll grab the ones that match generated patterns.
    # Pattern: 2026-01-06_* (Assuming date) or just grab all relevant yamls.
    # To be safe and deterministic, we should probably grab what's there corresponding to the proof runs.
    # We will grab all .yaml files in dl_doc modified today/recently or just all of them that match patterns?
    # Let's grab all .yaml files in dl_doc that match the patterns required by audit.
    
    ledger_files = sorted(list(LEDGER_DIR.glob("*.yaml")))
    # Filter for relevant ones (smoke, neg_test, neg_test_boundary, neg_test_multi)
    relevant_ledgers = [f for f in ledger_files if any(x in f.name for x in ["_smoke_test_", "_neg_test_"])]
    
    if not relevant_ledgers:
         print(f"[ERROR] No ledger files found in {LEDGER_DIR}")
         sys.exit(1)
         
    artifacts.extend(relevant_ledgers)
    
    # 2. Generate Inventory
    print("[BUILDER] Generating Evidence_SHA256_Inventory.txt...")
    inventory_lines = []
    inventory_lines.append("# Evidence SHA256 Inventory")
    inventory_lines.append(f"Generated: {datetime.now().isoformat()}")
    inventory_lines.append("")
    inventory_lines.append("| Path | SHA256 |")
    inventory_lines.append("|------|--------|")
    
    # Prepare mapping for zip
    # Key: Arcname (repo-relative), Value: FS Path
    zip_mapping = {}
    
    # Pre-calculate to sort
    inv_entries = []
    
    for fs_path in artifacts:
        # Determine repo-relative path
        try:
            rel_path = fs_path.relative_to(REPO_ROOT).as_posix()
        except ValueError:
            # Fallback if outside (should not happen)
            rel_path = fs_path.name
            
        zip_mapping[rel_path] = fs_path
        sha = compute_sha256(fs_path)
        inv_entries.append((rel_path, sha))
        
    # Sort by path
    inv_entries.sort(key=lambda x: x[0])
    
    for path, sha in inv_entries:
        inventory_lines.append(f"| `{path}` | `{sha}` |")
        
    inventory_content = "\n".join(inventory_lines)
    inventory_path = REPO_ROOT / "artifacts" / "plans" / "Evidence_SHA256_Inventory.txt"
    inventory_path.write_text(inventory_content, encoding="utf-8")
    
    # Add inventory to zip mapping
    zip_mapping["artifacts/plans/Evidence_SHA256_Inventory.txt"] = inventory_path
    
    # 3. Create Zip
    date_str = datetime.now().strftime("%Y-%m-%d")
    zip_name = f"Bundle_CT2_CouncilDONE_{date_str}.zip"
    zip_out = BUNDLE_DIR / zip_name
    
    print(f"[BUILDER] Creating zip: {zip_out}")
    with zipfile.ZipFile(zip_out, "w", zipfile.ZIP_DEFLATED) as zf:
        for arcname, fs_path in zip_mapping.items():
            print(f"  Adding: {arcname}")
            zf.write(fs_path, arcname=arcname)
            
    # 4. Audit
    print("[BUILDER] Running Audit Gate...")
    audit_script = REPO_ROOT / "scripts" / "ct2_audit_check.py"
    result = subprocess.run([sys.executable, str(audit_script), str(zip_out)])
    
    if result.returncode != 0:
        print("[BUILDER] Audit FAILED. Deleting bundle.")
        if zip_out.exists():
            zip_out.unlink()
        sys.exit(1)
        
    print("[BUILDER] SUCCESS. Bundle ready.")
    print(f"Path: {zip_out}")

if __name__ == "__main__":
    main()
