import pytest
import subprocess
import os
import sys
import uuid
import yaml
import hashlib
from datetime import datetime, timezone, timedelta

VALIDATOR_SCRIPT = "scripts/validate_packet.py"
CURRENT_SCHEMA = "docs/02_protocols/lifeos_packet_schemas_CURRENT.yaml"

def run_validator(path, args=None):
    if args is None:
        args = ["--schema", CURRENT_SCHEMA]
    cmd = [sys.executable, VALIDATOR_SCRIPT, path] + args
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr

def run_bundle_validator(dir_path):
    cmd = [sys.executable, VALIDATOR_SCRIPT, "--bundle", dir_path, "--schema", CURRENT_SCHEMA]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr

@pytest.fixture
def base_envelope():
    return {
        "packet_id": str(uuid.uuid4()),
        "packet_type": "HANDOFF_PACKET",
        "schema_version": "1.2",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_agent": "TestSrc",
        "target_agent": "TestDst",
        "chain_id": str(uuid.uuid4()),
        "priority": "P2_NORMAL",
        "nonce": str(uuid.uuid4()),
        "ttl_hours": 72,
        "is_draft": False,
        "signature_stub": { "signer": "Me", "method": "STUB", "attestation": "ok" }
    }

# --- P0.1 Required Fields ---
def test_missing_required_field(tmp_path, base_envelope):
    data = base_envelope.copy()
    data['packet_type'] = "CONTEXT_REQUEST_PACKET"
    # missing 'query', 'topic', 'requester_role'
    data['requester_role'] = "Builder" 
    data['topic'] = "Test"
    # Query missing
    
    p = tmp_path / "req_fail.yaml"
    p.write_text(yaml.dump(data), encoding='utf-8')
    
    code, out, err = run_validator(str(p))
    assert code == 2 # SCHEMA
    assert "Missing required payload fields" in err
    assert "query" in err

def test_council_review_missing_objective(tmp_path, base_envelope):
    data = base_envelope.copy()
    data['packet_type'] = "COUNCIL_REVIEW_PACKET"
    data['review_type'] = "CODE"
    data['subject_ref'] = "foo.py"
    data['subject_summary'] = "summ"
    # objective missing
    
    p = tmp_path / "cr_req_fail.yaml"
    p.write_text(yaml.dump(data), encoding='utf-8')
    
    code, out, err = run_validator(str(p))
    assert code == 2
    assert "objective" in err

# --- P0.2 Bundle Full Validation ---
def test_bundle_full_validate_fails_schema(tmp_path, base_envelope):
    # p1 valid
    p1 = base_envelope.copy()
    p1['packet_id'] = str(uuid.uuid4())
    p1['packet_type'] = "HANDOFF_PACKET"
    p1['nonce'] = str(uuid.uuid4())
    p1['reason'] = "ok"
    p1['current_state_summary'] = "ok"
    p1['next_step_goal'] = "ok"
    
    # p2 invalid schema (missing required)
    p2 = base_envelope.copy()
    p2['packet_id'] = str(uuid.uuid4())
    p2['packet_type'] = "HANDOFF_PACKET"
    p2['nonce'] = str(uuid.uuid4())
    p2['reason'] = "ok"
    # Missing current_state_summary
    
    (tmp_path / "p1.yaml").write_text(yaml.dump(p1), encoding='utf-8')
    (tmp_path / "p2.yaml").write_text(yaml.dump(p2), encoding='utf-8')
    
    code, out, err = run_bundle_validator(str(tmp_path))
    assert code == 2 or code == 1 # Bundle fail propagates from file fail
    assert "Missing required payload fields" in err

