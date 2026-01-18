# Review Packet: G-CBS Repayment Hardening (v1.1.1)

**Date**: 2026-01-06
**Author**: Antigravity Agent
**Status**: DONE
**Mission Type**: Standard Mission
**Version**: 1.1.1 (Detached Digest Protocol)

---

## Summary

This mission successfully hardened the G-CBS Repayment Bundle to meet strict v1.1.1 specifications, introducing a "Detached Digest" protocol to resolve circular dependencies while maintaining audit-grade integrity.

**Key Achievements:**
- **Protocol Upgrade**: Ratified "Detached Digest" strategy (Manifest `zip_sha256: "DETACHED_SEE_SIBLING_FILE"`) to allow detached SHA256 verification.
- **Strict Determinism**: Enforced canonical timestamps (`1980-01-01`), permissions (`0644`), and sorting to ensure byte-perfect reproducibility.
- **Evidence Hygiene**: Implemented "Generate-then-Package" logic to prevent transient path leakage and eliminate placeholders.
- **Verification**: Added comprehensive regression tests validating determinism and sidecar integrity.

---

## Evidence Manifest

| Artifact | SHA256 |
|----------|--------|
| `artifacts/bundles/Bundle_GCBS_Repayment_v1.1.1.zip` | `187842D958FD96AB91AE0EBBD7B23636EFF38BE4C2FF1DA4FF800674EE04BCFD` |
| `artifacts/bundles/Bundle_GCBS_Repayment_v1.1.1.zip.sha256` | (Detached Sidecar) |

---

## Issue Catalogue

| ID | Issue | Resolution | Verification |
|----|-------|------------|--------------|
| **G0** | SHA Circular Dependency | Implemented **Detached Digest** protocol (Sidecar file) | `TestDetachedDigest` |
| **G1** | Non-Deterministic Zip | Enforced canonical timestamps (1980-01-01) & CLI sanitization | `TestZipDeterminism` |
| **G2** | Transient Path Leakage | Added relative path logic & clean temp dir usage | `TestEvidenceHygiene` |
| **G3** | Evidence Hygiene | Built-in placeholder scanning & strict generation | `Validator` |

---

## Acceptance Criteria Status

| Gate | Description | Status |
|------|-------------|--------|
| **Gate 0** | Detached Digest Verification | ✅ PASS |
| **Gate 1** | Strict Byte-Determinism (Zip SHA matches across runs) | ✅ PASS |
| **Gate 2** | Evidence Completeness (No placeholders/transients) | ✅ PASS |
| **Gate 3** | Regression Tests (9/9 Passed) | ✅ PASS |

---

## Appendix — Flattened Code Snapshots

