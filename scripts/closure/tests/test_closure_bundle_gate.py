
import pytest
import os
import sys
import zipfile
import json
import subprocess
import shutil
import hashlib
from pathlib import Path

# Locate scripts
SCRIPTS_DIR = Path(__file__).parent.parent
BPG_SCRIPT = SCRIPTS_DIR / "validate_bundle_preflight_gate.py"

@pytest.fixture
def run_bpg():
    def _run(zip_path):
        result = subprocess.run(
            [sys.executable, str(BPG_SCRIPT), str(zip_path)],
            capture_output=True,
            text=True
        )
        return result
    return _run

def calc_sha(content_str):
    return hashlib.sha256(content_str.encode('utf-8')).hexdigest().upper()

@pytest.fixture
def valid_bundle_components(tmp_path):
    # Fixed content for reproducibility
    ev_content = "dummy content"
    ev_sha = calc_sha(ev_content)
    
    audit_content = "# Audit Report\n**Date**: 2026-01-01T12:00:00\n"
    audit_sha = calc_sha(audit_content)
    
    fix_content = """
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
    fix_sha = calc_sha(fix_content)

    # Construct complete file list (sorted)
    # Entries: audit_report.md, evidence/test_ev.txt, FIX_RETURN.md
    files = [
        ("FIX_RETURN.md", fix_sha),
        ("audit_report.md", audit_sha),
        ("evidence/test_ev.txt", ev_sha)
    ]
    files.sort(key=lambda x: x[0])
    
    file_list_content = ""
    for name, sha in files:
        file_list_content += f"{name}\tsha256:{sha}\n"
    
    fl_sha = calc_sha(file_list_content)

    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "test_ev.txt").write_text(ev_content, encoding='utf-8')
    (evidence / "bundle_file_list.txt").write_text(file_list_content, encoding='utf-8')
    
    manifest = {
        "schema_version": "G-CBS-1.0",
        "run_timestamp": "2026-01-01T12:00:00",
        "closure_id": "TEST_ID_2026-01-01",
        "bundle_name": "TEST_BUNDLE",
        "evidence": [
            {"path": "evidence/test_ev.txt", "sha256": ev_sha, "role": "test"},
            {"path": "evidence/bundle_file_list.txt", "sha256": fl_sha, "role": "bundle_file_list"}
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
    
    closure_addendum = "# Addendum\n"
    
    return manifest, audit_content, closure_addendum, fix_content, evidence

def create_zip(path, manifest, audit, addendum, fix, evidence_dir=None):
    with zipfile.ZipFile(path, 'w') as zf:
        zf.writestr("closure_manifest.json", json.dumps(manifest))
        if audit is not None: zf.writestr("audit_report.md", audit)
        if addendum is not None: zf.writestr("closure_addendum.md", addendum)
        if fix is not None: zf.writestr("FIX_RETURN.md", fix)
             
        if evidence_dir:
            # Write evidence
            zf.writestr("evidence/test_ev.txt", "dummy content")
            # Write file list (content matters for hash check)
            # We read from evidence_dir
            fl_content = (evidence_dir / "bundle_file_list.txt").read_text(encoding='utf-8')
            zf.writestr("evidence/bundle_file_list.txt", fl_content)

    return path


def test_t1_pass_valid(tmp_path, run_bpg, valid_bundle_components):
    manifest, audit, addendum, fix, ev_dir = valid_bundle_components
    
    zip_path = tmp_path / "valid.zip"
    create_zip(zip_path, manifest, audit, addendum, fix, ev_dir)
    
    res = run_bpg(zip_path)
    assert res.returncode == 0
    assert "PASS" in res.stdout

def test_t3_bpg001_corrupt(tmp_path, run_bpg):
    zip_path = tmp_path / "corrupt.zip"
    zip_path.write_bytes(b"PK00000_GARBAGE")
    res = run_bpg(zip_path)
    assert res.returncode == 1
    assert "FAIL BPG001" in res.stdout

def test_t4_bpg002_missing_root(tmp_path, run_bpg, valid_bundle_components):
    # Missing audit_report
    manifest, _, addendum, fix, ev_dir = valid_bundle_components
    zip_path = tmp_path / "bpg002.zip"
    create_zip(zip_path, manifest, None, addendum, fix, ev_dir)
    res = run_bpg(zip_path)
    assert res.returncode == 1
    assert "FAIL BPG002" in res.stdout

def test_t5_bpg008_missing_fix(tmp_path, run_bpg, valid_bundle_components):
    manifest, audit, addendum, _, ev_dir = valid_bundle_components
    zip_path = tmp_path / "bpg008.zip"
    create_zip(zip_path, manifest, audit, addendum, None, ev_dir)
    res = run_bpg(zip_path)
    assert res.returncode == 1
    assert "FAIL BPG008" in res.stdout

def test_t6_bpg005_audit_mismatch(tmp_path, run_bpg, valid_bundle_components):
    manifest, audit, addendum, fix, ev_dir = valid_bundle_components
    manifest["run_timestamp"] = "2026-01-01T12:00:00"
    audit = "# Audit\n**Date**: 2026-01-02T12:00:00\n" # Mismatch
    
    zip_path = tmp_path / "bpg005.zip"
    create_zip(zip_path, manifest, audit, addendum, fix, ev_dir)
    res = run_bpg(zip_path)
    assert res.returncode == 1
    assert "FAIL BPG005" in res.stdout

def test_t7_bpg004_placeholder_ts(tmp_path, run_bpg, valid_bundle_components):
    manifest, audit, addendum, fix, ev_dir = valid_bundle_components
    manifest["run_timestamp"] = "1980-01-01T00:00:00"
    audit = "# Audit\n**Date**: 1980-01-01T00:00:00\n"
    
    zip_path = tmp_path / "bpg004.zip"
    create_zip(zip_path, manifest, audit, addendum, fix, ev_dir)
    res = run_bpg(zip_path)
    assert res.returncode == 1
    assert "FAIL BPG004" in res.stdout

def test_t8_bpg006_placeholder_identity(tmp_path, run_bpg, valid_bundle_components):
    manifest, audit, addendum, fix, ev_dir = valid_bundle_components
    manifest["closure_id"] = "ID_1980-01-01_COMMIT"
    
    zip_path = tmp_path / "bpg006.zip"
    create_zip(zip_path, manifest, audit, addendum, fix, ev_dir)
    res = run_bpg(zip_path)
    assert res.returncode == 1
    assert "FAIL BPG006" in res.stdout

def test_t9_bpg007_drift_brackets(tmp_path, run_bpg, valid_bundle_components):
    manifest, audit, addendum, fix, ev_dir = valid_bundle_components
    # Targeted replace to avoid breaking header "(1 PASS + 5 FAIL)"
    fix_bad = fix.replace("\nPASS\n", "\n[PASS]\n")
    
    zip_path = tmp_path / "bpg007.zip"
    create_zip(zip_path, manifest, audit, addendum, fix_bad, ev_dir)
    res = run_bpg(zip_path)
    assert res.returncode == 1
    assert "FAIL BPG007" in res.stdout

def test_t13_bpg007_dirty_transcript(tmp_path, run_bpg, valid_bundle_components):
    manifest, audit, addendum, fix, ev_dir = valid_bundle_components
    # Insert NON-CONTRACT line, preserving header
    fix_dirty = fix.replace("\nPASS\n", "\nPASS\nNOTE: Some info\n")
    
    zip_path = tmp_path / "bpg007_dirty.zip"
    create_zip(zip_path, manifest, audit, addendum, fix_dirty, ev_dir)
    res = run_bpg(zip_path)
    assert res.returncode == 1
    assert "FAIL BPG007" in res.stdout

def test_t10_bpg010_bad_counts(tmp_path, run_bpg, valid_bundle_components):
    manifest, audit, addendum, fix, ev_dir = valid_bundle_components
    # Only 4 failures
    fix_bad = """