# --- P0.3 Lineage Verification ---
def test_lineage_verification_pass(tmp_path, base_envelope):
    # Review Packet
    rev_id = str(uuid.uuid4())
    rev = base_envelope.copy()
    rev['packet_id'] = rev_id
    rev['packet_type'] = "COUNCIL_REVIEW_PACKET"
    rev['nonce'] = str(uuid.uuid4())
    rev['review_type'] = "CODE"
    rev['subject_ref'] = "x"
    rev['subject_summary'] = "x"
    rev['objective'] = "x"
    
    # Calculate Hash (simulate validator logic)
    import hashlib
    canonical = yaml.dump(rev, sort_keys=True, allow_unicode=True, width=float("inf"))
    h = hashlib.sha256(canonical.encode('utf-8')).hexdigest()
    
    # Approval Packet
    app = base_envelope.copy()
    app['packet_id'] = str(uuid.uuid4())
    app['packet_type'] = "COUNCIL_APPROVAL_PACKET"
    app['nonce'] = str(uuid.uuid4())
    app['verdict'] = "APPROVED"
    app['review_packet_id'] = rev_id
    app['subject_hash'] = h # MATCH
    app['rationale'] = "ok"
    
    (tmp_path / "rev.yaml").write_text(yaml.dump(rev), encoding='utf-8')
    (tmp_path / "app.yaml").write_text(yaml.dump(app), encoding='utf-8')
    
    code, out, err = run_bundle_validator(str(tmp_path))
    assert code == 0

def test_lineage_verification_mismatch(tmp_path, base_envelope):
    rev_id = str(uuid.uuid4())
    rev = base_envelope.copy()
    rev['packet_id'] = rev_id
    rev['packet_type'] = "COUNCIL_REVIEW_PACKET"
    rev['nonce'] = str(uuid.uuid4())
    rev['review_type'] = "CODE"
    rev['subject_ref'] = "x"
    rev['subject_summary'] = "x"
    rev['objective'] = "x"
    
    app = base_envelope.copy()
    app['packet_id'] = str(uuid.uuid4())
    app['packet_type'] = "COUNCIL_APPROVAL_PACKET"
    app['nonce'] = str(uuid.uuid4())
    app['verdict'] = "APPROVED"
    app['review_packet_id'] = rev_id
    app['subject_hash'] = "badhash" # MISMATCH
    app['rationale'] = "ok"
    
    (tmp_path / "rev.yaml").write_text(yaml.dump(rev), encoding='utf-8')
    (tmp_path / "app.yaml").write_text(yaml.dump(app), encoding='utf-8')
    
    code, out, err = run_bundle_validator(str(tmp_path))
    assert code == 4 # EXIT_LINEAGE_VIOLATION
    assert "subject_hash mismatch" in err

def test_lineage_verification_missing_packet(tmp_path, base_envelope):
    app = base_envelope.copy()
    app['packet_id'] = str(uuid.uuid4())
    app['packet_type'] = "COUNCIL_APPROVAL_PACKET"
    app['nonce'] = str(uuid.uuid4())
    app['verdict'] = "APPROVED"
    app['review_packet_id'] = str(uuid.uuid4()) # Missing
    app['subject_hash'] = "somehash"
    app['rationale'] = "ok"
    
    (tmp_path / "app.yaml").write_text(yaml.dump(app), encoding='utf-8')
    
    code, out, err = run_bundle_validator(str(tmp_path))
    assert code == 4 # EXIT_LINEAGE_VIOLATION
    assert "references missing Review Packet" in err

# --- P1.1 Compression ---
def test_compression_fail(tmp_path, base_envelope):
    data = base_envelope.copy()
    data['packet_type'] = "HANDOFF_PACKET"
    data['reason'] = "ok"
    data['current_state_summary'] = "ok"
    data['next_step_goal'] = "ok"
    data['compression'] = "GZIP" # Should fail
    
    p = tmp_path / "comp_fail.yaml"
    p.write_text(yaml.dump(data), encoding='utf-8')
    
    code, out, err = run_validator(str(p))
    assert code == 2 # SCHEMA
    assert "Compression not supported" in err

# --- P0.3 Schema Driven Tests ---

