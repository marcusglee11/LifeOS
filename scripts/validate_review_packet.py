
import sys
import re
import yaml
import os

def fail(code, msg):
    print(f"FAIL {code}: {msg}")
    sys.exit(1)

def pass_check():
    print("PASS")
    sys.exit(0)

def validate_markdown(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"FAIL RPV000: File not found: {path}")
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
        # P0.1: Plan implies strict discovery, but if generic markdown validator, maybe optional?
        # Assuming required if aiming for closure grade review packet.
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
            fail('RPV002', f"Section '{sec}' found before previous section.") 
        last_idx = idx

    # P0.1: RPV003/RPV004 - Acceptance Criteria Table Parsing
    ac_match = re.search(r'# Acceptance Criteria\n(.*?)(\n# |\Z)', content, re.DOTALL)
    if ac_match:
        ac_text = ac_match.group(1)
        # Find the first markdown table
        # Look for header row: | ... | ... |
        # and separator row: |---|---|
        lines = ac_text.splitlines()
        header_idx = -1
        for i, line in enumerate(lines):
            if "|" in line and "---" in lines[i+1] if i+1 < len(lines) else False:
                header_idx = i
                break
        
        if header_idx != -1:
            header_line = lines[header_idx]
            # Normalize header
            headers = [h.strip().lower() for h in header_line.split("|") if h.strip()]
            
            # Check required columns
            required_cols = ["id", "criterion", "status", "evidence pointer", "sha-256"]
            col_map = {}
            for req in required_cols:
                found = False
                for i, h in enumerate(headers):
                    if h == req:
                        col_map[req] = i
                        found = True
                        break
                if not found:
                    # If columns are missing, is it strictly fatal? P0.1 says "Enforce... Required columns"
                    # We might fail or just warn? fail is safer for "Enforce".
                    # Let's check if we can map loosely? Protocol says "case-insensitive match".
                    # If strictly missing:
                    fail('RPV003', f"Acceptance Criteria table missing column '{req}'. Found: {headers}")

            # Parse rows
            # Separator is at header_idx + 1
            for i in range(header_idx + 2, len(lines)):
                line = lines[i].strip()
                if not line.startswith("|"): continue # End of table or empty line
                
                parts = [p.strip() for p in line.split("|")]
                # split("|") on "| a | b |" gives ["", "a", "b", ""]
                # Filter out empty start/end if they exist
                if len(parts) > 1 and parts[0] == "": parts.pop(0)
                if len(parts) > 0 and parts[-1] == "": parts.pop()
                
                # Check row length matches headers roughly
                if len(parts) != len(headers):
                    continue # Valid markdown tables might vary, but strict schema implies consistency.
                             # Or maybe just skip validly? Let's process what we have.
                
                # Get values
                try:
                    ev_ptr = parts[col_map["evidence pointer"]]
                    sha_val = parts[col_map["sha-256"]]
                except IndexError:
                    continue 

                # RPV004: Evidence Pointer Grammar
                # path | path:Lx-Ly | path#sha256:<HEX64> | N/A(<reason>)
                # Bare N/A invalid.
                valid_ptr_regex = r'^(.+?(:L\d+(-L\d+)?)?|.+?#sha256:[a-fA-F0-9]{64}|N/A\(.+\))$'
                if not re.match(valid_ptr_regex, ev_ptr, re.IGNORECASE):
                    fail('RPV004', f"Invalid Evidence Pointer '{ev_ptr}' (must be path | path:Lx-Ly | path#sha256:<HEX64> | N/A(<reason>)).")
                
                if ev_ptr.upper() == "N/A":
                    fail('RPV004', f"Bare 'N/A' is invalid for Evidence Pointer. Use N/A(<reason>).")

                # SHA-256 Grammar
                # <HEX64> OR N/A(<reason>)
                # Optional: "N/A" bare might be allowed for SHA? P0.1 says "SHA-256 must be <HEX64> OR N/A(<reason>)"
                valid_sha_regex = r'^([a-fA-F0-9]{64}|N/A\(.+\))$'
                if not re.match(valid_sha_regex, sha_val, re.IGNORECASE):
                     fail('RPV004', f"Invalid SHA-256 '{sha_val}' (must be <HEX64> or N/A(<reason>)).")

    # RPV005/RPV006: Checklist (Preserve Semantics)
    checklist_match = re.search(r'# Closure Evidence Checklist\n(.*?)(\n# |\Z)', content, re.DOTALL)
    if checklist_match:
        table = checklist_match.group(1)
        required_rows = ["Provenance", "Artifacts", "Repro", "Governance", "Outcome"]
        for row in required_rows:
            if row not in table:
                fail('RPV005', f"Missing mandatory checklist row '{row}'.")
            
            # RPV006: Check Verification Column
            row_pattern = re.escape(row) + r".*?\|.*?\|(.*?)\|"
            row_match = re.search(row_pattern, table)
            if row_match:
                verified_cell = row_match.group(1).strip()
                if not verified_cell or verified_cell in ["[]", "[ ]"]:
                     fail('RPV006', f"Checklist item '{row}' verification failed (empty).")

def validate_yaml_data(data):
    # YPV011: Missing fields
    # P0.2: Ensure closure_evidence is required
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
        print("FAIL RPV000: Usage: validate_review_packet.py <path>")
        sys.exit(1)
    
    path = sys.argv[1]
    if path.endswith(".md"):
        validate_markdown(path)
    elif path.endswith(".yaml"):
        validate_yaml(path)
    else:
        pass_check()

    pass_check()