### validate_review_packet.py (1 PASS + 5 FAIL)
```text
PASS
FAIL C1: Msg
FAIL C2: Msg
FAIL C3: Msg
FAIL C4: Msg
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
    zip_path = tmp_path / "bpg010.zip"
    create_zip(zip_path, manifest, audit, addendum, fix_bad, ev_dir)
    res = run_bpg(zip_path)
    assert res.returncode == 1
    assert "FAIL BPG010" in res.stdout

def test_t11_bpg011_missing_file_list(tmp_path, run_bpg, valid_bundle_components):
    manifest, audit, addendum, fix, ev_dir = valid_bundle_components
    # Make manifest not have the entry
    manifest["evidence"] = [e for e in manifest["evidence"] if e["role"] != "bundle_file_list"]
    
    zip_path = tmp_path / "bpg011.zip"
    create_zip(zip_path, manifest, audit, addendum, fix, ev_dir)
    res = run_bpg(zip_path)
    assert res.returncode == 1
    assert "FAIL BPG011" in res.stdout

def test_t14_bpg011_incomplete_list(tmp_path, run_bpg, valid_bundle_components):
    manifest, audit, addendum, fix, ev_dir = valid_bundle_components
    
    zip_path = tmp_path / "bpg011_inc.zip"
    # Create valid zip first
    create_zip(zip_path, manifest, audit, addendum, fix, ev_dir)
    
    # Append a file to zip that is NOT in the list
    with zipfile.ZipFile(zip_path, 'a') as zf:
        zf.writestr("evidence/rogue.txt", "surprise")
        
    res = run_bpg(zip_path)
    assert res.returncode == 1
    assert "FAIL BPG011" in res.stdout
    assert "incomplete" in res.stdout