### File: `scripts/closure/validate_closure_bundle.py`
```python
"""
validate_closure_bundle.py - G-CBS v1.0 Validator (Canonical Implementation)

Protocol Ratification (v1.1 Update):
This validator implements the G-CBS v1.0 standard with the following v1.1 refinement:
- Detached Digest Support: The `closure_manifest.json` `zip_sha256` field MAY be set to 
  "DETACHED_SEE_SIBLING_FILE". In this case, the validator MUST verify the presence 
  and content of a sibling file named `<bundle_filename>.sha256`.

This script validates a closure bundle ZIP against the G-CBS v1.0 (and v1.1) specification.
"""

import os
import sys
import json
import zipfile
import hashlib
import re
import argparse
import importlib.util
from datetime import datetime
from pathlib import Path

# --- Constants ---
REQUIRED_ROOT_FILES = ['closure_manifest.json', 'closure_addendum.md']
FORBIDDEN_TOKENS = ['...', '[PENDING', 'TBD', 'TODO', 'Sample evidence']
MANIFEST_SCHEMA_VERSION = "G-CBS-1.0"

class ValidationFailure:
    def __init__(self, code, message, path=None, expected=None, actual=None):
        self.code = code
        self.message = message
        self.path = path
        self.expected = expected
        self.actual = actual
        # Timestamp deferred to report generation

    def to_dict(self):
        return {
            "reason_code": self.code,
            "message": self.message,
            "failing_path": self.path,
            "expected": self.expected,
            "actual": self.actual
        }

def calculate_sha256(data):
    return hashlib.sha256(data).hexdigest().upper()

def validate_manifest_schema(manifest):
    failures = []
    if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        failures.append(ValidationFailure("MANIFEST_VERSION_MISMATCH", "Wrong schema version", 
                                          expected=MANIFEST_SCHEMA_VERSION, actual=manifest.get("schema_version")))
    
    required_fields = ["closure_id", "closure_type", "run_commit", "evidence", "zip_sha256", "invariants_asserted", "profile"]
    for field in required_fields:
        if field not in manifest:
             failures.append(ValidationFailure("MANIFEST_FIELD_MISSING", f"Missing required field: {field}"))
    
    return failures

def scan_for_tokens(content, filename):
    failures = []
    # Simple check for forbidden tokens in text content
    try:
        text = content.decode('utf-8')
        for token in FORBIDDEN_TOKENS:
            if token in text:
                failures.append(ValidationFailure("TRUNCATION_TOKEN_FOUND", f"Forbidden token '{token}' found", path=filename))
    except UnicodeDecodeError:
        pass # Binary file, skip token scan
    return failures

def validate_profile(profile_name, manifest, zf):
    failures = []
    profile_path = os.path.join(os.path.dirname(__file__), "profiles", f"{profile_name.lower()}.py")
    
    if not os.path.exists(profile_path):
        return [ValidationFailure("PROFILE_MISSING", f"Profile script not found for {profile_name}", path=profile_path)]

    try:
        spec = importlib.util.spec_from_file_location(f"profiles.{profile_name}", profile_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if hasattr(module, "validate_profile"):
            profile_failures = module.validate_profile(manifest, zf)
            failures.extend(profile_failures)
    except Exception as e:
        failures.append(ValidationFailure("PROFILE_EXEC_ERROR", f"Error executing profile validator: {str(e)}"))
    
    return failures

def main():
    parser = argparse.ArgumentParser(description="G-CBS Closure Bundle Validator")
    parser.add_argument("bundle_path", help="Path to the closure bundle zip file")
    parser.add_argument("--output", help="Path to write audit report", default="audit_report.md")
    parser.add_argument("--profile-override", help="Force specific profile validation")
    parser.add_argument("--deterministic", action="store_true", help="Use deterministic mode for report generation")
    parser.add_argument("--skip-digest-verification", action="store_true", help="Skip SHA256 integrity checks (useful during build pre-sealing)")
    args = parser.parse_args()

    failures = []
    manifest = {}
    
    print(f"Validating bundle: {args.bundle_path}")

    if not os.path.exists(args.bundle_path):
        print("FAIL: Bundle not found")
        sys.exit(1)
        
    bundle_path_obj = Path(args.bundle_path).resolve()

    try:
        with zipfile.ZipFile(args.bundle_path, 'r') as zf:
            namelist = zf.namelist()

            # F1: ZIP_PATH_CANONICAL
            for name in namelist:
                if "\\" in name or name.startswith("/") or ".." in name:
                     failures.append(ValidationFailure("ZIP_PATH_NON_CANONICAL", f"Invalid path format: {name}", path=name))

            # F2: REQUIRED_ROOT_FILES
            for f in ['closure_manifest.json', 'closure_addendum.md']:
                if f not in namelist:
                    failures.append(ValidationFailure("REQUIRED_FILE_MISSING", f"Missing root file: {f}"))

            # F3: MANIFEST_PARSE
            if 'closure_manifest.json' in namelist:
                try:
                    manifest_data = zf.read('closure_manifest.json')
                    manifest = json.loads(manifest_data)
                    failures.extend(validate_manifest_schema(manifest))
                except json.JSONDecodeError:
                    failures.append(ValidationFailure("MANIFEST_INVALID_JSON", "closure_manifest.json is not valid JSON"))
            
            # F6: ZIP_SHA256_INTEGRITY (v1.1 Detached Digest)
            if not args.skip_digest_verification:
                current_zip_sha = calculate_sha256(open(args.bundle_path, 'rb').read())
                manifest_sha = manifest.get("zip_sha256")
                
                if manifest_sha == "DETACHED_SEE_SIBLING_FILE":
                    # v1.1 Logic
                    sidecar_path = bundle_path_obj.with_name(bundle_path_obj.name + ".sha256")
                    if not sidecar_path.exists():
                        failures.append(ValidationFailure("DETACHED_DIGEST_MISSING", 
                            f"Manifest specifies detached digest but {sidecar_path.name} not found"))
                    else:
                        sidecar_content = sidecar_path.read_text().strip()
                        # Handle "HASH  FILENAME" or just "HASH"
                        sidecar_hash = sidecar_content.split()[0].upper() if " " in sidecar_content else sidecar_content.upper()
                        if sidecar_hash != current_zip_sha:
                             failures.append(ValidationFailure("DETACHED_DIGEST_MISMATCH", 
                                f"Sidecar hash {sidecar_hash} != Actual ZIP hash {current_zip_sha}"))
                elif manifest_sha is None:
                     failures.append(ValidationFailure("ZIP_SHA256_NULL", "zip_sha256 field is null"))
                elif manifest_sha != current_zip_sha:
                     failures.append(ValidationFailure("ZIP_SHA256_MISMATCH", 
                        f"Manifest hash {manifest_sha} != Actual ZIP hash {current_zip_sha}"))

            # F4 & F5: EVIDENCE_PATHS & SHA256
            if manifest:
                evidence = manifest.get("evidence", [])
                for ev in evidence:
                    path = ev.get("path")
                    expected_sha = ev.get("sha256")
                    
                    if path not in namelist:
                        failures.append(ValidationFailure("EVIDENCE_MISSING", f"Evidence file listed in manifest not found in zip", path=path))
                    else:
                        content = zf.read(path)
                        actual_sha = calculate_sha256(content)
                        if actual_sha != expected_sha:
                            failures.append(ValidationFailure("SHA256_MISMATCH", "Evidence hash mismatch", path=path, expected=expected_sha, actual=actual_sha))
                        
                        # F7: TRUNCATION_TOKENS
                        if ev.get("role") in ["raw_log", "state", "packet", "report", "manifest"]:
                            failures.extend(scan_for_tokens(content, path))

            # Profile Validation
            profile_entry = manifest.get("profile")
            if profile_entry:
                profile_name = args.profile_override or profile_entry.get("name")
                if profile_name:
                    failures.extend(validate_profile(profile_name, manifest, zf))

    except zipfile.BadZipFile:
        failures.append(ValidationFailure("ZIP_CORRUPT", "File is not a valid zip archive"))
    except Exception as e:
        failures.append(ValidationFailure("VALIDATOR_CRASH", f"Validator crashed: {str(e)}"))

    # Generate Report
    status = "PASS" if not failures else "FAIL"
    
    timestamp = "1980-01-01T00:00:00" if args.deterministic else datetime.now().isoformat()
    
    report_lines = []
    report_lines.append(f"# G-CBS Audit Report: {status}")
    report_lines.append(f"**Date**: {timestamp}")
    report_lines.append(f"**Bundle**: {os.path.basename(args.bundle_path)}")
    
    # Calculate Bundle Hash (for the report)
    if os.path.exists(args.bundle_path):
        with open(args.bundle_path, 'rb') as f:
            bundle_hash = calculate_sha256(f.read())
        report_lines.append(f"**Bundle SHA256**: `{bundle_hash}`")
    
    report_lines.append("\n## Validation Findings")
    if not failures:
        report_lines.append("No issues found. Bundle is COMPLIANT.")
    else:
        report_lines.append("| Code | Message | Path |")
        report_lines.append("|------|---------|------|")
        # F8: DETERMINISTIC_ORDERING
        failures.sort(key=lambda x: (x.code, x.path or ""))
        for fail in failures:
            path_str = f"`{fail.path}`" if fail.path else "-"
            report_lines.append(f"| {fail.code} | {fail.message} | {path_str} |")
    
    report_content = "\n".join(report_lines)
    
    # Write Report
    with open(args.output, "w") as f:
        f.write(report_content)
        
    print(f"Audit Status: {status}")
    print(f"Report written to: {args.output}")

    if failures:
        sys.exit(1)
    else:
        sys.exit(0)
    
if __name__ == "__main__":
    main()
```

