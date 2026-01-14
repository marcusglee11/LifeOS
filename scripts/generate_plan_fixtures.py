import os
import sys

def resolve_repo_root():
    # Deterministic discovery: Walk up until .git or GEMINI.md
    current = os.path.abspath(os.path.dirname(__file__))
    while True:
        if os.path.exists(os.path.join(current, ".git")) or os.path.exists(os.path.join(current, "GEMINI.md")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            print("[FAIL] Could not resolve repo root (no .git or GEMINI.md found).")
            sys.exit(1)
        current = parent

REPO_ROOT = resolve_repo_root()

# P0.2: Fixture destination discovery
# Priority: tests/fixtures/ -> test/fixtures/ -> fixtures/ -> create tests/fixtures/<type>
def resolve_fixture_dir(packet_type):
    candidates = [
        os.path.join(REPO_ROOT, "tests", "fixtures"),
        os.path.join(REPO_ROOT, "test", "fixtures"),
        os.path.join(REPO_ROOT, "fixtures")
    ]
    for c in candidates:
        if os.path.exists(c):
            target = os.path.join(c, packet_type)
            os.makedirs(target, exist_ok=True)
            return target
    
    # Fallback: Create tests/fixtures/<type>
    target = os.path.join(REPO_ROOT, "tests", "fixtures", packet_type)
    os.makedirs(target, exist_ok=True)
    return target

FIXTURE_DIR = resolve_fixture_dir("plan_packet")
print(f"Fixture Target: {FIXTURE_DIR}")

BASE = """# Scope Envelope
- **In-Scope Artefacts (resolved by discovery)**: X

# Proposed Changes
- P

# Claims
- **Claim**: C
  - **Type**: policy_mandate
  - **Evidence Pointer**: path/to/file:L1-L10
  - **Status**: asserted

# Targets
- T

# Validator Contract
- O

# Verification Matrix
| Case | Input | Expected | Code | Prefix |
|---|---|---|---|---|
| P1 | i | PASS | | |
| F1 | i | FAIL | C1 | |
| F2 | i | FAIL | C2 | |
| F3 | i | FAIL | C3 | |
| F4 | i | FAIL | C4 | |
| F5 | i | FAIL | C5 | |
# Migration Plan
- M

# Governance Impact
- G
"""

# Stable naming: pass_01.md, fail_<CODE>.md
FILES = {
    "pass_01.md": BASE,
    "fail_PPV001.md": BASE.replace("# Scope Envelope", ""),
    "fail_PPV002.md": BASE.replace("# Proposed Changes", "# Scope Envelope").replace("# Scope Envelope", "# Proposed Changes", 1),
    "fail_PPV003.md": BASE.replace("asserted", "proven").replace("- **Evidence Pointer**: path/to/file:L1-L10", ""), # Removes line, triggers PPV003
    "fail_PPV005.md": BASE.replace("asserted", "proven").replace("path/to/file:L1-L10", "nonexistent_file.md"),
    "fail_PPV006.md": BASE.replace("| F5 | i | FAIL | C5 | |", ""),
    "fail_PPV007.md": BASE.replace("# Validator Contract", "# Validator Contract\n FAIL RPV001"),
    "fail_PPV008.md": BASE.replace("- T", "- **Target**: /absolute/path\n- **Mode**: discover") 
}

sorted_filenames = sorted(FILES.keys())
for name in sorted_filenames:
    content = FILES[name]
    with open(os.path.join(FIXTURE_DIR, name), "w", encoding="utf-8") as f:
        f.write(content)

print(f"Generated {len(FILES)} PPV fixtures in {FIXTURE_DIR}")
