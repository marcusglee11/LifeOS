import zipfile
import os
import argparse
from pathlib import Path

def package_fixpack(output_path, changed_files, reference_files, evidence_files):
    """
    Package fixpack with strict segregation of changed vs reference files.
    """
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        # 1. Changed Files (Root - Preserving Paths)
        for f in changed_files:
            if os.path.exists(f):
                # Write with full relative path to match repo structure
                zf.write(f, f)
            else:
                print(f"Warning: Changed file missing: {f}")

        # 2. Evidence Files (Root)
        for f in evidence_files:
            if os.path.exists(f):
                zf.write(f, os.path.basename(f))
            else:
                print(f"Warning: Evidence file missing: {f}")

        # 3. Reference Only Files (reference_only/ subdirectory)
        for f in reference_files:
            if os.path.exists(f):
                zf.write(f, f"reference_only/{os.path.basename(f)}")
            else:
                print(f"Warning: Reference file missing: {f}")
        
        # 4. Reference Only README
        zf.writestr(
            "reference_only/README.txt",
            "This directory contains files included for context/reference only.\n"
            "These files are NOT part of the patch delta and strictly SHOULD NOT be applied."
        )

    print(f"Bundle created: {output_path}")

if __name__ == "__main__":
    # Define payload
    changed = [
        "docs/01_governance/ARTEFACT_INDEX.json",
        ".gitattributes",
        "tools/validate_governance_index.py",
        "scripts/package_audit_fixpack.py"
    ]
    
    reference = [
        "docs/02_protocols/G-CBS_Standard_v1.0.md"
    ]
    
    evidence = [
        "artifacts/PATCH_POSTGO_HARDENING_GOV_INDEX_EOL_AND_PACKAGING_v0.5.diff",
        "artifacts/TEST_REPORT_POSTGO_HARDENING_GOV_INDEX_EOL_AND_PACKAGING_v0.5.md",
        "artifacts/review_packets/REVIEW_PACKET_POSTGO_HARDENING_GOV_INDEX_EOL_AND_PACKAGING_v0.5.md"
    ]
    
    output_zip = "artifacts/bundles/Bundle_PostGo_Hardening_GovIndex_EOL_v0.5.zip"
    
    os.makedirs(os.path.dirname(output_zip), exist_ok=True)
    package_fixpack(output_zip, changed, reference, evidence)