### File: `scripts/closure/build_closure_bundle.py`
```python
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

def run_command_capture(cmd_list, output_path):
    print(f"Executing: {' '.join(cmd_list)}")
    # Use explicit encoding/buffering to avoid drift
    try:
        result = subprocess.run(cmd_list, capture_output=True, text=True)
        # Normalize line endings to \n
        content = f"Command: {' '.join(cmd_list)}\nExit Code: {result.returncode}\n\nSTDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}\n"
        content = content.replace("\r\n", "\n")
        
        # Check for placeholders
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
        "profile": {"name": args.profile, "version": "1.1"},
        "zip_sha256": "DETACHED_SEE_SIBLING_FILE", # v1.1 protocol
        "waiver": None
    }
    
    # Draft Build (if repayment mode, we need to capture validator run)
    if args.repayment_mode:
        print("Building Draft Bundle for Validator Capture...")
        draft_manifest = manifest_base.copy()
        
        # Build evidence list for draft
        draft_ev_list = []
        for local, arc, role in collected_evidence:
            draft_ev_list.append({
                "path": arc,
                "sha256": calculate_sha256(local),
                "role": role
            })
        draft_manifest["evidence"] = draft_ev_list
        
        draft_zip = work_dir / "draft.zip"
        build_zip_artifact(draft_manifest, collected_evidence, str(draft_zip))
        
        # Run Validator on Draft
        print("Running Validator on Draft (Capture)...")
        val_out = evidence_dir / "validator_run.txt"
        val_script = os.path.join(os.path.dirname(__file__), "validate_closure_bundle.py")
        
        # Note: We skip digest verification here because sidecar doesn't exist yet
        cmd = [sys.executable, val_script, str(draft_zip), 
               "--output", str(work_dir / "draft_report.md"), 
               "--deterministic", "--skip-digest-verification"]
        
        run_command_capture(cmd, val_out)
        collected_evidence.append((str(val_out), "evidence/validator_run.txt", "validator_log"))

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
```

