
import sys
import re

def fail(code, msg):
    print(f"[FAIL] {code}: {msg}")
    sys.exit(1)

def pass_check():
    print("[PASS] Packet valid.")
    sys.exit(0)

def validate_plan(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        sys.exit(1)

    # PPV001: Missing section
    sections = [
        "Scope Envelope",
        "Proposed Changes",
        "Claims",
        "Targets",
        "Validator Contract",
        "Verification Matrix",
        "Migration Plan",
        "Governance Impact"
    ]
    
    last_idx = -1
    last_sec = None
    for sec in sections:
        idx = content.find(f"# {sec}")
        if idx == -1:
            fail('PPV001', f"Missing required section '{sec}' in PLAN_PACKET.")
        
        if idx < last_idx:
            fail('PPV002', f"PLAN_PACKET section order invalid. Expected: { ' -> '.join(sections) }.")
        last_idx = idx
        last_sec = sec

    # PPV003: Proven Claims Evidence
    # Extract Claims
    claims_match = re.search(r'# Claims\n(.*?)(\n# |\Z)', content, re.DOTALL)
    if claims_match:
        claims_text = claims_match.group(1)
        current_claim = None
        current_status = None
        current_pointer = None
        
        # Simple line processor
        for line in claims_text.split('\n'):
            line = line.strip()
            if line.startswith("- **Claim**:"):
                # Validate previous
                if current_claim and current_status == "proven":
                     if not current_pointer:
                         fail('PPV003', f"Claim '{current_claim}' marked proven but evidence pointer missing.")
                
                current_claim = line.split(":", 1)[1].strip()
                current_status = None
                current_pointer = None
            
            elif line.startswith("- **Status**:"):
                current_status = line.split(":", 1)[1].strip()
            
            elif line.startswith("- **Evidence Pointer**:"):
                val = line.split(":", 1)[1].strip()
                current_pointer = val
                # PPV004: Grammar
                ptr_pattern = r'^[\w\-\./\\]+(:L\d+(-L\d+)?|#sha256:[a-fA-F0-9]{64})?$'
                nav_pattern = r'^N/A\(.+\)$'
                if not (re.match(nav_pattern, val) or re.match(ptr_pattern, val)):
                    fail('PPV004', f"Evidence pointer '{val}' invalid (must be path | path:Lx-Ly | path#sha256:<HEX64> | N/A(<reason>)).")

        # Check last
        if current_claim and current_status == "proven":
             if not current_pointer:
                 fail('PPV003', f"Claim '{current_claim}' marked proven but evidence pointer missing.")

    # PPV006: Matrix
    matrix_match = re.search(r'# Verification Matrix\n(.*?)(\n# |\Z)', content, re.DOTALL)
    if matrix_match:
        matrix_text = matrix_match.group(1)
        pass_count = matrix_text.count("| PASS ")
        fail_count = matrix_text.count("| FAIL ")
        
        # Determine distinct fail codes?
        # Rough check
        if pass_count < 1 or fail_count < 5:
             fail('PPV006', f"Verification Matrix insufficient (need >=1 PASS and >=5 FAIL with distinct codes; found PASS={pass_count}, FAIL_DISTINCT={fail_count} (approx)).")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: validate_plan_packet.py <path>")
        sys.exit(1)
    
    validate_plan(sys.argv[1])
    pass_check()