def test_schema_validity():
    # Verify the actual schema file on disk parses correctly
    with open("docs/02_protocols/lifeos_packet_schemas_CURRENT.yaml", 'r') as f:
        schema = yaml.safe_load(f)
    assert schema['schema_version'] == "1.2"
    assert "max_clock_skew_seconds" in schema['limits']
    assert "COUNCIL_REVIEW_PACKET" in schema['taxonomy']['core_packet_types']

def test_validator_uses_schema_override(tmp_path, base_envelope):
    # 1. Create a schema with tiny skew limit
    with open("docs/02_protocols/lifeos_packet_schemas_CURRENT.yaml", 'r') as f:
        custom_schema = yaml.safe_load(f)
    
    custom_schema['limits']['max_clock_skew_seconds'] = 1 # 1 second tolerance
    
    schema_path = tmp_path / "strict_skew_schema.yaml"
    schema_path.write_text(yaml.dump(custom_schema), encoding='utf-8')
    
    # 2. Create packet with 10s skew (valid in default schema, invalid here)
    data = base_envelope.copy()
    old_time = datetime.now(timezone.utc) - timedelta(seconds=10)
    data['created_at'] = old_time.isoformat()
    # Add valid payload
    data['reason'] = "ok"
    data['current_state_summary'] = "ok"
    data['next_step_goal'] = "ok"
    
    p = tmp_path / "skew_10s.yaml"
    p.write_text(yaml.dump(data), encoding='utf-8')
    
    # 3. Run with default schema (Expect Pass, default is 300s)
    code, out, err = run_validator(str(p))
    assert code == 0 

    # 4. Run with custom schema (Expect Fail, limit is 1s)
    code, out, err = run_validator(str(p), args=["--schema", str(schema_path)])
    assert code == 3, f"Expected 3, got {code}. Err: {err}"
    assert "Clock skew" in err
    assert "exceeds max 1s" in err

def test_no_hardcoded_taxonomy(tmp_path, base_envelope):
    # 1. Create schema that removes HANDOFF_PACKET from core types
    with open("docs/02_protocols/lifeos_packet_schemas_CURRENT.yaml", 'r') as f:
        custom_schema = yaml.safe_load(f)
        
    if "HANDOFF_PACKET" in custom_schema['taxonomy']['core_packet_types']:
        custom_schema['taxonomy']['core_packet_types'].remove("HANDOFF_PACKET")
    
    schema_path = tmp_path / "no_handoff_schema.yaml"
    schema_path.write_text(yaml.dump(custom_schema), encoding='utf-8')
    
    # 2. Create HANDOFF packet
    data = base_envelope.copy()
    data['reason'] = "ok"
    data['current_state_summary'] = "ok"
    data['next_step_goal'] = "ok"
    
    p = tmp_path / "handoff.yaml"
    p.write_text(yaml.dump(data), encoding='utf-8')
    
    # 3. Run with custom schema (Expect Fail, HANDOFF is now unknown)
    code, out, err = run_validator(str(p), args=["--schema", str(schema_path)])
    assert code == 2 # SCHEMA
    assert "Unknown packet type: HANDOFF_PACKET" in err

# --- Final Close-Out Delta Tests ---

def test_ttl_expiry(tmp_path, base_envelope):
    data = base_envelope.copy()
    # Expired 1 hour ago
    created = datetime.now(timezone.utc) - timedelta(hours=73)
    data['created_at'] = created.isoformat()
    data['ttl_hours'] = 72
    # Add payload
    data['reason'] = "ok"
    data['current_state_summary'] = "ok"
    data['next_step_goal'] = "ok"
    
    p = tmp_path / "expired.yaml"
    p.write_text(yaml.dump(data), encoding='utf-8')
    
    # Skew check fires before TTL, so we must ignore skew to test TTL specifically
    code, out, err = run_validator(str(p), args=["--ignore-skew"])
    assert code == 3 # SECURITY
    assert "Packet TTL expired" in err

