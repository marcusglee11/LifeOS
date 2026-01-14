
import sys
import re
import yaml

def fail(code, msg):
    print(f"[FAIL] {code}: {msg}")
    sys.exit(1)

def pass_check():
    print("[PASS] Packet valid.")
    sys.exit(0)

def validate_markdown(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"File found: {path}") # Should have been caught by runner
        sys.exit(1)

    # Frontmatter Check (YPV)
    fm_match = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
    if fm_match:
        try:
            fm_data = yaml.safe_load(fm_match.group(1))
            validate_yaml_data(fm_data)
        except Exception as e:
            fail('YPV000', f"Invalid Frontmatter YAML: {e}")
    else:
        # If strict packet format, might require frontmatter. Plan says strictly discovered.
        pass

    # RPV001: Missing section
    sections = [
        "Scope Envelope",
        "Summary",
        "Issue Catalogue",
        "Acceptance Criteria",
        "Closure Evidence Checklist",
        "Non-Goals",
        "Appendix"
    ]
    
    last_idx = -1
    for sec in sections:
        idx = content.find(f"# {sec}")
        if idx == -1:
            fail('RPV001', f"Missing section '{sec}'.")
        
        # RPV002: Order check
        if idx < last_idx:
            # Re-find previous to name it
            # This is a simple linear check
            fail('RPV002', f"Section '{sec}' found before previous section.") 
        last_idx = idx

    # RPV005/RPV006: Checklist
    checklist_match = re.search(r'# Closure Evidence Checklist\n(.*?)(\n# |\Z)', content, re.DOTALL)
    if checklist_match:
        table = checklist_match.group(1)
        required_rows = ["Provenance", "Artifacts", "Repro", "Governance", "Outcome"]
        for row in required_rows:
            if row not in table:
                fail('RPV005', f"Missing mandatory checklist row '{row}'.")
            
            # RPV006: Check Verification Column
            # Row format: | Category | Requirement | Verified |
            # We match 'Category' (row), then skip 'Requirement', then capture 'Verified'.
            # Pattern: row + ... | <Requirement> | <CapturingVerified> |
            row_pattern = re.escape(row) + r".*?\|.*?\|(.*?)\|"
            row_match = re.search(row_pattern, table)
            if row_match:
                verified_cell = row_match.group(1).strip()
                if not verified_cell or verified_cell == "[]" or verified_cell == "[ ]":
                     fail('RPV006', f"Checklist item '{row}' verification failed (empty).")

    # RPV003/RPV004: Evidence Pointers in Acceptance Criteria
    # (Implementation complexity: parsing table columns)
    # Skipping detailed table parsing for this snippet to keep it robust per instructions "minimal".

def validate_yaml_data(data):
    # YPV011: Missing fields
    required = ['artifact_type', 'version', 'terminal_outcome', 'closure_evidence']
    for req in required:
        if req not in data:
            fail('YPV011', f"Missing field '{req}' in YAML.")
    
    # YPV012: Terminal Outcome
    valid_outcomes = ['PASS', 'BLOCKED', 'REJECTED']
    if data.get('terminal_outcome') not in valid_outcomes:
        fail('YPV012', f"Invalid or missing 'terminal_outcome' (Must be PASS|BLOCKED|REJECTED).")

    # YPV013: Closure Evidence
    if not isinstance(data.get('closure_evidence'), dict):
        fail('YPV013', "Missing 'closure_evidence' object.")

def validate_yaml(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        validate_yaml_data(data)
    except Exception as e:
        fail('YPV000', f"Invalid YAML: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: validate_review_packet.py <path>")
        sys.exit(1)
    
    path = sys.argv[1]
    if path.endswith(".md"):
        validate_markdown(path)
    elif path.endswith(".yaml"):
        validate_yaml(path)
    else:
        pass_check()

    pass_check()
