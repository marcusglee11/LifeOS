#!/usr/bin/env python3
"""
Mission Synthesis Engine MVP Verification Runner
=================================================

Runs all verification gates and produces a single PASS/FAIL report.
No external dependencies beyond stdlib + repo-approved packages.

Evidence contract:
- Full SHA-256 hashes (no truncation)
- Exact commands with exit codes
- Deterministic ordering
- Complete artifact references
- Strict E2E semantics (Wiring vs Completion)

Usage:
    python scripts/verify_mission_synthesis_mvp.py [--live] [--scratch]
    
Options:
    --live     Run live connectivity checks (default: offline only)
    --scratch  Run E2E in a isolated scratch workspace for audit purity
"""

import subprocess
import hashlib
import json
import os
import sys
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Tuple


def detect_repo_root() -> Path:
    """Detect repo root via .git or GEMINI.md marker."""
    cwd = Path.cwd()
    for parent in [cwd] + list(cwd.parents):
        if (parent / ".git").exists() or (parent / "GEMINI.md").exists():
            return parent
    raise RuntimeError("Cannot detect repo root")


def compute_sha256(filepath: Path) -> str:
    """Compute full SHA-256 hash of file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def run_command(cmd: List[str], cwd: Path) -> Tuple[int, str, str]:
    """Run command and capture output."""
    result = subprocess.run(
        cmd, capture_output=True, text=True, cwd=cwd
    )
    return result.returncode, result.stdout, result.stderr


def check_git_status(repo_root: Path) -> str:
    """Capture git status --porcelain."""
    code, stdout, _ = run_command(["git", "status", "--porcelain"], repo_root)
    if code != 0:
        return f"ERROR: git status failed (exit code {code})"
    return stdout.strip()


def on_rm_error(func, path, exc_info):
    """Handle read-only files on Windows during rmtree."""
    import stat
    try:
        os.chmod(path, stat.S_IWUSR)
        func(path)
    except Exception:
        pass

def setup_scratch_workspace(source_repo: Path) -> Path:
    """Create a scratch workspace by copying source and initializing git."""
    tmp_parent = Path(tempfile.mkdtemp(prefix="mse_scratch_"))
    
    # Copy current repo (excluding common large/system dirs)
    def ignore_patterns(path, names):
        ignore = {".git", "__pycache__", ".pytest_cache", ".venv", "venv", ".env", "node_modules", ".idea", ".vscode"}
        return [n for n in names if n in ignore]
        
    try:
        shutil.copytree(source_repo, tmp_parent, ignore=ignore_patterns, dirs_exist_ok=True)
    except Exception as e:
        # If copy fails, cleanup and re-raise
        shutil.rmtree(tmp_parent, onerror=on_rm_error)
        raise e
    
    # Initialize git to provide clean baseline for audit
    run_command(["git", "init"], tmp_parent)
    run_command(["git", "add", "."], tmp_parent)
    run_command(["git", "commit", "-m", "Baseline for MSE E2E Audit"], tmp_parent)
    
    return tmp_parent


def run_verification(repo_root: Path, live_mode: bool = False, scratch_mode: bool = False) -> Dict[str, Any]:
    """
    Run all verification gates.
    """
    report = {
        "environment": {
            "repo_root": str(repo_root),
            "python_version": sys.version.split()[0],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "live_mode": live_mode,
            "scratch_mode": scratch_mode,
        },
        "preconditions": [],
        "steps": [],
        "results": {"passed": 0, "failed": 0, "skipped": 0},
        "artifacts": [],
        "hashes": {},
        "notes": [],
    }
    
    # Precondition: Check backlog file exists
    backlog_path = repo_root / "config" / "backlog.yaml"
    if backlog_path.exists():
        report["preconditions"].append({
            "name": "backlog_file_exists",
            "status": "PASS",
            "path": str(backlog_path.relative_to(repo_root)),
        })
    else:
        report["preconditions"].append({
            "name": "backlog_file_exists",
            "status": "FAIL",
            "path": str(backlog_path.relative_to(repo_root)),
        })
        
    # Gate 1: Dependency Check (P0.3)
    try:
        import yaml
        report["steps"].append({
            "name": "dependency_check_pyyaml",
            "command": "import yaml",
            "exit_code": 0,
            "stdout_excerpt": f"PyYAML version: {yaml.__version__}",
            "status": "PASS",
        })
        report["results"]["passed"] += 1
        
        req_path = repo_root / "requirements.txt"
        if req_path.exists():
             req_content = req_path.read_text()
             if "pyyaml" in req_content.lower():
                 report["notes"].append("PyYAML confirmed in requirements.txt (repo-approved).")
             else:
                 report["notes"].append("WARNING: PyYAML installed but NOT in requirements.txt")
                 
    except ImportError:
        report["steps"].append({
            "name": "dependency_check_pyyaml",
            "command": "import yaml",
            "exit_code": 1,
            "stdout_excerpt": "ImportError: No module named yaml",
            "status": "FAIL",
        })
        report["results"]["failed"] += 1

    # Gate 2: Backlog parser tests
    gate2_cmd = [
        sys.executable, "-m", "pytest",
        "runtime/tests/test_backlog_parser.py",
        "-v", "--tb=short"
    ]
    code, stdout, stderr = run_command(gate2_cmd, repo_root)
    report["steps"].append({
        "name": "backlog_parser_tests",
        "command": " ".join(gate2_cmd),
        "exit_code": code,
        "stdout_excerpt": stdout[-2000:] if len(stdout) > 2000 else stdout,
        "stderr_excerpt": stderr[-1000:] if len(stderr) > 1000 else stderr,
        "status": "PASS" if code == 0 else "FAIL",
    })
    if code == 0:
        report["results"]["passed"] += 1
    else:
        report["results"]["failed"] += 1
    
    # Gate 3: Context resolver tests
    gate3_cmd = [
        sys.executable, "-m", "pytest",
        "runtime/tests/test_context_resolver.py",
        "-v", "--tb=short"
    ]
    code, stdout, stderr = run_command(gate3_cmd, repo_root)
    report["steps"].append({
        "name": "context_resolver_tests",
        "command": " ".join(gate3_cmd),
        "exit_code": code,
        "stdout_excerpt": stdout[-2000:] if len(stdout) > 2000 else stdout,
        "stderr_excerpt": stderr[-1000:] if len(stderr) > 1000 else stderr,
        "status": "PASS" if code == 0 else "FAIL",
    })
    if code == 0:
        report["results"]["passed"] += 1
    else:
        report["results"]["failed"] += 1
    
    # Gate 4: Synthesizer tests
    gate4_cmd = [
        sys.executable, "-m", "pytest",
        "runtime/tests/test_backlog_synthesizer.py",
        "-v", "--tb=short"
    ]
    code, stdout, stderr = run_command(gate4_cmd, repo_root)
    report["steps"].append({
        "name": "backlog_synthesizer_tests",
        "command": " ".join(gate4_cmd),
        "exit_code": code,
        "stdout_excerpt": stdout[-2000:] if len(stdout) > 2000 else stdout,
        "stderr_excerpt": stderr[-1000:] if len(stderr) > 1000 else stderr,
        "status": "PASS" if code == 0 else "FAIL",
    })
    if code == 0:
        report["results"]["passed"] += 1
    else:
        report["results"]["failed"] += 1
        
    # Gate 5: E2E Smoke Test (Echo Semantics)
    # Using 'echo' mission type to prove offline completion
    e2e_cmd = [
        sys.executable, "-m", "runtime", "run-mission",
        "--from-backlog", "MSE-MVP-E2E-001",
        "--mission-type", "echo"
    ]
    
    e2e_repo = repo_root
    scratch_dir = None
    if scratch_mode:
        report["notes"].append("Executing E2E in isolated scratch workspace.")
        scratch_dir = setup_scratch_workspace(repo_root)
        e2e_repo = scratch_dir
    
    # Capture PRE-EXECUTION git status
    git_pre = check_git_status(e2e_repo)
    
    # Run E2E
    code, stdout, stderr = run_command(e2e_cmd, e2e_repo)
    
    # Capture POST-EXECUTION git status
    git_post = check_git_status(e2e_repo)
    
    # Wiring Check: Did CLI invoke orchestrator?
    wiring_proven = "Step 2: Executing mission via orchestrator" in stdout
    
    # Completion Check: Did it exit 0 AND return Status: SUCCESS?
    completion_proven = (code == 0) and ("Status: SUCCESS" in stdout)
    
    # Clean workspace check
    clean_pre = not git_pre
    clean_post = git_post == git_pre # Echo should change nothing
    
    # Gating Logic: Overall PASS only if ALL sub-checks pass
    e2e_status = "PASS" if (wiring_proven and completion_proven and clean_pre and clean_post) else "FAIL"
    
    report["steps"].append({
        "name": "e2e_smoke_gate",
        "command": " ".join(e2e_cmd),
        "exit_code": code,
        "status": e2e_status,
        "checks": {
            "wiring_check": "PASS" if wiring_proven else "FAIL",
            "completion_check": "PASS" if completion_proven else "FAIL",
            "clean_workspace_pre": "PASS" if clean_pre else "FAIL",
            "clean_workspace_post": "PASS" if clean_post else "FAIL"
        },
        "evidence": {
            "git_status_pre": git_pre[:1000] + ("..." if len(git_pre) > 1000 else "") if git_pre else "(clean)",
            "git_status_post": git_post[:1000] + ("..." if len(git_post) > 1000 else "") if git_post else "(clean)",
            "stdout_excerpt": stdout[-3000:] if len(stdout) > 3000 else stdout,
            "stderr_excerpt": stderr[-1000:] if len(stderr) > 1000 else stderr,
        }
    })
    
    if e2e_status == "PASS":
        report["results"]["passed"] += 1
    else:
        report["results"]["failed"] += 1
    
    # Cleanup scratch
    if scratch_dir and scratch_dir.exists():
        shutil.rmtree(scratch_dir, onerror=on_rm_error)
    
    # Gate 6: Live connectivity (only if live_mode)
    if live_mode:
        gate6_cmd = [
            sys.executable, "scripts/verify_opencode_connectivity.py"
        ]
        code, stdout, stderr = run_command(gate6_cmd, repo_root)
        report["steps"].append({
            "name": "live_connectivity_check",
            "command": " ".join(gate6_cmd),
            "exit_code": code,
            "stdout_excerpt": stdout[-2000:] if len(stdout) > 2000 else stdout,
            "stderr_excerpt": stderr[-1000:] if len(stderr) > 1000 else stderr,
            "status": "PASS" if code == 0 else "FAIL",
        })
        if code == 0:
            report["results"]["passed"] += 1
        else:
            report["results"]["failed"] += 1
    else:
        report["steps"].append({
            "name": "live_connectivity_check",
            "command": "SKIPPED (not live_mode)",
            "exit_code": None,
            "status": "SKIPPED",
        })
        report["results"]["skipped"] += 1
    
    # Final verdict: All steps must be PASS or SKIPPED
    if report["results"]["failed"] > 0:
        report["verdict"] = "FAIL"
    else:
        report["verdict"] = "PASS"
    
    return report


def write_report(report: Dict[str, Any], report_path: Path) -> None:
    """Write markdown report."""
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Mission Synthesis Engine MVP Verification Report\n\n")
        f.write(f"**Verdict:** {report['verdict']}\n")
        f.write(f"**Timestamp:** {report['environment']['timestamp']}\n")
        f.write(f"**Python:** {report['environment']['python_version']}\n")
        f.write(f"**Live Mode:** {report['environment']['live_mode']}\n")
        f.write(f"**Scratch Mode:** {report['environment']['scratch_mode']}\n\n")
        
        if report["notes"]:
            f.write("## Notes\n\n")
            for note in report["notes"]:
                f.write(f"- {note}\n")
            f.write("\n")
        
        f.write("## Results Summary\n\n")
        f.write(f"- **Passed:** {report['results']['passed']}\n")
        f.write(f"- **Failed:** {report['results']['failed']}\n")
        f.write(f"- **Skipped:** {report['results']['skipped']}\n\n")
        
        f.write("## Preconditions\n\n")
        for pre in report["preconditions"]:
            f.write(f"- **{pre['name']}:** {pre['status']}")
            if pre.get("path"):
                f.write(f" (`{pre['path']}`)")
            f.write("\n")
        f.write("\n")
        
        f.write("## Verification Steps\n\n")
        for step in report["steps"]:
            status_emoji = "✅" if step["status"] == "PASS" else ("⏭️" if step["status"] == "SKIPPED" else "❌")
            f.write(f"### {status_emoji} {step['name']}\n\n")
            f.write(f"- **Command:** `{step['command']}`\n")
            if step.get("exit_code") is not None:
                f.write(f"- **Exit Code:** {step['exit_code']}\n")
            f.write(f"- **Status:** {step['status']}\n\n")
            
            if step.get("checks"):
                f.write("**Detailed Checks:**\n")
                for k, v in step["checks"].items():
                    check_emoji = "✅" if v == "PASS" else "❌"
                    f.write(f"- {check_emoji} {k}: {v}\n")
                f.write("\n")
            
            if step.get("evidence"):
                f.write("**Evidence:**\n")
                for key, val in step["evidence"].items():
                    if isinstance(val, str) and ("\n" in val or len(val) > 80):
                         f.write(f"- {key}:\n```\n{val}\n```\n")
                    else:
                         f.write(f"- {key}: {val}\n")
                f.write("\n")
            
            if step.get("stdout_excerpt"):
                f.write("**Output:**\n```\n")
                f.write(step["stdout_excerpt"].strip())
                f.write("\n```\n\n")
        
        f.write("## Artifacts\n\n")
        f.write(f"- Report: `{report_path.name}`\n")
        if report.get("hashes"):
            f.write("\n## Hashes\n\n")
            for name, hash_val in sorted(report["hashes"].items()):
                f.write(f"- `{name}`: `{hash_val}`\n")


def main() -> int:
    repo_root = detect_repo_root()
    live_mode = "--live" in sys.argv
    scratch_mode = "--scratch" in sys.argv
    
    print(f"Mission Synthesis Engine MVP Verification")
    print(f"==========================================")
    print(f"Repo root: {repo_root}")
    print(f"Live mode: {live_mode}")
    print(f"Scratch mode: {scratch_mode}")
    print()
    
    report = run_verification(repo_root, live_mode, scratch_mode)
    
    # Write report
    report_path = repo_root / "artifacts" / "REPORT_MISSION_SYNTHESIS_MVP.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    
    write_report(report, report_path)
    
    # Compute hash of report
    report_hash = compute_sha256(report_path)
    report["hashes"]["REPORT_MISSION_SYNTHESIS_MVP.md"] = report_hash
    
    # Rewrite with hash
    write_report(report, report_path)
    
    print(f"Report: {report_path}")
    print(f"SHA256: {report_hash}")
    print(f"Verdict: {report['verdict']}")
    print()
    
    # Print step summary
    for step in report["steps"]:
        status = "✅" if step["status"] == "PASS" else ("⏭️" if step["status"] == "SKIPPED" else "❌")
        print(f"  {status} {step['name']}: {step['status']}")
    
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
