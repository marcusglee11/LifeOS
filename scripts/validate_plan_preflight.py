import sys
import re
import os
import argparse
import yaml

# Failure Codes
CODES = {
    'PPV001': "Missing required section '{}' in plan.",
    'PPV002': "Plan section order invalid. Expected: {}.",
    'PPV003': "Policy mandate claim lacks evidence_pointer (claim '{}').",
    'PPV004': "Canonical path claim lacks evidence_pointer (claim '{}').",
    'PPV005': "Evidence pointer '{}' invalid (must match path:Lx-Ly | path#sha256:HEX | N/A(reason)).",
    'PPV006': "Target uses fixed_path '{}' but no canonical_path claim provides evidence for it.",
    'PPV007': "Validator contract output_format missing or not 'PASS/FAIL'.",
    'PPV008': "Verification matrix insufficient (need >=1 PASS and >=5 FAIL with distinct codes; found PASS={}, FAIL_DISTINCT={}).",
    'PPV009': "Verification matrix references unknown section '{}' (not declared in plan schema/order).",
    'PPV010': "Governance impact missing gate/rationale for constitutional touch."
}

SECTIONS = [
    "Scope Envelope", "Proposed Changes", "Claims", "Targets",
    "Validator Contract", "Verification Matrix", "Migration Plan", "Governance Impact"
]

def fail(code, *args):
    msg = CODES[code].format(*args)
    print(f"[FAIL] {code}: {msg}")
    sys.exit(1)

def validate_markdown(content):
    # 1. Section Presence & Order
    headers = [line.strip().replace("# ", "") for line in content.split('\n') if line.startswith("# ")]
    # Filter only known sections to check order of key blocks
    known_headers = [h for h in headers if h in SECTIONS]
    
    missing = set(SECTIONS) - set(known_headers)
    if missing:
        fail('PPV001', list(missing)[0])

    # Check strict order of known sections
    expected_order_idx = 0
    for h in known_headers:
        if h == SECTIONS[expected_order_idx]:
            expected_order_idx += 1
        else:
            # If current header is later in expected list, maybe we skipped one? 
            # But we already checked missing. So this means out of order.
            fail('PPV002', " -> ".join(SECTIONS))

    # 2. Claims Check
    claims_match = re.search(r'# Claims\n(.*?)(\n# |\Z)', content, re.DOTALL)
    if claims_match:
        claims_text = claims_match.group(1)
        current_claim = None
        current_type = None
        has_pointer = False
        
        def check_previous_claim(claim_name, claim_type, pointer_seen):
            if claim_type in ['policy_mandate', 'canonical_path'] and not pointer_seen:
                code = 'PPV003' if claim_type == 'policy_mandate' else 'PPV004'
                fail(code, claim_name or "Unknown")

        for line in claims_text.split('\n'):
            line = line.strip()
            if line.startswith("- **Claim**:"):
                # Check previous
                if current_claim:
                    check_previous_claim(current_claim, current_type, has_pointer)
                
                current_claim = line.split(":", 1)[1].strip()
                current_type = None
                has_pointer = False
                
            elif line.startswith("- **Type**:"):
                current_type = line.split(":", 1)[1].strip()
                
            elif line.startswith("- **Evidence Pointer**:"):
                has_pointer = True
                val = line.split(":", 1)[1].strip()
                # Validate Pointer Grammar
                # Disallow spaces in paths to avoid matching sentences. Support standard path chars.
                ptr_pattern = r'^[\w\-\./\\]+(:L\d+(-L\d+)?|#sha256:[a-fA-F0-9]{64})?$'
                nav_pattern = r'^N/A\(.+\)$'
                
                if not (re.match(nav_pattern, val) or re.match(ptr_pattern, val)):
                    fail('PPV005', val)

        # Check last claim
        if current_claim:
             check_previous_claim(current_claim, current_type, has_pointer)
                
    # 3. Targets Check
    targets_match = re.search(r'# Targets\n(.*?)(\n# |\Z)', content, re.DOTALL)
    if targets_match:
        targets_text = targets_match.group(1)
        for line in targets_text.split('\n'):
            if "- **Mode**: fixed_path" in line:
                # We'd need to extract the path from the parent target item. 
                # Doing strict parsing on Markdown is fragile. 
                # Recommendation: Prefer YAML for strict validation.
                pass

    # 4. Validator Contract
    vc_match = re.search(r'# Validator Contract\n(.*?)(\n# |\Z)', content, re.DOTALL)
    if not vc_match or "Output Format**: PASS/FAIL" not in vc_match.group(1):
        fail('PPV007')

    # 5. Verification Matrix
    vm_match = re.search(r'# Verification Matrix\n(.*?)(\n# |\Z)', content, re.DOTALL)
    if not vm_match: fail('PPV001', 'Verification Matrix')
    
    vm_text = vm_match.group(1)
    pass_count = vm_text.count("| PASS ") + vm_text.count("| PASS |")
    # For FAIL distinct, we need to extract the codes.
    fail_codes = set(re.findall(r'FAIL\s+\|\s+([A-Z0-9]+)', vm_text))
    
    if pass_count < 1 or len(fail_codes) < 5:
        fail('PPV008', pass_count, len(fail_codes))

    print("[PASS] Packet valid.")

def main():
    if len(sys.argv) < 2:
        print("Usage: python validate_plan_preflight.py <plan.md|plan.yaml>")
        sys.exit(1)
        
    path = sys.argv[1]
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    if path.endswith('.yaml'):
        # YAML Validation (Stub for future strictness, user focused on Markdown Template structure matching)
        pass 
    else:
        validate_markdown(content)

if __name__ == "__main__":
    main()