def test_replay_collision(tmp_path, base_envelope):
    # Two valid packets, same nonce
    nonce = str(uuid.uuid4())
    
    p1 = base_envelope.copy()
    p1['packet_id'] = str(uuid.uuid4())
    p1['nonce'] = nonce
    p1['reason'] = "ok"
    p1['current_state_summary'] = "ok"
    p1['next_step_goal'] = "ok"
    
    p2 = base_envelope.copy()
    p2['packet_id'] = str(uuid.uuid4())
    p2['nonce'] = nonce
    p2['reason'] = "ok"
    p2['current_state_summary'] = "ok"
    p2['next_step_goal'] = "ok"
    
    (tmp_path / "p1.yaml").write_text(yaml.dump(p1), encoding='utf-8')
    (tmp_path / "p2.yaml").write_text(yaml.dump(p2), encoding='utf-8')
    
    code, out, err = run_bundle_validator(str(tmp_path))
    assert code == 5 # REPLAY
    assert "Duplicate nonce" in err

def test_signature_enforcement(tmp_path, base_envelope):
    # Case A: Non-draft missing signature
    data = base_envelope.copy()
    data['is_draft'] = False
    if 'signature_stub' in data:
        del data['signature_stub']
    data['reason'] = "ok"
    data['current_state_summary'] = "ok"
    data['next_step_goal'] = "ok"
    
    p = tmp_path / "unsig_handoff.yaml"
    p.write_text(yaml.dump(data), encoding='utf-8')
    
    code, out, err = run_validator(str(p))
    assert code == 3 # SECURITY
    assert "Signature stub required" in err

    # Case B: Council Approval missing signature (even if draft)
    app = base_envelope.copy()
    app['packet_type'] = "COUNCIL_APPROVAL_PACKET"
    app['is_draft'] = True # Draft, but still needs sig
    if 'signature_stub' in app:
        del app['signature_stub']
    # Payload
    app['verdict'] = "APPROVED"
    app['review_packet_id'] = str(uuid.uuid4())
    app['subject_hash'] = "hash"
    
    p2 = tmp_path / "unsig_council.yaml"
    p2.write_text(yaml.dump(app), encoding='utf-8')
    
    code, out, err = run_validator(str(p2))
    assert code == 3 # SECURITY
    assert "Signature stub required" in err

def test_deprecated_gating(tmp_path, base_envelope):
    data = base_envelope.copy()
    data['packet_type'] = "GATE_APPROVAL_PACKET"
    # payload for gate approval
    data['gate_id'] = "G1"
    data['status'] = "OPEN"
    data['approver'] = "Me"
    
    p = tmp_path / "deprecated.yaml"
    p.write_text(yaml.dump(data), encoding='utf-8')
    
    # 1. Default: Fail
    code, out, err = run_validator(str(p))
    assert code == 2 # SCHEMA
    assert "Deprecated packet type" in err
    
    # 2. Allow Flag: Pass
    code, out, err = run_validator(str(p), args=["--allow-deprecated"])
    assert code == 0

def test_ignore_skew_override(tmp_path, base_envelope):
    data = base_envelope.copy()
    # Skewed 10 mins (600s) > 300s default
    old = datetime.now(timezone.utc) - timedelta(seconds=600)
    data['created_at'] = old.isoformat()
    data['reason'] = "ok"
    data['current_state_summary'] = "ok"
    data['next_step_goal'] = "ok"
    
    p = tmp_path / "skewed.yaml"
    p.write_text(yaml.dump(data), encoding='utf-8')
    
    # 1. Default: Fail
    code, out, err = run_validator(str(p))
    assert code == 3 # SECURITY
    assert "Clock skew" in err
    
    # 2. Ignore Flag: Pass
    code, out, err = run_validator(str(p), args=["--ignore-skew"])
    assert code == 0

# --- v1.2 Plan Cycle Tests (Subtypes) ---

