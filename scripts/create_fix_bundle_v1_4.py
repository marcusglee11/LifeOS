import zipfile
import shutil
from pathlib import Path

def main():
    repo_root = Path.cwd()
    artifacts_dir = repo_root / "artifacts"
    review_packets_dir = artifacts_dir / "review_packets"
    evidence_dir = artifacts_dir / "evidence"
    bundles_dir = artifacts_dir / "bundles"
    ceo_dir = artifacts_dir / "for_ceo"

    bundles_dir.mkdir(parents=True, exist_ok=True)
    ceo_dir.mkdir(parents=True, exist_ok=True)

    zip_name = "Bundle_OpenCode_Phase1_Fix_v1.4.zip"
    zip_path = bundles_dir / zip_name
    
    # Locate Packet Fix Summary (Brain or fallback)
    brain_path = Path(r"C:\Users\cabra\.gemini\antigravity\brain\c9967bad-7ca5-4451-b5fc-8f521b90e1e7\Packet_Fix_Summary.md")
    
    # Locate Stream File
    stream_file = None
    for f in evidence_dir.iterdir():
        if f.name.endswith(".out"):
            stream_file = f
            break
    if not stream_file:
        print("CRITICAL: Stream file missing from evidence dir.")
        exit(1)

    # Config File
    config_file = evidence_dir / "steward_runner_config_audit_verify_t5.yaml"
    # Helper Script
    helper_script = evidence_dir / "print_100.py"

    files_to_add = {
        review_packets_dir / "Review_Packet_OpenCode_Phase1_v1.0.md": "Review_Packet_OpenCode_Phase1_v1.0.md",
        brain_path: "Packet_Fix_Summary.md",
        artifacts_dir / "Evidence_Commands_And_Outputs.md": "Evidence_Commands_And_Outputs.md",
        evidence_dir / "Diff_TestChanges.patch": "Diff_TestChanges.patch",
        stream_file: f"artifacts/evidence/{stream_file.name}",
        config_file: "artifacts/evidence/steward_runner_config_audit_verify_t5.yaml",
        helper_script: "artifacts/evidence/print_100.py"
    }

    print(f"Creating bundle: {zip_path}")
    added_files = []
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path, arcname in files_to_add.items():
            if file_path.exists():
                print(f"Adding: {arcname}")
                zf.write(file_path, arcname=arcname)
                added_files.append(arcname)
            else:
                print(f"ERROR: Missing file {file_path}")
                exit(1)
        
        # Add listing
        listing_info = zipfile.ZipInfo("Bundle_Content_Listing.txt")
        listing_content = "\n".join(sorted(added_files + ["Bundle_Content_Listing.txt"]))
        zf.writestr(listing_info, listing_content)

    # Copy to CEO dir
    ceo_path = ceo_dir / zip_name
    print(f"Copying to: {ceo_path}")
    shutil.copy2(zip_path, ceo_path)
    print("Done.")

if __name__ == "__main__":
    main()
