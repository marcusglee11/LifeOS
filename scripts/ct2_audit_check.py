#!/usr/bin/env python3
"""CT-2 Audit Gate — Validates bundle integrity and CT2 packet evidence."""
import argparse
import hashlib
import zipfile
import sys
import re
from pathlib import Path

# --- Configuration ---
REQUIRED_LEDGER_PATTERNS = [
    r"_smoke_test_.*\.yaml",
    r"_neg_test_boundary_.*\.yaml",
    r"_neg_test_multi_.*\.yaml"
]

CT2_PACKET_PATH = "artifacts/plans/CT2_Activation_Packet_DocSteward_G3.md"

# Markers for deterministic parsing
LEDGER_EVIDENCE_START = "### 3.3 Ledger Evidence"
LEDGER_EVIDENCE_END = "### 3.4"

def compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()

def fail(msg: str):
    print(f"[FAIL] {msg}")
    sys.exit(1)

def pass_msg(msg: str):
    print(f"[PASS] {msg}")

def check_zip_structure(zip_ref: zipfile.ZipFile):
    for name in zip_ref.namelist():
        if "\\" in name:
            fail(f"ZIP_PATH_CANONICAL: Found backslash in path: {name}")
        if name.startswith("/") or ":" in name:
            fail(f"ZIP_PATH_CANONICAL: Absolute path or drive letter: {name}")
    pass_msg("ZIP structure canonical (POSIX paths)")

def check_evidence_inventory(zip_ref: zipfile.ZipFile):
    inv_path = "artifacts/plans/Evidence_SHA256_Inventory.txt"
    if inv_path not in zip_ref.namelist():
        if "Evidence_SHA256_Inventory.txt" in zip_ref.namelist():
            inv_path = "Evidence_SHA256_Inventory.txt"
        else:
            fail("INVENTORY_MATCH: Evidence_SHA256_Inventory.txt not found")
            
    print(f"[INFO] Parsing inventory: {inv_path}")
    inventory_content = zip_ref.read(inv_path).decode("utf-8")
    
    entries = []
    for line in inventory_content.splitlines():
        if line.strip().startswith("|") and "SHA256" not in line and "---" not in line:
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if len(parts) >= 2:
                path = parts[0].strip("`")
                sha = parts[1].strip("`")
                entries.append((path, sha))
                
    if not entries:
        fail("INVENTORY_MATCH: No entries found in inventory table")

    for path, expected_sha in entries:
        if path not in zip_ref.namelist():
            fail(f"EVIDENCE_MAP_PATHS_EXIST: Path in inventory not in zip: {path}")
            
        data = zip_ref.read(path)
        actual_sha = compute_sha256(data)
        if actual_sha != expected_sha:
            fail(f"SHA256_MATCH: Hash mismatch for {path}. Expected {expected_sha}, got {actual_sha}")
            
    pass_msg(f"Verified {len(entries)} inventory items (SHA256 match)")

def check_no_elisions(zip_ref: zipfile.ZipFile):
    log_file = None
    for name in zip_ref.namelist():
        if "Execution_Evidence" in name and name.endswith(".txt"):
            log_file = name
            break
            
    if not log_file:
        print("[WARN] NO_ELISIONS: No execution evidence log found to check.")
        return

    print(f"[INFO] Checking log for elisions: {log_file}")
    data = zip_ref.read(log_file)
    
    if b"..." in data:
        count = data.count(b"...")
        fail(f"NO_ELISIONS_IN_RAW_LOG: Found {count} occurrences of '...' in {log_file}")
        
    pass_msg("Log elision check passed (0 '...')")

def check_proof_coverage(zip_ref: zipfile.ZipFile):
    files = zip_ref.namelist()
    
    for pattern in REQUIRED_LEDGER_PATTERNS:
        if not any(re.search(pattern, f) for f in files):
            fail(f"PROOF_COVERAGE: Missing ledger matching pattern: {pattern}")
            
    multi_ledger = next((f for f in files if "_neg_test_multi_" in f and f.endswith(".yaml")), None)
    if multi_ledger:
        content = zip_ref.read(multi_ledger).decode("utf-8")
        if "match_count_found: 2" not in content:
            fail(f"PROOF_COVERAGE: Multi-match ledger does not show found: 2")
        
        if "HUNK_MATCH_COUNT_MISMATCH" not in content:
            fail(f"REASON_CODES: Multi-match ledger missing HUNK_MATCH_COUNT_MISMATCH")
            
    pass_msg("Proof coverage and reason codes verified")

