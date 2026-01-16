
import sys
import os
import zipfile
import json
import subprocess
import hashlib
from pathlib import Path

# Setup
SCRIPTS_DIR = Path(__file__).parent.parent
BPG_SCRIPT = SCRIPTS_DIR / "validate_bundle_preflight_gate.py"

def calculate_sha256(data):
    if isinstance(data, str): data = data.encode('utf-8')
    return hashlib.sha256(data).hexdigest().upper()

def run_bpg(name, zip_path):
    print(f"--- CMD: python {BPG_SCRIPT.name} {zip_path} ---")
    print(f"--- CWD: {os.getcwd()} ---")
    res = subprocess.run([sys.executable, str(BPG_SCRIPT), str(zip_path)], capture_output=True, text=True)
    print(res.stdout, end='')
    if res.stderr:
        print("STDERR:", res.stderr)
    # print(f"EXIT CODE: {res.returncode}") # User requested clean transcripts in packet?
    # Actually user requested "Verbatim transcripts including command lines".
    # Usually "EXIT CODE" is helpful context. I'll keep it.
    # Wait, previous packet had exit code.
    print("--------------------------------\n")

def make_zip(path, manifest, audit, addendum, fix, evidence_files):
    # evidence_files: list of (arcname, content_str)
    
    # BPG011 requires bundle_file_list.txt in ZIP, containing hashes of:
    # 1. evidence/* (except itself)
    # 2. audit_report.md
    # 3. FIX_RETURN.md
    
    # Calculate hashes for file list
    fl_entries = []
    
    if audit:
        fl_entries.append(("audit_report.md", calculate_sha256(audit)))
    if fix:
        fl_entries.append(("FIX_RETURN.md", calculate_sha256(fix)))
        
    for name, content in evidence_files:
        fl_entries.append((name, calculate_sha256(content)))
        
    fl_entries.sort(key=lambda x: x[0])
    
    fl_content = ""
    for name, sha in fl_entries:
        fl_content += f"{name}\tsha256:{sha}\n"
        
    fl_sha = calculate_sha256(fl_content)
    
    # Update Manifest to match correct hash of file list
    # Find the file list entry and update sha
    found = False
    for ev in manifest['evidence']:
        if ev['path'] == "evidence/bundle_file_list.txt":
            ev['sha256'] = fl_sha
            found = True
            break
            
    with zipfile.ZipFile(path, 'w') as zf:
        zf.writestr("closure_manifest.json", json.dumps(manifest))
        if audit: zf.writestr("audit_report.md", audit)
        if addendum: zf.writestr("closure_addendum.md", addendum)
        if fix: zf.writestr("FIX_RETURN.md", fix)
        
        for name, content in evidence_files:
            zf.writestr(name, content)
            
        zf.writestr("evidence/bundle_file_list.txt", fl_content)

ev_content = "dummy content"
ev_sha = calculate_sha256(ev_content)
# Placeholder for file list hash, will be updated by make_zip
manifest_base = {
    "schema_version": "G-CBS-1.0",
    "run_timestamp": "2026-01-01T12:00:00",
    "closure_id": "TEST_ID_2026-01-01",
    "bundle_name": "TEST_BUNDLE",
    "evidence": [
        {"path": "evidence/test_ev.txt", "sha256": ev_sha, "role": "test"},
        {"path": "evidence/bundle_file_list.txt", "sha256": "UPDATE_ME", "role": "bundle_file_list"}
    ],
    "provenance": {
        "identity_source": "derived",
        "run_timestamp_source": "captured",
        "allow_placeholder_identity_date": False
    },
    "closure_type": "TEST",
    "run_commit": "HEAD",
    "invariants_asserted": [],
    "profile": {"name": "TEST", "version": "1.0"}
}
audit_base = "# Audit Report\n**Date**: 2026-01-01T12:00:00\n"
addendum_base = "# Addendum\n"
fix_base = """
### validate_review_packet.py (1 PASS + 5 FAIL)
```text
PASS
FAIL C1: Msg
FAIL C2: Msg
FAIL C3: Msg
FAIL C4: Msg
FAIL C5: Msg
```

### validate_plan_packet.py (1 PASS + 5 FAIL)
```text
PASS
FAIL P1: Msg
FAIL P2: Msg
FAIL P3: Msg
FAIL P4: Msg
FAIL P5: Msg
```
"""

print("=== EVIDENCE GENERATION START ===\n")

def get_file_sha(fp):
    if not os.path.exists(fp): return "MISSING"
    with open(fp, 'rb') as f: return hashlib.sha256(f.read()).hexdigest().lower()

# Files to Hash
chk_files = [
    "scripts/closure/validate_bundle_preflight_gate.py",
    "scripts/closure/build_closure_bundle.py",
    "scripts/closure/tests/test_closure_bundle_gate.py",
    "docs/11_admin/LIFEOS_STATE.md",
    "docs/INDEX.md",
    "docs/LifeOS_Strategic_Corpus.md"
]
print("### FILE HASHES")
for f in chk_files:
    print(f"{f}: {get_file_sha(f)}")
print("\n")

# 1. PASS
evidence = [("evidence/test_ev.txt", ev_content)]
make_zip("pass.zip", manifest_base, audit_base, addendum_base, fix_base, evidence)
run_bpg("PASS CASE", "pass.zip")

# 2. FAIL BPG007 (Dirty Transcript)
# Ensure we don't break the header "1 PASS + 5 FAIL"
f_fail = fix_base.replace("\nPASS\n", "\nPASS\nNOTE: Extra Info\n")
make_zip("fail_bpg007.zip", manifest_base, audit_base, addendum_base, f_fail, evidence)
run_bpg("FAIL BPG007", "fail_bpg007.zip")

# 3. FAIL BPG011 (Incomplete List)
# Add extra evidence but don't handle it in make_zip (requires hack)
# We make specific zip for this
zp = "fail_bpg011.zip"
make_zip(zp, manifest_base, audit_base, addendum_base, fix_base, evidence)
with zipfile.ZipFile(zp, 'a') as zf:
    zf.writestr("evidence/rogue.txt", "rogue")
run_bpg("FAIL BPG011", zp)

# Cleanup
for f in ["pass.zip", "fail_bpg007.zip", "fail_bpg011.zip"]:
    if os.path.exists(f): os.remove(f)

print("=== EVIDENCE GENERATION END ===")
