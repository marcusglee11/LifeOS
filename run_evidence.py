import os
import subprocess
import glob

def run_tests(validator, fixture_dir, filter_pattern="*"):
    print(f"\n### Validator: {os.path.basename(validator)}\n")
    print("```text")
    
    files = sorted(glob.glob(os.path.join(fixture_dir, filter_pattern)))
    
    # We need 1 PASS and 5 FAIL distinct.
    # Prioritize: pass_01, then fails.
    pass_files = [f for f in files if "pass" in f]
    fail_files = [f for f in files if "fail" in f]
    
    selected = pass_files[:1] + fail_files[:5]
    
    for fpath in selected:
        fname = os.path.basename(fpath)
        cmd = ["python", validator, fpath]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True)
            output = res.stdout.strip() or res.stderr.strip()
            print(f"> python {os.path.basename(validator)} {fname}")
            print(output)
        except Exception as e:
            print(f"Error running {fname}: {e}")
            
    print("```")

if __name__ == "__main__":
    repo_root = os.getcwd()
    run_tests("scripts/validate_review_packet.py", os.path.join(repo_root, "tests/fixtures/review_packet"), "*.md")
    run_tests("scripts/validate_plan_packet.py", os.path.join(repo_root, "tests/fixtures/plan_packet"), "*.md")
