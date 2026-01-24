import zipfile, os

impl_dirs = ['runtime/governance', 'config/policy']
test_files = ['runtime/tests/orchestration/loop/test_configurable_policy.py', 'runtime/tests/orchestration/loop/test_policy.py', 'runtime/tests/test_tool_policy.py']
evidence_log = 'artifacts/bundles/policy_engine_test_evidence.log'
f_name = 'artifacts/bundles/COUNCIL_PACKET_Policy_Engine_Impl_v1.zip'

print(f"Zipping to {f_name}")
with zipfile.ZipFile(f_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
    for d in impl_dirs:
        if not os.path.exists(d):
            print(f"Warning: {d} does not exist.")
            continue
        for root, dirs, files in os.walk(d):
            if '__pycache__' in root:
                continue
            for f in files:
                full_path = os.path.join(root, f)
                # Store relative to the root of the repo or reasonable structure
                arcname = full_path
                zipf.write(full_path, arcname)
    for f in test_files:
        if os.path.exists(f):
            zipf.write(f, f)
    if os.path.exists(evidence_log):
        zipf.write(evidence_log, os.path.basename(evidence_log))
print("Done")
