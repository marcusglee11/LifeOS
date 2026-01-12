"""
Build POSIX-compatible TDD Hardening Bundle v1.2
This script creates a zip with forward-slash paths for Unix/macOS/Linux compatibility.
"""
import zipfile
import os

REPO_ROOT = os.getcwd()
OUTPUT_ZIP = os.path.join(REPO_ROOT, "artifacts", "bundles", "Bundle_TDD_Hardening_Enforcement_v1.3.zip")

FILES_TO_BUNDLE = [
    ("tests_doc/test_tdd_compliance.py", os.path.join(REPO_ROOT, "tests_doc", "test_tdd_compliance.py")),
    ("tests_doc/tdd_compliance_allowlist.yaml", os.path.join(REPO_ROOT, "tests_doc", "tdd_compliance_allowlist.yaml")),
    ("tests_doc/tdd_compliance_allowlist.lock.json", os.path.join(REPO_ROOT, "tests_doc", "tdd_compliance_allowlist.lock.json")),
    ("artifacts/context_packs/CCP_Core_TDD_Principles_v1.0.md", os.path.join(REPO_ROOT, "artifacts", "context_packs", "CCP_Core_TDD_Principles_v1.0.md")),
]

def build_bundle():
    os.makedirs(os.path.dirname(OUTPUT_ZIP), exist_ok=True)
    
    with zipfile.ZipFile(OUTPUT_ZIP, 'w', zipfile.ZIP_DEFLATED) as zf:
        for arcname, filepath in FILES_TO_BUNDLE:
            if os.path.exists(filepath):
                # Write with forward-slash arcname (POSIX)
                zf.write(filepath, arcname)
                print(f"Added: {arcname}")
            else:
                print(f"WARNING: Missing {filepath}")
    
    print(f"\nBundle created: {OUTPUT_ZIP}")
    
    # Print manifest
    print("\n--- ZIP MANIFEST (sorted) ---")
    with zipfile.ZipFile(OUTPUT_ZIP, 'r') as zf:
        for name in sorted(zf.namelist()):
            print(name)

if __name__ == "__main__":
    build_bundle()
