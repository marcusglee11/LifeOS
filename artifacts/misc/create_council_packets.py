import os
import zipfile
import subprocess
from pathlib import Path

def create_zip(zip_name, file_list):
    print(f"Creating {zip_name}...")
    with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in file_list:
            if os.path.exists(file_path):
                if os.path.isdir(file_path):
                    for root, dirs, files in os.walk(file_path):
                        for file in files:
                            full_path = os.path.join(root, file)
                            arcname = os.path.relpath(full_path, os.path.dirname(file_path))
                            zipf.write(full_path, arcname)
                else:
                    zipf.write(file_path, os.path.basename(file_path))
            else:
                print(f"Warning: {file_path} does not exist.")

def run_tests_and_log(test_files, log_path):
    print(f"Running tests and logging to {log_path}...")
    with open(log_path, 'w') as f:
        subprocess.run(['pytest'] + test_files + ['-v'], stdout=f, stderr=subprocess.STDOUT)

if __name__ == "__main__":
    # 1. COUNCIL_CONTEXT_PACK_v1.zip
    context_files = [
        "docs/99_archive/legacy_structures/Governance/Council_Protocol_v1.0.md",
        "docs/99_archive/AI_Council_Procedural_Spec_v1.0.md",
        "docs/01_governance/ALIGNMENT_REVIEW_TEMPLATE_v1.0.md",
        "docs/09_prompts/v1.2/reviewer_architect_v1.2.md",
        "docs/09_prompts/v1.2/reviewer_risk_adversarial_v1.2.md",
        "docs/09_prompts/v1.2/reviewer_testing_v1.2.md",
        "docs/09_prompts/v1.2/reviewer_governance_v1.2.md",
        "docs/01_governance/Antigravity_Council_Review_Packet_Spec_v1.1.md"
    ]
    create_zip("artifacts/bundles/COUNCIL_CONTEXT_PACK_v1.zip", context_files)

    # 2. Evidence: Run tests
    policy_tests = [
        "runtime/tests/orchestration/loop/test_configurable_policy.py",
        "runtime/tests/orchestration/loop/test_policy.py",
        "runtime/tests/test_tool_policy.py"
    ]
    log_file = "artifacts/bundles/policy_engine_test_evidence.log"
    run_tests_and_log(policy_tests, log_file)

    # 3. COUNCIL_PACKET_Policy_Engine_Impl_v1.zip
    impl_files = [
        "runtime/governance/",
        "config/policy/",
        "runtime/tests/orchestration/loop/test_configurable_policy.py",
        "runtime/tests/orchestration/loop/test_policy.py",
        "runtime/tests/test_tool_policy.py",
        log_file
    ]
    create_zip("artifacts/bundles/COUNCIL_PACKET_Policy_Engine_Impl_v1.zip", impl_files)

    print("Done.")
