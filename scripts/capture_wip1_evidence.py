import subprocess
import os
import sys
from pathlib import Path

def run_command(cmd, log_path, description):
    print(f"[{description}] Running: {' '.join(cmd)}")
    with open(log_path, "w", encoding="utf-8") as f:
        # Use subprocess.run with capture_output=False and stdout/stderr directed to file
        # to ensure raw output is captured without shell assumptions.
        result = subprocess.run(
            cmd,
            stdout=f,
            stderr=subprocess.STDOUT,
            text=True,
            env=os.environ.copy()
        )
    
    if result.returncode != 0:
        print(f"FAILED: {description}")
        print(f"Log: {log_path}")
        print("Exiting (fail-closed).")
        sys.exit(1)
        
    return result.returncode

def main():
    repo_root = Path(__file__).parent.parent.resolve()
    evidence_dir = repo_root / "artifacts" / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    
    fixture_cfg = repo_root / "runtime" / "tests" / "fixtures" / "wip1_config.yaml"
    
    # Task P0.8 - Evidence capture
    
    # 1. pytest
    # Configure pytest to not truncate output (-v, --tb=long, -vv)
    pytest_cmd = [sys.executable, "-m", "pytest", "runtime/tests/test_cli_skeleton.py", "-vv", "--tb=long"]
    run_command(pytest_cmd, evidence_dir / "wip1_pytest.log", "Pytest Suite")
    
    # 2. CLI status
    cli_status_cmd = [sys.executable, "-m", "runtime", "--config", str(fixture_cfg), "status"]
    run_command(cli_status_cmd, evidence_dir / "wip1_cli_status.log", "CLI Status")
    
    # 3. CLI config validate
    cli_val_cmd = [sys.executable, "-m", "runtime", "--config", str(fixture_cfg), "config", "validate"]
    run_command(cli_val_cmd, evidence_dir / "wip1_cli_config_validate.log", "CLI Config Validate")
    
    # 4. CLI config show
    cli_show_cmd = [sys.executable, "-m", "runtime", "--config", str(fixture_cfg), "config", "show"]
    run_command(cli_show_cmd, evidence_dir / "wip1_cli_config_show.log", "CLI Config Show")
    
    print(f"SUCCESS: Evidence captured to {evidence_dir}")

if __name__ == "__main__":
    main()