def check_ct2_packet_evidence(zip_ref: zipfile.ZipFile):
    """P0: Validate CT2 packet ledger evidence against shipped artifacts."""
    # CT2_PACKET_EXISTS
    if CT2_PACKET_PATH not in zip_ref.namelist():
        fail(f"CT2_PACKET_EXISTS: CT2 packet not found at {CT2_PACKET_PATH}")
    
    print(f"[INFO] Parsing CT2 packet evidence: {CT2_PACKET_PATH}")
    packet_content = zip_ref.read(CT2_PACKET_PATH).decode("utf-8")
    
    # CT2_LEDGER_EVIDENCE_PARSE
    start_idx = packet_content.find(LEDGER_EVIDENCE_START)
    end_idx = packet_content.find(LEDGER_EVIDENCE_END)
    
    if start_idx == -1:
        fail(f"CT2_EVIDENCE_PARSE_FAILED: Could not find '{LEDGER_EVIDENCE_START}' marker")
    if end_idx == -1:
        end_idx = len(packet_content)  # Parse to end if no terminator
        
    evidence_block = packet_content[start_idx:end_idx]
    
    # Parse table rows
    entries = []
    for line in evidence_block.splitlines():
        if line.strip().startswith("|") and "Artifact Path" not in line and "---" not in line:
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if len(parts) >= 2:
                path = parts[0].strip("`")
                sha = parts[1].strip("`")
                entries.append((path, sha))
                
    if not entries:
        fail("CT2_EVIDENCE_PARSE_FAILED: No entries found in CT2 Ledger Evidence table")
    
    print(f"[INFO] Found {len(entries)} CT2 Ledger Evidence entries")
    
    # CT2_EVIDENCE_PATHS_EXIST + CT2_EVIDENCE_SHA256_MATCH
    for path, expected_sha in entries:
        if path not in zip_ref.namelist():
            fail(f"CT2_EVIDENCE_PATHS_EXIST: Path in CT2 packet not in zip: {path}")
            
        data = zip_ref.read(path)
        actual_sha = compute_sha256(data)
        if actual_sha != expected_sha:
            fail(f"CT2_EVIDENCE_SHA256_MATCH: Hash mismatch for {path}. Expected {expected_sha}, got {actual_sha}")
            
    pass_msg(f"CT2 packet evidence verified ({len(entries)} entries)")

def main():
    parser = argparse.ArgumentParser(description="Audit CT-2 Bundle")
    parser.add_argument("bundle_path", help="Path to the CT-2 zip bundle")
    args = parser.parse_args()
    
    zip_path = Path(args.bundle_path)
    if not zip_path.exists():
        fail(f"Bundle not found: {zip_path}")
        
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            print(f"Auditing: {zip_path.name}")
            check_zip_structure(zip_ref)
            check_evidence_inventory(zip_ref)
            check_no_elisions(zip_ref)
            check_proof_coverage(zip_ref)
            check_ct2_packet_evidence(zip_ref)  # P0: New check
            
        print("\n[SUCCESS] Audit Passed")
        
        report_path = Path("artifacts/ct2/CT2_AUDIT_REPORT.md")
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_content = f"""# CT-2 Audit Report

- **Bundle**: {zip_path.name}
- **Status**: PASS

## Checks Performed

1. ZIP_PATH_CANONICAL: PASS
2. INVENTORY_MATCH: PASS
3. NO_ELISIONS: PASS
4. PROOF_COVERAGE: PASS
5. CT2_PACKET_EVIDENCE: PASS
"""
        report_path.write_text(report_content)
        
    except zipfile.BadZipFile:
        fail("Invalid zip file")
    except Exception as e:
        fail(f"Audit exception: {e}")

if __name__ == "__main__":
    main()
