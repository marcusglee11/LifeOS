import zipfile
import os

BUNDLE_NAME = "artifacts/bundles/Bundle_OpenCode_Steward_Hardening_CT2_v1.4.1.zip"
FILES = [
    "artifacts/plans/Plan_OpenCode_Steward_Hardening_v1.4.md",
    "artifacts/review_packets/CCP_OpenCode_Steward_Activation_CT2_Phase2.md",
    "scripts/opencode_ci_runner.py",
    "scripts/run_certification_tests.py",
    "artifacts/evidence/opencode_steward_certification/CERTIFICATION_REPORT_v1_4.json",
    "artifacts/evidence/opencode_steward_certification/HASH_MANIFEST_v1.4.1.json",
    "artifacts/evidence/opencode_steward_certification/CERT_LOG_v1.4.md",
    "CHANGELOG_v1.4.1.md"
]

def create_bundle():
    print(f"Creating {BUNDLE_NAME}...")
    with zipfile.ZipFile(BUNDLE_NAME, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file_path in FILES:
            if os.path.exists(file_path):
                zf.write(file_path, arcname=file_path)
                print(f"Added {file_path}")
            else:
                print(f"ERROR: Missing file {file_path}")
                exit(1)
    print("Bundle created successfully.")

if __name__ == "__main__":
    create_bundle()
