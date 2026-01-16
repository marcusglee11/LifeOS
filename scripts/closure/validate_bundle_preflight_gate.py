#!/usr/bin/env python3
"""
validate_bundle_preflight_gate.py - G-CBS Bundle Preflight Gate (BPG) v1.0

Enforces Determinism Boundary Spec (DBS) and Closure-Grade Evidence requirements.
This gate MUST return PASS before a bundle is sealed/published.

Output Contract:
  PASS
  FAIL BPG###: <MESSAGE>
"""

import sys
import zipfile
import json
import re
import hashlib
from datetime import datetime

# --- Constants ---
REQUIRED_ROOT_FILES = ['closure_manifest.json', 'audit_report.md', 'closure_addendum.md']
PLACEHOLDERS = [
    "1980-01-01", "1970-01-01", "0001-01-01",
    "19800101", "19700101", "00010101"
]
MANIFEST_SCHEMA_VERSION = "G-CBS-1.0"

class BPGError(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message
        super().__init__(f"FAIL {code}: {message}")

def fail(code, message):
    print(f"FAIL {code}: {message}")
    sys.exit(1)

def validate_zip_integrity(zip_path):
    """BPG001: ZIP integrity/CRC failure"""
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            bad_file = zf.testzip()
            if bad_file:
                fail("BPG001", "ZIP integrity check failed (unreadable or CRC error).")
    except (zipfile.BadZipFile, Exception):
        # P1: Stabilize message (no exception text)
        fail("BPG001", "ZIP integrity check failed (unreadable or CRC error).")

def get_zip_content(zip_path, filename):
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            return zf.read(filename).decode('utf-8')
    except KeyError:
        return None
    except Exception as e:
        # File read error generic
        fail("BPG001", f"ZIP integrity check failed (read error on {filename}).")

def validate_root_files(zip_path):
    """BPG002: Missing required root file"""
    with zipfile.ZipFile(zip_path, 'r') as zf:
        namelist = zf.namelist()
        for f in REQUIRED_ROOT_FILES:
            if f not in namelist:
                fail("BPG002", f"Missing required root file: {f}.")

def validate_manifest(zip_path):
    """BPG003, BPG004, BPG006"""
    content = get_zip_content(zip_path, "closure_manifest.json")
    try:
        manifest = json.loads(content)
    except json.JSONDecodeError:
        fail("BPG003", "closure_manifest.json is not valid JSON.")

    # BPG003: Manifest missing required field
    required = ["schema_version", "run_timestamp", "closure_id", "bundle_name", "evidence", "provenance"]
    for field in required:
        if field not in manifest:
            fail("BPG003", f"closure_manifest missing required field: {field}.")
    
    provenance = manifest.get("provenance", {})
    prov_required = ["identity_source", "run_timestamp_source", "allow_placeholder_identity_date"]
    for field in prov_required:
        if field not in provenance:
            fail("BPG003", f"closure_manifest missing required field: provenance.{field}.")

    # BPG004: Placeholder run_timestamp
    run_ts = manifest.get("run_timestamp", "")
    for ph in PLACEHOLDERS:
        if ph in run_ts:
            fail("BPG004", f"run_timestamp is a known placeholder ({run_ts}); placeholders are forbidden.")

    # BPG006: Placeholder identity check
    identities = [manifest.get("closure_id", ""), manifest.get("bundle_name", "")]
    identity_source = provenance.get("identity_source")
    allow_placeholder = provenance.get("allow_placeholder_identity_date")
    
    # "Identity contains placeholder date ... without caller-provided override record."
    # Rule: IF (placeholder in identity) AND NOT (source=caller_provided AND allow=true) -> FAIL
    for val in identities:
        for ph in PLACEHOLDERS:
            if ph in val:
                # Placeholder detected
                if not (identity_source == "caller_provided" and allow_placeholder is True):
                    fail("BPG006", f"identity contains placeholder date ({val}) without caller-provided override record.")

    return manifest

def validate_audit_report(zip_path, manifest_ts):
    """BPG005: audit_report timestamp mismatch"""
    content = get_zip_content(zip_path, "audit_report.md")
    if not content:
        # Should be caught by BPG002, but safety net
        fail("BPG002", "Missing required root file: audit_report.md.")
    
    lines = content.splitlines()[:50]
    matches = []
    for line in lines:
        m = re.match(r"^\*\*Date\*\*:\s*(.+)$", line)
        if m:
            matches.append(m.group(1).strip())
            
    if len(matches) == 0:
        fail("BPG005", "audit_report Date not found in first 50 lines.")
    if len(matches) > 1:
        fail("BPG005", f"audit_report Date ambiguous (found {len(matches)} matches).")
        
    audit_date = matches[0]
    if audit_date != manifest_ts:
        fail("BPG005", f"audit_report Date does not match closure_manifest.run_timestamp (audit={audit_date}, manifest={manifest_ts}).")

def validate_fix_return(zip_path):
    """BPG007, BPG008, BPG009, BPG010"""
    content = get_zip_content(zip_path, "FIX_RETURN.md")
    if content is None:
        fail("BPG008", "FIX_RETURN.md is missing from bundle root.")

    validators = [
        "validate_review_packet.py",
        "validate_plan_packet.py"
    ]

    for val_name in validators:
        # BPG009 Check headings and fences
        header_pattern = re.escape(f"### {val_name} (1 PASS + 5 FAIL)")
        # We need to find the header, then look for the fenced block immediately following
        # Simplifying: regex search for Header + newline + fence
        
        # Regex to capture the transcript block content
        # Pattern: ### HEADER \n ```text \n (CONTENT) \n ```
        # Note: Depending on line endings, might need \r?\n
        pattern = fr"### {re.escape(val_name)} \(1 PASS \+ 5 FAIL\)\s+```text\s+(.*?)\s+```"
        match = re.search(pattern, content, re.DOTALL)
        
        if not match:
            fail("BPG009", f"FIX_RETURN missing required verbatim validator transcripts for {val_name}.")
            
        transcript = match.group(1)
        
        # Check for elisions (BPG009)
        if "..." in transcript or "…" in transcript:
            fail("BPG009", f"FIX_RETURN missing required verbatim validator transcripts for {val_name} (elision detected).")
            
        # Parse lines for BPG007 and BPG010
        lines = [l.strip() for l in transcript.splitlines() if l.strip()]
        pass_count = 0
        fail_codes = set()
        
        for line in lines:
            # P0: Strict BPG007 Enforcement
            is_pass = (line == "PASS")
            is_fail = bool(re.match(r"^FAIL [A-Z0-9_]+: .+$", line))
            
            if is_pass:
                pass_count += 1
            elif is_fail:
                fail_codes.add(line.split()[1].strip(":"))
            else:
                # Any other line is a DRIFT failure
                fail("BPG007", f"validator output contract drift detected (expected PASS or 'FAIL <CODE>: <MESSAGE>'). Found: '{line}'")

        # BPG010 counts
        if pass_count != 1:
            fail("BPG010", f"validator transcript counts invalid for {val_name} (need PASS=1 and FAIL_DISTINCT=5). Found PASS={pass_count}.")
        if len(fail_codes) != 5:
            fail("BPG010", f"validator transcript counts invalid for {val_name} (need PASS=1 and FAIL_DISTINCT=5). Found FAIL={len(fail_codes)} ({sorted(list(fail_codes))}).")

def validate_auditability(zip_path, manifest):
    """BPG011: Missing auditability artefact + Completeness"""
    # 1. Require evidence/bundle_file_list.txt in ZIP
    with zipfile.ZipFile(zip_path, 'r') as zf:
        zip_files = set(zf.namelist())
        if "evidence/bundle_file_list.txt" not in zip_files:
            fail("BPG011", "missing required auditability artefact (evidence/bundle_file_list.txt).")
            
        # 2. Manifest reference
        found_ref = False
        ref_sha = None
        for ev in manifest.get("evidence", []):
            if ev.get("path") == "evidence/bundle_file_list.txt":
                found_ref = True
                ref_sha = ev.get("sha256")
                break
        
        if not found_ref:
            fail("BPG011", "missing required auditability artefact (evidence/bundle_file_list.txt) in manifest evidence.")
            
        # 3. Hash verification
        content = zf.read("evidence/bundle_file_list.txt")
        computed_sha = hashlib.sha256(content).hexdigest().upper()
        if ref_sha and ref_sha.upper() != computed_sha:
             # This technically falls under BPG011 per spec "hashes verified against manifest"
             # Could also be a generic hash mismatch, but BPG011 specifically mentions it.
             fail("BPG011", f"missing required auditability artefact (evidence/bundle_file_list.txt) hash mismatch.")

        # 4. Completeness Check (P0)
        # Verify bundle_file_list.txt contains all ZIP entries (minus allowed exclusions)
        # Parse file_list
        listed_files = set()
        file_list_lines = content.decode('utf-8').splitlines()
        for ln in file_list_lines:
            if not ln.strip(): continue
            parts = ln.split('\t')
            if parts:
                listed_files.add(parts[0])
        
        # Allowed Exclusions (Metadata Cycle)
        # We allow manifest, addendum, and the file_list itself to be missing from the list.
        exclusions = {
            "closure_manifest.json",
            "closure_addendum.md",
            "evidence/bundle_file_list.txt",
            # Sidecars are usually detached, but if in zip? Usually not.
        }
        
        # Check for unlisted files
        unlisted = []
        for zf_name in zip_files:
            if zf_name not in listed_files and zf_name not in exclusions:
                unlisted.append(zf_name)
        
        if unlisted:
            fail("BPG011", f"bundle_file_list incomplete. Missing entrie(s): {', '.join(unlisted[:3])}...")

def main():
    if len(sys.argv) != 2:
        print("Usage: validate_bundle_preflight_gate.py <bundle.zip>")
        sys.exit(1)
        
    bundle_path = sys.argv[1]
    
    # 1. BPG001
    validate_zip_integrity(bundle_path)
    
    # 2. BPG002
    validate_root_files(bundle_path)
    
    # 3. BPG003, BPG004, BPG006
    manifest = validate_manifest(bundle_path)
    
    # 4. BPG005
    validate_audit_report(bundle_path, manifest['run_timestamp'])
    
    # 5. BPG007, BPG008, BPG009, BPG010
    validate_fix_return(bundle_path)
    
    # 6. BPG011
    validate_auditability(bundle_path, manifest)
    
    print("PASS")
    sys.exit(0)

if __name__ == "__main__":
    main()
