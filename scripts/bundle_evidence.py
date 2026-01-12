import zipfile
import os
import shutil

def bundle_evidence():
    repo_root = os.getcwd()
    files = [
        'runtime/orchestration/operations.py',
        'artifacts/TEST_REPORT_BUILD_LOOP_PHASE2_v1.1_PASS.md',
        'docs/03_runtime/LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md'
    ]
    
    bundle_name = 'Phase2_Capabilities_Evidence.zip'
    bundle_dir = os.path.join(repo_root, 'artifacts', 'bundles')
    ceo_dir = os.path.join(repo_root, 'artifacts', 'for_ceo')
    
    os.makedirs(bundle_dir, exist_ok=True)
    os.makedirs(ceo_dir, exist_ok=True)
    
    bundle_path = os.path.join(bundle_dir, bundle_name)
    
    print(f"Bundling files into {bundle_path}...")
    with zipfile.ZipFile(bundle_path, 'w') as zipf:
        for f in files:
            full_path = os.path.join(repo_root, f)
            if os.path.exists(full_path):
                arcname = os.path.basename(f)
                zipf.write(full_path, arcname)
                print(f"  Added: {f}")
                
                # Copy for CEO pickup
                shutil.copy(full_path, ceo_dir)
                print(f"  Copied to pickup: {f}")
            else:
                print(f"  Warning: File not found: {f}")

if __name__ == "__main__":
    bundle_evidence()
