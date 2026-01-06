#!/usr/bin/env python3
import os
import sys
import json
import zipfile
import hashlib
import argparse
import subprocess
import shutil
import re
from datetime import datetime
from pathlib import Path

# --- Constants ---
SCHEMA_VERSION = "G-CBS-1.0"
# Determinism Constants (v1.1)
CANONICAL_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
EXTERNAL_ATTR_FILE = 0o644 << 16
ZIP_COMPRESSION = zipfile.ZIP_DEFLATED
ZIP_LEVEL = 9

def calculate_sha256(filepath):
    sha = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while True:
            data = f.read(65536)
            if not data: break
            sha.update(data)
    return sha.hexdigest().upper()

def get_git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"]).decode('utf-8').strip()
    except:
        return "UNKNOWN_COMMIT"

def create_addendum(manifest):
    lines = []
    lines.append(f"# Closure Addendum: {manifest['closure_id']}")
    lines.append(f"**Date**: {manifest['created_at']}")
    lines.append(f"**Commit**: {manifest['run_commit']}")
    lines.append(f"**Profile**: {manifest['profile']['name']} v{manifest['profile']['version']}")
    lines.append("\n## Evidence Inventory")
    lines.append("| Role | Path | SHA256 |")
    lines.append("|------|------|--------|")
    
    # Sort evidence table
    sorted_idx = sorted(manifest['evidence'], key=lambda x: x['path'])
    for item in sorted_idx:
        lines.append(f"| {item['role']} | `{item['path']}` | `{item['sha256']}` |")
        
    lines.append("\n## Asserted Invariants")
    for inv in manifest['invariants_asserted']:
        lines.append(f"- {inv}")
        
    return "\n".join(lines) + "\n"