def test_plan_build_packet_valid(tmp_path, base_envelope):
    data = base_envelope.copy()
    data['packet_type'] = "BUILD_PACKET"
    # Testing SemVer: 1.1 packet under 1.2 Schema should PASS
    data['schema_version'] = "1.1" 
    
    # Payload
    data['goal'] = "Plan Feature X"
    data['build_type'] = "PLAN"
    data['proposed_changes'] = "Files A, B"
    data['verification_plan'] = "Tests C"
    
    p = tmp_path / "build_plan.yaml"
    p.write_text(yaml.dump(data), encoding='utf-8')
    
    # Use CURRENT schema (v1.2)
    code, out, err = run_validator(str(p), args=["--schema", "docs/02_protocols/lifeos_packet_schemas_CURRENT.yaml"])
    assert code == 0

def test_plan_review_packet_valid(tmp_path, base_envelope):
    data = base_envelope.copy()
    data['packet_type'] = "REVIEW_PACKET"
    data['schema_version'] = "1.2"
    
    # Payload
    data['outcome'] = "GO"
    data['review_type'] = "PLAN_REVIEW"
    data['plan_hash'] = "sha256-hash-of-plan"
    data['verdict'] = "GO"
    data['terminal_outcome'] = "PASS"
    data['scope_envelope'] = "scope"
    data['repro'] = "cmd"
    data['closure_evidence'] = {}
    
    p = tmp_path / "review_plan.yaml"
    p.write_text(yaml.dump(data), encoding='utf-8')
    
    code, out, err = run_validator(str(p), args=["--schema", "docs/02_protocols/lifeos_packet_schemas_CURRENT.yaml"])
    assert code == 0

def test_semver_incompatible(tmp_path, base_envelope):
    data = base_envelope.copy()
    data['packet_type'] = "BUILD_PACKET"
    data['schema_version'] = "1.3" # Minor > 1.2
    data['goal'] = "Future stuff"
    
    p = tmp_path / "future_packet.yaml"
    p.write_text(yaml.dump(data), encoding='utf-8')
    
    code, out, err = run_validator(str(p), args=["--schema", "docs/02_protocols/lifeos_packet_schemas_CURRENT.yaml"])
    assert code == 6 # VERSION_INCOMPATIBLE

# --- P0.3 Regression Tests ---

def test_schema_taxonomy_no_overlap():
    with open(CURRENT_SCHEMA, 'r') as f:
        schema = yaml.safe_load(f)
    
    core = set(schema['taxonomy']['core_packet_types'])
    deprecated = set(schema['taxonomy']['deprecated_packet_types'])
    overlap = core.intersection(deprecated)
    assert not overlap, f"Schema has overlapping types: {overlap}"

def test_deprecated_gate_enforced_even_if_core_overlap(tmp_path, base_envelope):
    # 1. Create a broken schema with overlap
    with open(CURRENT_SCHEMA, 'r') as f:
        bad_schema = yaml.safe_load(f)
    
    # Introduce overlap
    ptype = "BAD_PACKET"
    bad_schema['taxonomy']['core_packet_types'].append(ptype)
    
    # Ensure 'deprecated_packet_types' key exists and is a list
    if 'deprecated_packet_types' not in bad_schema['taxonomy']:
         bad_schema['taxonomy']['deprecated_packet_types'] = []
    bad_schema['taxonomy']['deprecated_packet_types'].append(ptype)
    
    schema_path = tmp_path / "broken_schema.yaml"
    schema_path.write_text(yaml.dump(bad_schema), encoding='utf-8')
    
    # 2. Create packet of that type
    data = base_envelope.copy()
    data['packet_type'] = ptype
    p = tmp_path / "overlap.yaml"
    p.write_text(yaml.dump(data), encoding='utf-8')
    
    # 3. Validation should fail (SCHEMA_VIOLATION)
    code, out, err = run_validator(str(p), args=["--schema", str(schema_path)])
    
    # The new fail-closed logic fails at schema load, which is EXIT_SCHEMA_VIOLATION (2, from EXIT_FAIL_GENERIC check? No, invalid key check is generic, overlap check is SCHEMA).
    # Wait, fail() prints to stderr. 
    assert code == 2 or code == 1
    assert "taxonomy intersection detected" in err or "Deprecated packet type" in err


