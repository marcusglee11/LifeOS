
import sys
import os
import zipfile
import json
import subprocess
import shutil
import hashlib
from pathlib import Path

SCRIPTS_DIR = Path("scripts/closure")
TESTS_DIR = SCRIPTS_DIR / "tests"
BPG_SCRIPT = SCRIPTS_DIR / "validate_bundle_preflight_gate.py"

EVIDENCE_DIR = Path("closure_evidence_temp")
if EVIDENCE_DIR.exists(): shutil.rmtree(EVIDENCE_DIR)
EVIDENCE_DIR.mkdir()

def run_cmd(cmd, outfile):
    print(f"Running: {cmd} -> {outfile}")
    with open(outfile, "w", encoding="utf-8") as f:
        # Capture stdout only for strict transcripts? Packet says "Verbatim transcripts including command lines"
        # The previous packet included command lines. BPG script doesn't print command lines.
        # I'll simulate the "transcripts" format used in packet.
        f.write(f"Command: {cmd}\n")
        f.write(f"CWD: {os.getcwd()}\n\n")
        
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        f.write(res.stdout)
        if res.stderr:
            f.write("\nSTDERR:\n")
            f.write(res.stderr)
        # f.write(f"\nExit Code: {res.returncode}\n")

# Use generate_evidence_logs_v3.py logic but direct to files.
# Actually, I can just reuse v3 script to MAKE the zips, then run BPG on them and capture output.
# v3 script creates: pass.zip, fail_bpg007.zip, fail_bpg011.zip locally.

# 1. Run v3 log gen script to create the ZIPs (it cleans them up at end, so I should modify it or just copy code)
# Easier to just use the v3 script but comment out cleanup or interrupt it?
# Or just copy the make_zip logic here.

def calculate_sha256(data):
    if isinstance(data, str): data = data.encode('utf-8')
    return hashlib.sha256(data).hexdigest().upper()

def make_zip(path, manifest, audit, addendum, fix, evidence_files):
    fl_entries = []
    if audit: fl_entries.append(("audit_report.md", calculate_sha256(audit)))
    if fix: fl_entries.append(("FIX_RETURN.md", calculate_sha256(fix)))
    for name, content in evidence_files: fl_entries.append((name, calculate_sha256(content)))
    fl_entries.sort(key=lambda x: x[0])
    
    fl_content = ""
    for name, sha in fl_entries: fl_content += f"{name}\tsha256:{sha}\n"
    fl_sha = calculate_sha256(fl_content)
    
    # Update Manifest
    for ev in manifest['evidence']:
        if ev['path'] == "evidence/bundle_file_list.txt":
            ev['sha256'] = fl_sha
            break
            
    with zipfile.ZipFile(path, 'w') as zf:
        zf.writestr("closure_manifest.json", json.dumps(manifest))
        if audit: zf.writestr("audit_report.md", audit)
        if addendum: zf.writestr("closure_addendum.md", addendum)
        if fix: zf.writestr("FIX_RETURN.md", fix)
        for name, content in evidence_files: zf.writestr(name, content)
        zf.writestr("evidence/bundle_file_list.txt", fl_content)

ev_content = "dummy content"
ev_sha = calculate_sha256(ev_content)
manifest_base = {
    "schema_version": "G-CBS-1.0",
    "run_timestamp": "2026-01-01T12:00:00",
    "closure_id": "TEST_ID_2026-01-01",
    "bundle_name": "TEST_BUNDLE",
    "evidence": [{"path": "evidence/test_ev.txt", "sha256": ev_sha, "role": "test"}, {"path": "evidence/bundle_file_list.txt", "sha256": "UPDATE_ME", "role": "bundle_file_list"}],
    "provenance": {"identity_source": "derived", "run_timestamp_source": "captured", "allow_placeholder_identity_date": False},
    "closure_type": "TEST", "run_commit": "HEAD", "invariants_asserted": [], "profile": {"name": "TEST", "version": "1.0"}
}
audit_base = "# Audit Report\n**Date**: 2026-01-01T12:00:00\n"
addendum_base = "# Addendum\n"
fix_base = "### validate_review_packet.py (1 PASS + 5 FAIL)\n```text\nPASS\nFAIL C1: Msg\nFAIL C2: Msg\nFAIL C3: Msg\nFAIL C4: Msg\nFAIL C5: Msg\n```\n\n### validate_plan_packet.py (1 PASS + 5 FAIL)\n```text\nPASS\nFAIL P1: Msg\nFAIL P2: Msg\nFAIL P3: Msg\nFAIL P4: Msg\nFAIL P5: Msg\n```\n"
evidence = [("evidence/test_ev.txt", ev_content)]

# 1. PASS
make_zip("pass.zip", manifest_base, audit_base, addendum_base, fix_base, evidence)
run_cmd(f"python {BPG_SCRIPT} pass.zip", EVIDENCE_DIR / "transcript_pass_run.txt")

# 2. FAIL BPG007 (Dirty Transcript)
f_fail = fix_base.replace("\nPASS\n", "\nPASS\nNOTE: Extra Info\n")
make_zip("fail_bpg007.zip", manifest_base, audit_base, addendum_base, f_fail, evidence)
run_cmd(f"python {BPG_SCRIPT} fail_bpg007.zip", EVIDENCE_DIR / "transcript_fail_bpg007.txt")

# 3. FAIL BPG011 (Incomplete List)
zp = "fail_bpg011.zip"
make_zip(zp, manifest_base, audit_base, addendum_base, fix_base, evidence)
with zipfile.ZipFile(zp, 'a') as zf: zf.writestr("evidence/rogue.txt", "rogue")
run_cmd(f"python {BPG_SCRIPT} fail_bpg011.zip", EVIDENCE_DIR / "transcript_fail_bpg011.txt")

# 4. Pytest
run_cmd(f"python -m pytest {TESTS_DIR / 'test_closure_bundle_gate.py'} -vv", EVIDENCE_DIR / "transcript_pytest.txt")

# Cleanup Zips
for f in ["pass.zip", "fail_bpg007.zip", "fail_bpg011.zip"]:
    if os.path.exists(f): os.remove(f)

print("Evidence files generated in closure_evidence_temp/")
