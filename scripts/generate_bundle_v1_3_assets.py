import sys
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

# Sentinel REPO_ROOT
def find_repo_root(start_path: Path) -> Path:
    current = start_path.resolve()
    while current != current.parent:
        if (current / "doc_steward").exists():
            return current
        current = current.parent
    raise RuntimeError("Could not find REPO_ROOT")

REPO_ROOT = find_repo_root(Path(__file__))
sys.path.insert(0, str(REPO_ROOT))

def main():
    evidence_dir = REPO_ROOT / "artifacts" / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Prepare Config and Script
    script_content = """
for i in range(100):
    print(f"Line {i}: Evidence capture test.")
"""
    script_path = evidence_dir / "print_100.py"
    script_path.write_text(script_content, encoding="utf-8")
    
    # Use forward slashes for config to avoid windows escaping issues in yaml
    log_dir = evidence_dir / "logs"
    streams_dir = log_dir / "streams"
    shutil.rmtree(log_dir, ignore_errors=True) # Clean start
    
    log_dir_str = str(log_dir).replace(os.sep, '/')
    streams_dir_str = str(streams_dir).replace(os.sep, '/')
    script_path_str = str(script_path).replace(os.sep, '/')
    python_path_str = sys.executable.replace(os.sep, '/')
    
    config_content = f"""
logging:
  log_dir: "{log_dir_str}"
  streams_dir: "{streams_dir_str}"
validators:
  commands:
    - ["{python_path_str}", "{script_path_str}"]
"""
    config_path = evidence_dir / "steward_runner_config_audit_verify_t5.yaml"
    config_path.write_text(config_content, encoding="utf-8")
    
    # 2. Run Steward Runner
    runner = REPO_ROOT / "scripts" / "steward_runner.py"
    run_id = "audit_verify_t5"
    
    cmd = [
        sys.executable, str(runner),
        "--config", str(config_path),
        "--run-id", run_id,
        "--step", "validators"
    ]
    
    print(f"Running: {' '.join(cmd)}")
    res = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    if res.returncode != 0:
        print("Runner Failed!")
        print(res.stderr)
        sys.exit(1)
        
    # 3. Locate and Secure Stream File
    stream_file = None
    if streams_dir.exists():
        for f in streams_dir.iterdir():
            if f.name.endswith(".out"):
                stream_file = f
                break
    
    if not stream_file:
        print("No stream file found!")
        sys.exit(1)
        
    # Copy stream file to evidence root for easy bundling
    final_stream_path = evidence_dir / stream_file.name
    shutil.copy2(stream_file, final_stream_path)
    
    # Clean up logs dir to keep evidence dir clean? 
    # Instruction says "Include the referenced stream/evidence file". 
    # We will bundle `artifacts/evidence/<hash>.out`.
    # We should delete the logs dir to avoid bundling it? No, keep it as debug residue is fine, but we won't bundle it.
    
    # 4. Generate Command Proofs
    
    # Relative path for command display
    rel_stream_path = f"artifacts/evidence/{stream_file.name}"
    
    # WC -L
    # Using python one-liner for portability as requested
    wc_cmd_str = f"python -c \"import sys; print(sum(1 for _ in open(sys.argv[1])), sys.argv[1])\" \"{rel_stream_path}\""
    # execute on absolute path
    wc_res = subprocess.run([sys.executable, "-c", f"print(sum(1 for _ in open('{final_stream_path}')), '{rel_stream_path}')"], capture_output=True, text=True)
    wc_output = wc_res.stdout.strip()
    
    # Excerpt Extraction
    extract_cmd_str = f"python -c \"lines=open('{rel_stream_path}').readlines(); print(''.join(lines[:3] + lines[-3:]), end='')\""
    extract_res = subprocess.run([sys.executable, "-c", f"lines=open('{final_stream_path}').readlines(); print(''.join(lines[:3] + lines[-3:]), end='')"], capture_output=True, text=True)
    extract_output = extract_res.stdout
    
    # 5. Write Evidence_Commands_And_Outputs.md
    md_content = f"""# Evidence Commands and Outputs
**Run ID**: {run_id}

## 1. Canonical Runner Invocation
**Config File**: `artifacts/evidence/steward_runner_config_audit_verify_t5.yaml`
**Command**:
```bash
python scripts/steward_runner.py --config artifacts/evidence/steward_runner_config_audit_verify_t5.yaml --run-id {run_id} --step validators
```

## 2. Line Count Proof
**Command**:
```bash
{wc_cmd_str}
```
**Output**:
```text
{wc_output}
```

## 3. Excerpt Extraction Proof
**Command**:
```bash
{extract_cmd_str}
```
**Output**:
```text
{extract_output}
```
"""
    (evidence_dir.parent / "Evidence_Commands_And_Outputs.md").write_text(md_content, encoding="utf-8")
    
    print(f"EVIDENCE_STREAM={stream_file.name}")

if __name__ == "__main__":
    main()
