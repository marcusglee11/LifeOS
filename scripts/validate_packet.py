#!/usr/bin/env python3
import sys
import yaml
import json
import argparse
import re
import os
import glob
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Set, Tuple
from uuid import UUID

# Exit Codes
EXIT_PASS = 0
EXIT_FAIL_GENERIC = 1
EXIT_SCHEMA_VIOLATION = 2
EXIT_SECURITY_VIOLATION = 3
EXIT_LINEAGE_VIOLATION = 4
EXIT_REPLAY_VIOLATION = 5
EXIT_VERSION_INCOMPATIBLE = 6

DEFAULT_SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "../docs/02_protocols/schemas/lifeos_packet_schemas_CURRENT.yaml")

# Global Schema Holder (loaded at runtime)
SCHEMA: Dict[str, Any] = {}

def fail(code: int, message: str):
    print(f"[FAIL] {message}", file=sys.stderr)
    sys.exit(code)

def load_schema(path: str):
    global SCHEMA
    try:
        if not os.path.exists(path):
            fail(EXIT_FAIL_GENERIC, f"Schema file not found: {path}")
        with open(path, 'r', encoding='utf-8') as f:
            SCHEMA = yaml.safe_load(f)
            
        # Basic validation of the schema itself
        required_keys = ["schema_version", "limits", "envelope", "taxonomy", "payloads"]
        for k in required_keys:
            if k not in SCHEMA:
                fail(EXIT_FAIL_GENERIC, f"Schema definition invalid: missing top-level key '{k}'")
                
        # Taxonomy Overlap Check (P0.2 - Fail Closed)
        core = set(SCHEMA['taxonomy']['core_packet_types'])
        deprecated = set(SCHEMA['taxonomy']['deprecated_packet_types'])
        overlap = core.intersection(deprecated)
        if overlap:
            fail(EXIT_SCHEMA_VIOLATION, f"Schema taxonomy intersection detected: {overlap}")
            
    except Exception as e:
        fail(EXIT_FAIL_GENERIC, f"Failed to load schema from {path}: {e}")

def parse_yaml_payload(content: str) -> Dict[str, Any]:
    try:
        return yaml.safe_load(content)
    except yaml.YAMLError as e:
        fail(EXIT_SCHEMA_VIOLATION, f"Invalid YAML format: {e}")

