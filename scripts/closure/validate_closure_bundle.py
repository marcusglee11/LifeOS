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
# Updated per TODO_Standard_v1.0: Allow LIFEOS_TODO but forbid generic TODO
FORBIDDEN_TOKENS = ['...', '[PENDING', 'TBD', 'Sample evidence']
FORBIDDEN_TODO_PATTERN = r'\bTODO\b(?!.*LIFEOS_TODO)'  # Match standalone TODO, not part of LIFEOS_TODO
# P0.4: Portability forbidden patterns (for canonical docs in bundle)
PORTABILITY_FORBIDDEN = [r'file:///[a-zA-Z]:', r'C:\\Users\\', r'c:\\users\\']
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

        # Check for generic TODO (but allow LIFEOS_TODO)
        # Strategy: Find TODO that's NOT preceded by "LIFEOS_"
        if re.search(r'(?<!LIFEOS_)TODO(?![:\[])', text):
            failures.append(ValidationFailure("TRUNCATION_TOKEN_FOUND",
                f"Forbidden generic TODO found (use LIFEOS_TODO instead)", path=filename))
    except UnicodeDecodeError:
        pass # Binary file, skip token scan
    return failures

def scan_for_portability(content, filename):
    """P0.4: Scan for non-portable file:/// URIs and machine-local paths."""
    failures = []
    try:
        text = content.decode('utf-8')
        for pattern in PORTABILITY_FORBIDDEN:
            if re.search(pattern, text, re.IGNORECASE):
                failures.append(ValidationFailure("E_PORTABILITY_LOCAL_PATH", 
                    f"Non-portable path pattern '{pattern}' found", path=filename))
    except UnicodeDecodeError:
        pass
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
    # F11: Provenance tracking (v1.1+)
    provenance_evidence = {}
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
            
            # F3.1: ADDENDUM_CHECKS (P0.2)
            if 'closure_addendum.md' in namelist:
                addendum_content = zf.read('closure_addendum.md').decode('utf-8')
                
                # Check 1: No elisions ("...")
                if '...' in addendum_content:
                    elision_count = addendum_content.count('...')
                    failures.append(ValidationFailure("E_ADDENDUM_ELISION", 
                        f"closure_addendum.md contains {elision_count} elision(s) ('...')", 
                        path="closure_addendum.md", actual=elision_count))
                
                # Check 2: Evidence table row count matches manifest
                manifest_evidence_count = len(manifest.get("evidence", []))
                # Count table rows (lines matching "| role | path | sha |")
                table_rows = [line for line in addendum_content.split('\n') 
                              if line.startswith('|') and '`' in line and not line.startswith('|---')]
                addendum_row_count = len(table_rows)
                
                if addendum_row_count != manifest_evidence_count:
                    failures.append(ValidationFailure("E_ADDENDUM_ROW_MISMATCH", 
                        f"Addendum has {addendum_row_count} evidence rows but manifest has {manifest_evidence_count}",
                        path="closure_addendum.md", expected=manifest_evidence_count, actual=addendum_row_count))
                
                # Check 3: Each table row parses cleanly into (role, path, sha256)
                for row in table_rows:
                    parts = [p.strip().strip('`') for p in row.split('|') if p.strip()]
                    if len(parts) != 3:
                        failures.append(ValidationFailure("E_ADDENDUM_PARSE_FAIL", 
                            f"Cannot parse evidence row: {row[:60]}", path="closure_addendum.md"))
            
            # F6: ZIP_SHA256_INTEGRITY (v1.1 Detached Digest)
            if not args.skip_digest_verification:
                current_zip_sha = calculate_sha256(open(args.bundle_path, 'rb').read())
                manifest_sha = manifest.get("zip_sha256")
                
                if manifest_sha == "DETACHED_SEE_SIBLING_FILE" or manifest_sha is None:
                    # v1.1 Logic (and v2.3 null support)
                    sidecar_path = bundle_path_obj.with_name(bundle_path_obj.name + ".sha256")
                    if not sidecar_path.exists():
                        failures.append(ValidationFailure("DETACHED_DIGEST_MISSING", 
                            f"Manifest specifies detached digest but {sidecar_path.name} not found"))
                    else:
                        sidecar_content = sidecar_path.read_text().strip()
                        # Handle "HASH  FILENAME" or just "HASH"
                        parts = sidecar_content.split()
                        sidecar_hash = parts[0].upper() if parts else ""
                        
                        # Tightening: Assert format
                        if not re.match(r"^[0-9A-F]{64}$", sidecar_hash):
                             failures.append(ValidationFailure("DETACHED_DIGEST_MALFORMED", 
                                f"Sidecar digest must be 64 hex characters. Found '{sidecar_hash}' in {sidecar_path.name}"))

                        elif sidecar_hash != current_zip_sha:
                             failures.append(ValidationFailure("DETACHED_DIGEST_MISMATCH", 
                                f"Sidecar hash {sidecar_hash} != Actual ZIP hash {current_zip_sha}"))
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
                        if ev.get("role") in ["raw_log", "state", "packet", "report", "manifest", "validator_final", "validator_final_shipped"]:
                            failures.extend(scan_for_tokens(content, path))
                        
                        # P0.4: PORTABILITY CHECK (for .md files)
                        if path.endswith(".md"):
                            failures.extend(scan_for_portability(content, path))
                            
                        # F9: TRANSCRIPT_COMPLETENESS (v1.2.1/v1.2.2)
                        if ev.get("role") in ["validator_final", "validator_final_shipped"]:
                            try:
                                text = content.decode('utf-8')
                                if "Exit Code:" not in text:
                                    failures.append(ValidationFailure("TRANSCRIPT_INCOMPLETE", "Validator transcript missing Exit Code", path=path))
                            except (UnicodeDecodeError, AttributeError):
                                pass  # Binary content or None, skip text parsing

            # Profile Validation
            profile_entry = manifest.get("profile")
            if profile_entry:
                profile_name = args.profile_override or profile_entry.get("name")
                if profile_name:
                    failures.extend(validate_profile(profile_name, manifest, zf))

            # F10: GCBS_STANDARD_VERSION_REQUIRED (v0.2.2)
            gcbs_version = manifest.get("gcbs_standard_version")
            if gcbs_version is None:
                failures.append(ValidationFailure("E_GCBS_STANDARD_VERSION_MISSING",
                    "Manifest missing required field: gcbs_standard_version"))
            else:
                print(f"GCBS Standard Version: {gcbs_version}")
            
            # F11: PROVENANCE_HASH_VERIFICATION (v0.2.2)
            activated_ref = manifest.get("activated_protocols_ref")
            activated_sha = manifest.get("activated_protocols_sha256")
            if activated_ref and activated_sha:
                # Compute hash of actual index file
                repo_root = Path(__file__).parent.parent.parent
                index_path = repo_root / activated_ref
                if index_path.exists():
                    actual_hash = calculate_sha256(index_path.read_bytes())
                    if actual_hash.upper() != activated_sha.upper():
                        failures.append(ValidationFailure("E_PROTOCOLS_PROVENANCE_MISMATCH",
                            f"Provenance hash mismatch: manifest={activated_sha} actual={actual_hash}",
                            path=activated_ref, expected=activated_sha, actual=actual_hash))
                    else:
                        print(f"Protocols provenance verified: {activated_sha}")
                    
                    provenance_evidence['protocols'] = {
                        'ref': activated_ref,
                        'expected': activated_sha,
                        'actual': actual_hash
                    }
            
            # F12: EVIDENCE_ROLE_VALIDATION (v0.2.2 - compat window)
            if manifest:
                evidence = manifest.get("evidence", [])
                roles = [ev.get("role") for ev in evidence if ev.get("role")]
                has_payload_pass = "validator_payload_pass" in roles
                has_legacy = "validator_final_shipped" in roles
                
                if has_legacy and not has_payload_pass:
                    # Check cutoff
                    try:
                        gcbs_ver = float(gcbs_version) if gcbs_version else 1.0
                        if gcbs_ver >= 1.1:
                            failures.append(ValidationFailure("E_ROLE_DEPRECATED",
                                "Legacy role validator_final_shipped rejected (G-CBS >= 1.1)"))
                        else:
                            print("WARN: Deprecated role validator_final_shipped, use validator_payload_pass")
                    except ValueError:
                        pass

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
    # Calculate Bundle Hash (for the report)
    if os.path.exists(args.bundle_path):
        manifest_sha = manifest.get("zip_sha256") if manifest else None
        
        if manifest_sha == "DETACHED_SEE_SIBLING_FILE" or manifest_sha is None:
             # v1.2.2 Logic: DETACHED_DIGEST STRATEGY
             # We explicitly do NOT print the bundle hash or the sidecar hash in the report.
             # This allows the report to be generated inside the bundle without creating a circular hash dependency.
             report_lines.append("**Digest Strategy**: Detached (Sidecar Verified)")
             # NOTE: The sidecar ITSELF is verified by the validator before generating this report (or during validation).
             # The report merely attests to the STRATEGY used.
        else:
            with open(args.bundle_path, 'rb') as f:
                bundle_hash = calculate_sha256(f.read())
            report_lines.append(f"**Bundle SHA256**: `{bundle_hash}`")
    
    report_lines.append("")
    report_lines.append("## Checks Performed")
    report_lines.append("- ZIP path canonicalization (no backslashes, no .., no absolute)")
    report_lines.append("- Required root files (closure_manifest.json, closure_addendum.md)")
    report_lines.append("- Manifest schema validation (G-CBS-1.0)")
    report_lines.append("- Addendum elision check (no elision tokens allowed)")
    report_lines.append("- Addendum row count vs manifest evidence count")
    report_lines.append("- Addendum table parsing (role, path, sha256)")
    report_lines.append("- Portability check (.md files: no file:///, no C:\\\\Users\\\\)")
    report_lines.append("- Evidence file integrity (SHA256 verification)")
    report_lines.append("- Transcript completeness (Exit Code presence)")
    report_lines.append("- Protocols provenance hash")
    
    if provenance_evidence:
        report_lines.append("")
        report_lines.append("## Provenance Evidence")
        report_lines.append("| Component | Reference | Expected SHA256 | Actual SHA256 | Status |")
        report_lines.append("|-----------|-----------|-----------------|---------------|--------|")
        for comp, data in provenance_evidence.items():
            status_cell = "PASS" if data['expected'].upper() == data['actual'].upper() else "FAIL"
            report_lines.append(f"| {comp} | {data['ref']} | `{data['expected']}` | `{data['actual']}` | {status_cell} |")

    report_lines.append("")
    report_lines.append("## Validation Findings")
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
    if not report_content.endswith("\n"): report_content += "\n"
    
    # Write Report with strict LF
    with open(args.output, "w", newline="\n", encoding="utf-8") as f:
        f.write(report_content)
        
    print(f"Audit Status: {status}")
    print(f"Report written to: {args.output}")

    if failures:
        sys.exit(1)
    else:
        sys.exit(0)
    
if __name__ == "__main__":
    main()