def run_command_capture(cmd_list, output_path, cwd=None):
    print(f"Executing: {' '.join(cmd_list)}")
    # Use explicit encoding/buffering to avoid drift
    try:
        # Popen to capture both streams
        result = subprocess.run(cmd_list, capture_output=True, text=True, cwd=cwd)
        
        # Normalize line endings to \n
        content_lines = []
        content_lines.append(f"Command: {' '.join(cmd_list)}")
        content_lines.append(f"CWD: {cwd or os.getcwd()}")
        content_lines.append(f"Exit Code: {result.returncode}")
        content_lines.append("")
        content_lines.append("STDOUT:")
        content_lines.append(result.stdout if result.stdout else "(empty)")
        content_lines.append("")
        content_lines.append("STDERR:")
        content_lines.append(result.stderr if result.stderr else "(empty)")
        content_lines.append("") # Trailing newline
        
        content = "\n".join(content_lines)
        content = content.replace("\r\n", "\n")
        
        if re.search(r"(Sample evidence|Placeholder)", content, re.IGNORECASE):
            print(f"CRITICAL: Placeholder detected in {output_path}")
            sys.exit(1)
            
        with open(output_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        return result.returncode
    except Exception as e:
        print(f"Error running command: {e}")
        sys.exit(1)

def build_zip_artifact(manifest, evidence_files, output_path):
    # evidence_files: list of (local_path, archive_name, role)
    
    # Write metadata files
    with open("closure_manifest.json", "w", encoding="utf-8", newline="\n") as f:
        json.dump(manifest, f, indent=2)
    # Ensure newline at end of json? json.dump doesn't add it.
    
    addendum = create_addendum(manifest)
    with open("closure_addendum.md", "w", encoding="utf-8", newline="\n") as f:
        f.write(addendum)

    with zipfile.ZipFile(output_path, 'w', ZIP_COMPRESSION) as zf:
        # 1. Add Metadata (Canonical)
        for fname in ["closure_manifest.json", "closure_addendum.md"]:
            zinfo = zipfile.ZipInfo(fname, date_time=CANONICAL_TIMESTAMP)
            zinfo.compress_type = ZIP_COMPRESSION
            zinfo.external_attr = EXTERNAL_ATTR_FILE
            
            with open(fname, "rb") as f:
                zf.writestr(zinfo, f.read())

        # 2. Add Evidence (Sorted, Canonical)
        # evidence_files might have duplicates or different roles, handle uniq paths
        seen_paths = set()
        for local, arcname, _ in sorted(evidence_files, key=lambda x: x[1]):
            if arcname in seen_paths: continue
            seen_paths.add(arcname)
            
            zinfo = zipfile.ZipInfo(arcname, date_time=CANONICAL_TIMESTAMP)
            zinfo.compress_type = ZIP_COMPRESSION
            zinfo.external_attr = EXTERNAL_ATTR_FILE
            
            with open(local, "rb") as f:
                zf.writestr(zinfo, f.read())
    
    # Clean temp metadata
    os.remove("closure_manifest.json")
    os.remove("closure_addendum.md")

def main():
    parser = argparse.ArgumentParser(description="G-CBS Bundle Builder (v1.1)")
    parser.add_argument("--profile", required=True, help="Profile name")
    parser.add_argument("--closure-id", help="Closure ID")
    parser.add_argument("--output", default="bundle.zip", help="Output zip path")
    parser.add_argument("--repayment-mode", action="store_true", help="Run strictly defined repayment evidence generation")
    parser.add_argument("--deterministic", action="store_true", help="Enforce deterministic build (timestamps, sorting)")
    
    # Legacy/Manual args
    parser.add_argument("--include", help="List of evidence files")
    
    args = parser.parse_args()
    
    # Ensure clean slate
    work_dir = Path("temp_repayment_work").resolve()
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir()
    
    evidence_dir = work_dir / "evidence"
    evidence_dir.mkdir()
    
    commit = get_git_commit()
    timestamp = "1980-01-01T00:00:00" if args.deterministic else datetime.now().isoformat()
    
    collected_evidence = [] # (local, arcname, role)
    
    # --- PHASE 1: Collect/Generate Evidence ---
    if args.repayment_mode:
        print("Required Mode: Repayment (Generating Strict Evidence)")
        
        # G1: TDD Compliance
        g1_out = evidence_dir / "pytest_tdd_compliance.txt"
        run_command_capture([sys.executable, "-m", "pytest", "tests_doc/test_tdd_compliance.py"], g1_out)
        collected_evidence.append((str(g1_out), "evidence/pytest_tdd_compliance.txt", "tdd_gate"))
        
        # G2: Bundle Tests (Determinism)
        g2_out = evidence_dir / "pytest_bundle_tests.txt"
        run_command_capture([sys.executable, "-m", "pytest", "scripts/closure/tests/"], g2_out)
        collected_evidence.append((str(g2_out), "evidence/pytest_bundle_tests.txt", "tests_bundle"))
        
        # Placeholder for validator run (G3) - handled in Phase 2
    
    elif args.include:
        print("Manual Mode: Using provided include list")
        with open(args.include, 'r') as f:
            paths = [l.strip() for l in f if l.strip()]
        for p in paths:
            if not os.path.exists(p):
                print(f"Missing: {p}")
                sys.exit(1)
            sha = calculate_sha256(p)
            
            # Relativize path
            if os.path.isabs(p):
                try:
                    p_rel = os.path.relpath(p, os.getcwd())
                except ValueError:
                    p_rel = os.path.basename(p) # Fallback if on different drive
            else:
                p_rel = p
                
            arc = p_rel.replace("\\", "/") # Normalize
            if arc.startswith("./"): arc = arc[2:]
            
            # Simple role heuristic
            role = "other"
            if "log" in arc: role = "raw_log"
            
            collected_evidence.append((p, arc, role))
            
    else:
        print("Error: Must specify --repayment-mode or --include")
        sys.exit(1)

    # --- PHASE 2: Two-Stage Build (Circular Dependency Resolution) ---
    
    # Common Manifest Data
    manifest_base = {
        "schema_version": SCHEMA_VERSION,
        "closure_id": args.closure_id or f"{args.profile}_{timestamp[:10]}_{commit[:8]}",
        "closure_type": "STEP_GATE_CLOSURE",
        "run_commit": commit,
        "created_at": timestamp,
        "commands": ["[deterministic-build]"] if args.deterministic else [" ".join(sys.argv)],
        "invariants_asserted": ["G-CBS-1.0-COMPLIANT", "G-CBS-1.1-DETACHED-DIGEST"],
        "profile": {"name": args.profile, "version": "1.2.2"},
        "zip_sha256": "DETACHED_SEE_SIBLING_FILE", # v1.1 protocol
        "waiver": None,
        "gcbs_standard_version": "1.0",
        "activated_protocols_ref": "docs/01_governance/ARTEFACT_INDEX.json",
        "activated_protocols_sha256": "5A5B11D89F234DEF7CFE812C57364F3C5BBD4769A389674802D7B80FA0E67EB7"
    }
    
    # Candidate Build (Correct Filename for Transcript Accuracy)
    if args.repayment_mode:
        print("Building Candidate Bundle for Validator Capture...")
        
        # Prepare Candidate Directory and Filename
        candidate_dir = work_dir / "candidate"
        candidate_dir.mkdir()
        # Strictly use the output filename (e.g. Bundle_...v1.2.2.zip) for the candidate
        # so the validator logs the correct filename.
        final_filename = os.path.basename(args.output)
        candidate_zip = candidate_dir / final_filename
        
        draft_manifest = manifest_base.copy()
        
        # Build evidence list for candidate
        draft_ev_list = []
        for local, arc, role in collected_evidence:
            draft_ev_list.append({
                "path": arc,
                "sha256": calculate_sha256(local),
                "role": role
            })
        draft_manifest["evidence"] = draft_ev_list
        
        build_zip_artifact(draft_manifest, collected_evidence, str(candidate_zip))
        
        # Create Candidate Sidecar (for strict validation)
        candidate_sha = calculate_sha256(str(candidate_zip))
        candidate_sidecar = candidate_zip.with_name(candidate_zip.name + ".sha256")
        with open(candidate_sidecar, "w", encoding="utf-8", newline="\n") as f:
            f.write(f"{candidate_sha}  {candidate_zip.name}\n")

        # Run Strict Validator on Candidate (Capture)
        print("Running Strict Validator on Candidate (Capture)...")
        val_out = evidence_dir / "validator_run_shipped.txt"
        val_script = os.path.join(os.path.dirname(__file__), "validate_closure_bundle.py")
        
        # Strict run on candidate
        cmd = [sys.executable, val_script, str(candidate_zip), 
               "--output", str(work_dir / "candidate_report.md"), 
               "--deterministic"]
        
        code = run_command_capture(cmd, val_out, cwd=str(candidate_dir))
        if code != 0:
            print("CRITICAL: Candidate validation failed!")
            sys.exit(1)
            
        collected_evidence.append((str(val_out), "evidence/validator_run_shipped.txt", "validator_final_shipped"))

    # --- PHASE 3: Final Build ---
    print("Building Final Bundle...")
    final_manifest = manifest_base.copy()
    
    # Calculate Final Evidence SHAs
    final_ev_list = []
    for local, arc, role in collected_evidence:
        final_ev_list.append({
            "path": arc,
            "sha256": calculate_sha256(local),
            "role": role
        })
    final_manifest["evidence"] = final_ev_list
    
    build_zip_artifact(final_manifest, collected_evidence, args.output)
    
    # --- PHASE 4: Post-Process (Audit Report & Sidecar) ---
    
    # Generate Official Audit Report via Validator (on Final Zip)
    # We use --skip-digest-verification because sidecar isn't written yet
    print("Generating Audit Report...")
    val_script = os.path.join(os.path.dirname(__file__), "validate_closure_bundle.py")
    subprocess.run([sys.executable, val_script, args.output, 
                    "--output", "audit_report.md", 
                    "--deterministic", "--skip-digest-verification"], check=True)
                    
    # Seal Bundle with Report
    print("Sealing Bundle...")
    with zipfile.ZipFile(args.output, 'a', ZIP_COMPRESSION) as zf:
        zinfo = zipfile.ZipInfo("audit_report.md", date_time=CANONICAL_TIMESTAMP)
        zinfo.compress_type = ZIP_COMPRESSION
        zinfo.external_attr = EXTERNAL_ATTR_FILE
        with open("audit_report.md", "rb") as f:
            zf.writestr(zinfo, f.read())
    
    # DETACHED DIGEST (Gate 0)
    print("Computing Detached Digest...")
    final_sha = calculate_sha256(args.output)
    sidecar_path = Path(args.output).with_name(Path(args.output).name + ".sha256")
    with open(sidecar_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(f"{final_sha}  {os.path.basename(args.output)}\n")
        
    print(f"Sidecar written: {sidecar_path}")
    
    # --- PHASE 5: Final Verification ---
    print("Running Final Verification (Gate 0 Strict)...")
    # Now we run validator WITHOUT skip-digest. It checks sidecar.
    subprocess.run([sys.executable, val_script, args.output, "--deterministic"], check=True)
    
    # Cleanup
    if os.path.exists("audit_report.md"): os.remove("audit_report.md")
    if work_dir.exists(): shutil.rmtree(work_dir)
    
    print(f"SUCCESS. Bundle: {args.output}")

if __name__ == "__main__":
    main()