def extract_packet_data(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        fail(EXIT_FAIL_GENERIC, f"File not found: {path}")
    
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Size Check (Schema Driven)
    max_size_kb = SCHEMA['limits']['max_payload_size_kb']
    if len(content.encode('utf-8')) > max_size_kb * 1024:
        fail(EXIT_SECURITY_VIOLATION, f"Payload size exceeds {max_size_kb}KB limit")

    if path.endswith('.md'):
        match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
        if not match:
            fail(EXIT_SCHEMA_VIOLATION, "Markdown file missing YAML frontmatter")
        # P0.3 Hashing Note: We hash the PARSED dictionary re-emitted, not raw string, 
        # to ensure deterministic key ordering.
        return parse_yaml_payload(match.group(1))
    else:
        return parse_yaml_payload(content)

def canonicalize_and_hash(data: Dict[str, Any]) -> str:
    # 1) Re-emit as YAML: keys sorted, allow_unicode=True
    # Using sort_keys=True ensures field ordering doesn't affect hash.
    # Note: This effectively hashes the "canonical" representation of the content.
    canonical_str = yaml.dump(data, sort_keys=True, allow_unicode=True, width=float("inf"))
    # 2) SHA256
    return hashlib.sha256(canonical_str.encode('utf-8')).hexdigest()

def validate_uuid(val: Any, field: str):
    if not isinstance(val, str):
        fail(EXIT_SCHEMA_VIOLATION, f"Field '{field}' must be a string UUID")
    try:
        UUID(val)
    except ValueError:
        fail(EXIT_SCHEMA_VIOLATION, f"Field '{field}' is not a valid UUID: {val}")

def validate_timestamp(val: Any, field: str, ignore_skew: bool):
    if not isinstance(val, str):
        fail(EXIT_SCHEMA_VIOLATION, f"Field '{field}' must be a string ISO timestamp")
    try:
        dt = datetime.fromisoformat(val.replace('Z', '+00:00'))
        
        # Clock Skew Enforcement (Schema Driven)
        if not ignore_skew:
            max_skew = SCHEMA['limits']['max_clock_skew_seconds']
            now = datetime.now(timezone.utc)
            skew = abs((now - dt).total_seconds())
            if skew > max_skew:
                fail(EXIT_SECURITY_VIOLATION, f"Clock skew {skew}s exceeds max {max_skew}s")
    except ValueError:
        fail(EXIT_SCHEMA_VIOLATION, f"Field '{field}' invalid timestamp format: {val}")

def validate_ttl(data: Dict[str, Any]):
    # TTL Enforcement (P0.2)
    created_at = datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
    ttl = data.get('ttl_hours', 72)
    
    if ttl == 0: return # Infinite
    
    if not isinstance(ttl, int):
        fail(EXIT_SCHEMA_VIOLATION, "ttl_hours must be integer")

    now = datetime.now(timezone.utc)
    age_hours = (now - created_at).total_seconds() / 3600
    if age_hours > ttl:
        fail(EXIT_SECURITY_VIOLATION, f"Packet TTL expired. Age: {age_hours:.2f}h > TTL: {ttl}h")

def validate_signature(data: Dict[str, Any]):
    # Signature Enforcement (Schema-Driven)
    ptype = data['packet_type']
    is_draft = data.get('is_draft', False)
    sig_stub = data.get('signature_stub')

    # Load policy from schema
    sig_policy = SCHEMA.get('signature_policy', {})
    require_for_non_draft = sig_policy.get('require_for_non_draft', True)
    require_for_types = set(sig_policy.get('require_for_packet_types', []))

    required = False
    if ptype in require_for_types:
        required = True
    elif require_for_non_draft and not is_draft:
        required = True
    
    if required and not sig_stub:
        fail(EXIT_SECURITY_VIOLATION, f"Signature stub required for {ptype} (is_draft={is_draft})")
    
    if sig_stub:
        if not isinstance(sig_stub, dict):
            fail(EXIT_SCHEMA_VIOLATION, "signature_stub must be object")
        if 'signer' not in sig_stub or 'method' not in sig_stub:
            fail(EXIT_SCHEMA_VIOLATION, "signature_stub missing signer or method")

def validate_envelope_and_taxonomy(data: Dict[str, Any], ignore_skew: bool, allow_deprecated: bool):
    # Envelope Required Fields (Schema Driven)
    required_env = set(SCHEMA['envelope']['required'])
    
    for field in required_env:
        if field not in data:
            fail(EXIT_SCHEMA_VIOLATION, f"Missing required envelope field: {field}")

    validate_uuid(data['packet_id'], 'packet_id')
    validate_uuid(data['chain_id'], 'chain_id')
    validate_uuid(data['nonce'], 'nonce')
    validate_timestamp(data['created_at'], 'created_at', ignore_skew)

    expected_version = SCHEMA.get('schema_version', '1.1')
    
    # SemVer Minor Compatibility (P0.2)
    try:
        p_major, p_minor = map(int, data['schema_version'].split('.')[:2])
        e_major, e_minor = map(int, expected_version.split('.')[:2])
        
        if p_major != e_major or p_minor > e_minor:
             fail(EXIT_VERSION_INCOMPATIBLE, f"Packet version {data['schema_version']} incompatible with schema v{expected_version}")
             
    except ValueError:
        # Fallback to strict string equality if non-semver
        if data['schema_version'] != expected_version:
            fail(EXIT_VERSION_INCOMPATIBLE, f"Packet version {data['schema_version']} != {expected_version}")

    # Compression Check (P1.1 - Fail Closed)
    if data.get('compression'):
        fail(EXIT_SCHEMA_VIOLATION, f"Compression not supported in v{expected_version} validator")

    # Taxonomy Enforcement (Schema Driven)
    ptype = data['packet_type']
    core_types = set(SCHEMA['taxonomy']['core_packet_types'])
    deprecated_types = set(SCHEMA['taxonomy']['deprecated_packet_types'])
    
    # Fail-closed deprecated check (P0.2)
    # Check if type is deprecated first, regardless of core membership to prevent bypass via overlap
    if ptype in deprecated_types:
        if not allow_deprecated:
            fail(EXIT_SCHEMA_VIOLATION, f"Deprecated packet type {ptype} requires --allow-deprecated")
            
    # Core valid check 
    if ptype not in core_types:
        # If not core and we already passed deprecated check (or it wasn't deprecated),
        # then it is truly unknown.
        # Note: If it WAS deprecated and allowed, and ALSO not in core (normal case), we pass.
        # If it IS in core, we pass.
        
        # Determine if we should fail as unknown
        if ptype not in deprecated_types:
             fail(EXIT_SCHEMA_VIOLATION, f"Unknown packet type: {ptype}")

    if 'is_draft' in data and not isinstance(data['is_draft'], bool):
        fail(EXIT_SCHEMA_VIOLATION, "is_draft must be boolean")

def validate_payload(data: Dict[str, Any]):
    ptype = data['packet_type']
    
    # Payload Definition from Schema
    payload_def = SCHEMA['payloads'].get(ptype)
    
    # If payload definition missing but type was valid, it might be a type with no payload spec 
    # (unlikely based on v1.1, but safeguard). Or if deprecated type has definition.
    if not payload_def:
        # If deprecated type is allowed and has a definition, use it.
        # Check if it exists in schema even if not core.
        pass 

    if payload_def:
        allowed_payload_fields = set(payload_def.get('allow', []))
        required_payload_fields = set(payload_def.get('required', []))
        
        # Envelope fields (Schema Driven - union of required and optional)
        envelope_fields = set(SCHEMA['envelope']['required']) | set(SCHEMA['envelope'].get('optional', []))
        
        all_keys = set(data.keys())
        # envelope mixed with payload
        unknown = all_keys - envelope_fields - allowed_payload_fields
        
        if unknown:
            fail(EXIT_SCHEMA_VIOLATION, f"Unknown fields for type {ptype}: {unknown}")

        # P0.1 Required Fields Check
        missing = required_payload_fields - all_keys
        if missing:
            fail(EXIT_SCHEMA_VIOLATION, f"Missing required payload fields for {ptype}: {missing}")

    if ptype == "COUNCIL_APPROVAL_PACKET":
        if "review_packet_id" not in data or "subject_hash" not in data:
            fail(EXIT_LINEAGE_VIOLATION, "COUNCIL_APPROVAL_PACKET missing lineage fields")

def validate_bundle(directory: str, ignore_skew: bool, allow_deprecated: bool):
    # P0.2 Full Validation + Replay
    files = sorted(glob.glob(os.path.join(directory, "*")))
    seen_nonces: Dict[str, str] = {}
    review_hashes: Dict[str, str] = {} # packet_id -> hash
    approvals: List[Dict[str, Any]] = []

    print(f"Validating bundle: {directory} ({len(files)} files)")
    
    for fpath in files:
        if not (fpath.endswith('.yaml') or fpath.endswith('.md') or fpath.endswith('.yml')):
            continue
            
        try:
            # 1. Extract
            data = extract_packet_data(fpath)
            
            # 2. Canonical Hash (for Lineage)
            # Only hash COUNCIL_REVIEW_PACKETs for now as they are subjects of approvals
            if data.get('packet_type') == 'COUNCIL_REVIEW_PACKET' and 'packet_id' in data:
                review_hashes[data['packet_id']] = canonicalize_and_hash(data)
            
            # Collect Approvals for Phase 2 Lineage Check
            if data.get('packet_type') == 'COUNCIL_APPROVAL_PACKET':
                approvals.append(data)

            # 3. Full Validation (P0.2)
            validate_envelope_and_taxonomy(data, ignore_skew, allow_deprecated)
            validate_ttl(data)
            validate_signature(data)
            validate_payload(data)

            # 4. Replay Check (P0.2)
            if 'nonce' in data:
                nonce = data['nonce']
                if nonce in seen_nonces:
                    fail(EXIT_REPLAY_VIOLATION, f"Duplicate nonce {nonce} in {fpath} (seen in {seen_nonces[nonce]})")
                seen_nonces[nonce] = fpath

        except Exception as e:
            # Propagate exit codes if they come from fail()
            if isinstance(e, SystemExit):
                if e.code != 0: raise # Re-raise failures
            else:
                 fail(EXIT_FAIL_GENERIC, f"Bundle file {fpath} failed validation: {e}")

    # Phase 2: Lineage Verification (P0.3)
    for appv in approvals:
        ref_id = appv.get('review_packet_id')
        ref_hash = appv.get('subject_hash')
        
        if ref_id not in review_hashes:
            # We do not fail immediately if it's missing from the bundle. 
            # Prompt says "lookup review_packet_id in map; if missing => fail(EXIT_LINEAGE_VIOLATION)" (implicitly assumes bundle contains closure)
            # Assuming bundle MUST contain the reviewed packet to verify linkage.
            fail(EXIT_LINEAGE_VIOLATION, f"Approval {appv.get('packet_id')} references missing Review Packet {ref_id}")
        
        expected = review_hashes[ref_id]
        if ref_hash != expected:
            fail(EXIT_LINEAGE_VIOLATION, f"Approval {appv.get('packet_id')} subject_hash mismatch. Expected {expected}, got {ref_hash}")

def main():
    parser = argparse.ArgumentParser(description="LifeOS Packet Validator (Strict v1.1 - Schema Driven)")
    parser.add_argument("path", nargs='?', help="Path to packet file or bundle directory")
    parser.add_argument("--bundle", help="Directory containing bundle of packets", metavar="DIR")
    parser.add_argument("--ignore-skew", action="store_true", help="Ignore clock skew checks")
    parser.add_argument("--allow-deprecated", action="store_true", help="Allow deprecated packet types")
    parser.add_argument("--schema", help="Path to schema definition YAML", default=DEFAULT_SCHEMA_PATH)
    args = parser.parse_args()

    # Load Schema
    load_schema(args.schema)

    try:
        if args.bundle:
            if not os.path.isdir(args.bundle):
                 fail(EXIT_FAIL_GENERIC, f"Bundle path is not a directory: {args.bundle}")
            validate_bundle(args.bundle, args.ignore_skew, args.allow_deprecated)
            print("[PASS] Bundle valid.")
            sys.exit(EXIT_PASS)
        elif args.path:
            # CLI 'path' could be a directory too if user forgot --bundle? 
            # Check if directory
            if os.path.isdir(args.path):
                 fail(EXIT_FAIL_GENERIC, f"Path is directory. Use --bundle to validate a directory.")

            data = extract_packet_data(args.path)
            validate_envelope_and_taxonomy(data, args.ignore_skew, args.allow_deprecated)
            validate_ttl(data)
            validate_signature(data)
            validate_payload(data)
            print("[PASS] Packet valid.")
            sys.exit(EXIT_PASS)
        else:
            parser.print_help()
            sys.exit(EXIT_FAIL_GENERIC)
    except SystemExit as e:
        sys.exit(e.code)
    except Exception as e:
        print(f"[CRASH] Unhandled exception: {e}", file=sys.stderr)
        sys.exit(EXIT_FAIL_GENERIC)

if __name__ == "__main__":
    main()
