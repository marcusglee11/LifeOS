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

FIXTURE_DIR = resolve_fixture_dir("review_packet")
print(f"Fixture Target: {FIXTURE_DIR}")

BASE = """---
artifact_id: "uuid"
artifact_type: "REVIEW_PACKET"
schema_version: "1.0.0"
created_at: "2026-01-01T00:00:00Z"
author: "Antigravity"
version: "1.0"
status: "PENDING_REVIEW"
terminal_outcome: "PASS"
closure_evidence: {}
---

# Review_Packet_Mission_v1.0

# Scope Envelope
- S

# Summary
S

# Issue Catalogue
| Id | D | R | S |
|---|---|---|---|

# Acceptance Criteria
| C | S | E | H |
|---|---|---|---|

# Closure Evidence Checklist
| Category | Requirement | Verified |
|----------|-------------|----------|
| **Provenance** | Code | [Hash] |
| **Artifacts** | Ledger | [Path] |
| **Repro** | Cmd | [Cmd] |
| **Governance** | Routing | [Ref] |
| **Outcome** | Proof | [PASS] |

# Non-Goals
- N

# Appendix
"""

FILES = {
    "pass_01.md": BASE,
    "fail_RPV001.md": BASE.replace("# Scope Envelope", ""),
    "fail_RPV002.md": BASE.replace("# Summary", "# Scope Envelope").replace("# Scope Envelope", "# Summary", 1),
    "fail_RPV005.md": BASE.replace("| **Provenance** |", "| **Missing** |"),
    "fail_RPV006.md": BASE.replace("| [Hash] |", "| |"),
    "fail_YPV013.md": BASE.replace('closure_evidence: {}', '') # was fail_11_yaml, now YPV013 per plan
}

sorted_filenames = sorted(FILES.keys())
for name in sorted_filenames:
    content = FILES[name]
    with open(os.path.join(FIXTURE_DIR, name), "w", encoding="utf-8") as f:
        f.write(content)

print(f"Generated {len(FILES)} Review Packet fixtures in {FIXTURE_DIR}")
