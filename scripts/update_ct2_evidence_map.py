#!/usr/bin/env python3
"""Update CT2 packet Ledger Evidence table from actual shipped artifacts."""
import hashlib
import re
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
CT2_PACKET = REPO_ROOT / "artifacts/plans/CT2_Activation_Packet_DocSteward_G3.md"
LEDGER_DIR = REPO_ROOT / "artifacts/ledger/dl_doc"

EVIDENCE_START = "### 3.3 Ledger Evidence (Sorted by Path)"
EVIDENCE_END = "### 3.4"

def compute_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()

def get_ledger_files():
    """Get relevant ledger files sorted by path."""
    files = []
    for f in sorted(LEDGER_DIR.glob("*.yaml")):
        if any(x in f.name for x in ["_smoke_test_", "_neg_test_"]):
            rel_path = f.relative_to(REPO_ROOT).as_posix()
            sha = compute_sha256(f)
            files.append((rel_path, sha))
    return files

def generate_evidence_table(files):
    """Generate markdown table from files."""
    lines = [
        "",
        "| Artifact Path | SHA256 |",
        "|---------------|--------|"
    ]
    for path, sha in files:
        lines.append(f"| `{path}` | `{sha}` |")
    lines.append("")
    return "\n".join(lines)

def main():
    print("[UPDATE] Scanning ledger files...")
    files = get_ledger_files()
    print(f"[UPDATE] Found {len(files)} ledger artifacts")
    
    if not files:
        print("[ERROR] No ledger files found")
        return
    
    # Read packet
    content = CT2_PACKET.read_text(encoding="utf-8")
    
    # Find markers
    start_idx = content.find(EVIDENCE_START)
    end_idx = content.find(EVIDENCE_END)
    
    if start_idx == -1:
        print("[ERROR] Could not find evidence start marker")
        return
        
    # Find end of the header line
    header_end = content.find("\n", start_idx) + 1
    
    # Generate new table
    new_table = generate_evidence_table(files)
    
    # Replace content
    if end_idx == -1:
        # No end marker, append after header
        new_content = content[:header_end] + new_table + "\n" + content[header_end:]
    else:
        new_content = content[:header_end] + new_table + "\n" + content[end_idx:]
    
    # Write back
    CT2_PACKET.write_text(new_content, encoding="utf-8")
    print(f"[UPDATE] CT2 packet updated with {len(files)} evidence entries")
    
    # Show table
    for path, sha in files:
        print(f"  {path}: {sha[:16]}...")

if __name__ == "__main__":
    main()