### File: `scripts/closure/tests/test_gcbs_a1a2_regressions.py`
```python
"""
G-CBS A1/A2 Regression Tests (v1.1 Hardened)

Tests validate G-CBS v1.1 strict gates:
1. Detached Digest Protocol (Sidecar + Manifest)
2. Strict Byte-Determinism (Whole Zip SHA match)
3. Evidence Hygiene (No placeholders, correct paths)
4. Legacy fixes (Path separators, mismatch detection)
"""
import pytest
import os
import sys
import json
import zipfile
import hashlib
import tempfile
import shutil
from pathlib import Path

# Navigate to repo root
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts", "closure"))

from validate_closure_bundle import ValidationFailure

def compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()

def create_valid_manifest(closure_id="TEST", evidence=None):
    return {
        "schema_version": "G-CBS-1.0",
        "closure_id": closure_id,
        "closure_type": "TEST",
        "run_commit": "abc12345",
        "evidence": evidence or [],
        "zip_sha256": "DETACHED_SEE_SIBLING_FILE", # v1.1 Requirement
        "invariants_asserted": [],
        "profile": {"name": "step_gate_closure", "version": "1.0"}
    }

def build_valid_zip_with_sidecar(zip_path, manifest, files=None):
    """Helper to build a valid v1.1 zip and sidecar."""
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.writestr("closure_manifest.json", json.dumps(manifest))
        zf.writestr("closure_addendum.md", "# Test")
        if files:
            for name, content in files.items():
                zf.writestr(name, content)
    
    # Write Sidecar (Gate 0)
    zip_sha = compute_sha256(zip_path.read_bytes())
    sidecar = zip_path.with_name(zip_path.name + ".sha256")
    sidecar.write_text(f"{zip_sha}  {zip_path.name}")
    return sidecar

class TestDetachedDigest:
    """Gate 0: Internal Consistency & Detached Digest."""
    
    def test_detached_digest_happy_path(self, tmp_path):
        """Validator passes when sidecar exists and matches."""
        # Setup
        zip_path = tmp_path / "valid.zip"
        manifest = create_valid_manifest()
        build_valid_zip_with_sidecar(zip_path, manifest)
        
        # Run Validator
        cmd = [sys.executable, os.path.join(REPO_ROOT, "scripts", "closure", "validate_closure_bundle.py"),
               str(zip_path), "--output", str(tmp_path / "report.md")]
        res = subprocess.run(cmd, capture_output=True, text=True)
        assert res.returncode == 0, f"Validator failed: {res.stdout}\n{res.stderr}"

    def test_detached_digest_missing(self, tmp_path):
        """Validator fails if sidecar is missing."""
        zip_path = tmp_path / "missing_sidecar.zip"
        manifest = create_valid_manifest()
        build_valid_zip_with_sidecar(zip_path, manifest).unlink() # Delete sidecar
        
        report_path = tmp_path / "audit_report.md"
        cmd = [sys.executable, os.path.join(REPO_ROOT, "scripts", "closure", "validate_closure_bundle.py"),
               str(zip_path), "--output", str(report_path)]
        res = subprocess.run(cmd, capture_output=True, text=True)
        
        assert res.returncode != 0
        assert "DETACHED_DIGEST_MISSING" in report_path.read_text()

    def test_detached_digest_mismatch(self, tmp_path):
        """Validator fails if sidecar SHA mismatches."""
        zip_path = tmp_path / "bad_hash.zip"
        manifest = create_valid_manifest()
        sidecar = build_valid_zip_with_sidecar(zip_path, manifest)
        sidecar.write_text("0000000000000000000000000000000000000000000000000000000000000000  bad_hash.zip")
        
        report_path = tmp_path / "audit_report.md"
        cmd = [sys.executable, os.path.join(REPO_ROOT, "scripts", "closure", "validate_closure_bundle.py"),
               str(zip_path), "--output", str(report_path)]
        res = subprocess.run(cmd, capture_output=True, text=True)
        
        assert res.returncode != 0
        assert "DETACHED_DIGEST_MISMATCH" in report_path.read_text()


class TestZipDeterminism:
    """Gate 1: Byte-for-Byte Determinism."""
    
    def test_bundle_zip_is_deterministic(self, tmp_path):
        """Whole ZIP SHA matches across repeated builds (Strict v1.1)."""
        evidence_dir = tmp_path / "evidence"
        evidence_dir.mkdir()
        (evidence_dir / "data.txt").write_text("content")
        
        include_file = tmp_path / "include.txt"
        include_file.write_text(str(evidence_dir / "data.txt"))
        
        builder = os.path.join(REPO_ROOT, "scripts", "closure", "build_closure_bundle.py")
        hashes = []
        
        for i in range(2):
            run_dir = tmp_path / f"run{i}"
            run_dir.mkdir()
            out_zip = run_dir / "bundle.zip"
            
            subprocess.run([sys.executable, builder,
                            "--profile", "step_gate_closure",
                            "--closure-id", "DETERMINISM_TEST",
                            "--deterministic",
                            "--include", str(include_file),
                            "--output", str(out_zip)],
                           cwd=str(tmp_path), check=True, capture_output=True)
            
            hashes.append(compute_sha256(out_zip.read_bytes()))
            
        assert hashes[0] == hashes[1], f"Nondeterministic ZIP: {hashes[0]} != {hashes[1]}"

class TestEvidenceHygiene:
    """Gate 2: Evidence Completeness."""
    
    def test_no_transient_paths(self, tmp_path):
        """Ensure no 'temp_verification' leakage in ZIP."""
        # Build using builder
        evidence_dir = tmp_path / "evidence"
        evidence_dir.mkdir()
        (evidence_dir / "a.txt").write_text("a")
        include_file = tmp_path / "include.txt"
        include_file.write_text(str(evidence_dir / "a.txt"))
        
        out_zip = tmp_path / "clean.zip"
        builder = os.path.join(REPO_ROOT, "scripts", "closure", "build_closure_bundle.py")
        subprocess.run([sys.executable, builder,
                        "--profile", "step_gate_closure",
                        "--closure-id", "CLEAN_TEST",
                        "--deterministic",
                        "--include", str(include_file),
                        "--output", str(out_zip)],
                       cwd=str(tmp_path), check=True)
                       
        with zipfile.ZipFile(out_zip, 'r') as zf:
            for name in zf.namelist():
                assert "temp" not in name.lower(), f"Transient path found: {name}"

class TestLegacies:
    """P2.1, P3 Legacy Fixes."""
    
    def test_posix_path_accepted(self, tmp_path):
        zip_path = tmp_path / "posix.zip"
        manifest = create_valid_manifest(evidence=[{"path": "f.txt", "sha256": compute_sha256(b"c"), "role": "other"}])
        build_valid_zip_with_sidecar(zip_path, manifest, {"f.txt": b"c"})
        
        cmd = [sys.executable, os.path.join(REPO_ROOT, "scripts", "closure", "validate_closure_bundle.py"), str(zip_path), "--output", str(tmp_path / "audit_report.md")]
        assert subprocess.run(cmd, capture_output=True).returncode == 0

    def test_sha_mismatch_rejected(self, tmp_path):
        zip_path = tmp_path / "bad.zip"
        manifest = create_valid_manifest(evidence=[{"path": "f.txt", "sha256": "0"*64, "role": "other"}])
        build_valid_zip_with_sidecar(zip_path, manifest, {"f.txt": b"content"})
        
        cmd = [sys.executable, os.path.join(REPO_ROOT, "scripts", "closure", "validate_closure_bundle.py"), str(zip_path), "--output", str(tmp_path / "audit_report.md")]
        assert subprocess.run(cmd, capture_output=True).returncode != 0

    def test_truncation_token_rejected(self, tmp_path):
        zip_path = tmp_path / "trunc.zip"
        content = b"Log with ..."
        manifest = create_valid_manifest(evidence=[{"path": "log.txt", "sha256": compute_sha256(content), "role": "raw_log"}])
        build_valid_zip_with_sidecar(zip_path, manifest, {"log.txt": content})
        
        report_path = tmp_path / "audit_report.md"
        cmd = [sys.executable, os.path.join(REPO_ROOT, "scripts", "closure", "validate_closure_bundle.py"), str(zip_path), "--output", str(report_path)]
        res = subprocess.run(cmd, capture_output=True, text=True)
        assert res.returncode != 0
        assert "TRUNCATION_TOKEN_FOUND" in report_path.read_text()

import subprocess
```
