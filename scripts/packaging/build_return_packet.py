#!/usr/bin/env python3
"""
Return-Packet Builder (RPPV v2.6a Compliant)

Features:
- Generates 07_git_diff.patch (Option A: working tree invariant)
- Prepares Primary Narrative File with Sentinel
- Generates 00_manifest.json and 08_evidence_manifest.sha256
- Validates packet using validate_return_packet_preflight.py
- Zips compliant packet

Usage:
    python -m scripts.packaging.build_return_packet \
        --repo-root . \
        --output-dir artifacts/return_packets
"""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Optional, List

# Configuration
NARRATIVE_PRECEDENCE = ["FIX_RETURN.md", "README.md", "RESULT.md"]
SENTINEL = "__EOF_SENTINEL__"
REQUIRED_FILES = ["00_manifest.json", "07_git_diff.patch", "08_evidence_manifest.sha256"]

def run_command(cmd: List[str], cwd: Path, capture_output: bool = True, text: bool = True) -> subprocess.CompletedProcess:
    """Run a shell command."""
    return subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=capture_output,
        text=text,
        check=False
    )

def load_allowlist(repo_root: Path) -> List[str]:
    """Load allowlist paths from YAML."""
    # Simple parse to avoid PyYAML dep if not installed (though it should be)
    # Reusing logic from validator would be better, but we want independence or CLI usage.
    # We will assume PyYAML is available as this is dev env.
    import yaml
    p = repo_root / "config" / "packaging" / "preflight_allowlist.yaml"
    if not p.exists():
        print(f"Warning: Allowlist not found at {p}")
        return []
    with open(p, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("allowlist", [])

def generate_patch(repo_root: Path, output_path: Path) -> bool:
    """Generate git diff patch (Option A)."""
    allowlist = load_allowlist(repo_root)
    if not allowlist:
        print("Error: Empty allowlist, cannot generate patch")
        return False
    
    cmd = ["git", "diff", "--no-color", "--"] + allowlist
    res = run_command(cmd, repo_root, text=False)
    
    if res.returncode != 0:
        print(f"Error generating patch: {res.stderr.decode('utf-8', errors='replace')}")
        return False
    
    # Normalize to LF (bytes)
    content = res.stdout.replace(b"\r\n", b"\n")
    if not content.strip():
        print("Error: Generated patch is empty")
        return False
        
    output_path.write_bytes(content)
    return True

def prepare_narrative(repo_root: Path, output_dir: Path) -> Optional[Path]:
    """Find and prepare primary narrative file."""
    source_file = None
    for fname in NARRATIVE_PRECEDENCE:
        f = repo_root / fname
        if f.exists():
            source_file = f
            break
    
    if not source_file:
        print("Error: No primary narrative file found (FIX_RETURN.md, README.md, RESULT.md)")
        return None
    
    dest = output_dir / source_file.name
    content = source_file.read_text(encoding="utf-8")
    
    # Check sentinel
    lines = content.strip().split("\n")
    last_line = lines[-1].strip() if lines else ""
    
    if last_line != SENTINEL:
        # Append sentinel
        if content and not content.endswith("\n"):
            content += "\n"
        content += f"\n{SENTINEL}\n"
    
    dest.write_text(content, encoding="utf-8", newline="\n")
    return dest

def generate_manifest(output_dir: Path):
    """Generate 00_manifest.json."""
    manifest = {
        "builder": "build_return_packet.py",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "schema_version": "2.6a"
    }
    (output_dir / "00_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )

def generate_evidence_manifest(output_dir: Path):
    """Generate 08_evidence_manifest.sha256."""
    lines = []
    for f in output_dir.iterdir():
        if f.name == "08_evidence_manifest.sha256":
            continue
        if f.is_file():
            # Hash
            h = hashlib.sha256(f.read_bytes()).hexdigest()
            lines.append(f"{h} *{f.name}")
    
    (output_dir / "08_evidence_manifest.sha256").write_text(
        "\n".join(sorted(lines)), encoding="utf-8"
    )

def main():
    parser = argparse.ArgumentParser(description="Build Return Packet (RPPV v2.6a)")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd(), help="Repository root")
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/return_packets"), help="Output directory for zip")
    parser.add_argument("--keep-stage", action="store_true", help="Keep staging directory")
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    # create staging area
    # Ideally RPPV-001 says stage outside repo.
    # We use tempfile which is usually outside.
    with tempfile.TemporaryDirectory(prefix="rppv_build_") as tmp_dir:
        stage_root = Path(tmp_dir)
        packet_name = f"return_packet_{int(time.time())}"
        packet_dir = stage_root / packet_name
        packet_dir.mkdir()
        
        print(f"Building in {packet_dir}...")
        
        # 1. Narrative
        narrative_path = prepare_narrative(repo_root, packet_dir)
        if not narrative_path:
            return 1
            
        # 2. Patch
        if not generate_patch(repo_root, packet_dir / "07_git_diff.patch"):
            return 1
            
        # 3. Manifests
        generate_manifest(packet_dir)
        generate_evidence_manifest(packet_dir)
        
        # 4. Copy optionals if present (01, 02, 03, 04, review_packet)
        # For simple builder, we might skip collecting these unless instructed.
        # But 'review_packet.json' is useful if present.
        rv_pkt = repo_root / "review_packet.json"
        if rv_pkt.exists():
            shutil.copy(rv_pkt, packet_dir / "review_packet.json")
            
        # 5. Validate
        print("Running Preflight Validation...")
        # python -m scripts.packaging.validate_return_packet_preflight ...
        # Construct CLI args
        # RPPV-001 requires stage-dir outside repo. Temp dir usually is.
        # We need to pass --repo-root etc.
        # We will create a dummy zip path arg because validator might require it for RPPV-005 check context?
        # RPPV-005 checks zip content. Validator runs ON FILES or ZIP?
        # CLI help: "python ... --packet-dir ... --stage-dir ... --zip-path ... --mode auto"
        # The validator separates "stage validation" from "zip validation"?
        # Actually RPPV-005 checks the Zip file.
        # But we haven't zipped yet.
        # Can we validate the folder BEFORE zipping?
        # RPPV-001..004, 006..014 are checking the stage/packet dir.
        # RPPV-005 checks the final zip.
        
        # We should validate the FOLDER first (excluding RPPV-005).
        # But the validator is monolithic?
        # Let's try running it. If RPPV-005 fails (missing zip), that's fine, we zip later?
        # Wait, "Wiring: build_return_packet.py MUST run validator before finalizing... If fail/block, build MUST stop".
        # So we validate the FOLDER content.
        # The validator CLI takes --zip-path. If it points to non-existent, RPPV-005 FAIL/SKIP?
        # Validator code: check_rppv_005: "if not zip_path ... exists ... return SKIP".
        # So it SKIPS zip check if zip missing. Good.
        
        val_cmd = [
            sys.executable, "-m", "scripts.packaging.validate_return_packet_preflight",
            "--repo-root", str(repo_root),
            "--packet-dir", str(packet_dir),
            "--stage-dir", str(stage_root),
            "--mode", "auto",
            "--json"
        ]
        
        res = run_command(val_cmd, repo_root)
        
        if res.returncode != 0:
            print("Validation process failed to run:")
            print("STDOUT:", res.stdout)
            print("STDERR:", res.stderr)
            return 1
            
        # Parse output
        try:
            report = json.loads(res.stdout)
        except:
            print(f"Validation output malformed: {res.stdout[:200]}")
            return 1
            
        outcome = report.get("outcome")
        print(f"Validation Outcome: {outcome}")
        
        if outcome != "PASS":
            print("Validation FAILED. See report:")
            print(json.dumps(report, indent=2))
            return 1
            
        # 6. Zip
        zip_path = output_dir / f"{packet_name}.zip"
        print(f"Zipping to {zip_path}...")
        
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in packet_dir.rglob("*"):
                if f.is_file():
                    zf.write(f, arcname=f.relative_to(stage_root)) # packet_name/filename
                    
        # 6a. Hard Gate: RPPV Exit-Blocker Zip Validation
        print("RPPV_EXIT_BLOCKER_ZIP_GATE: Validating zip...")
        if run_zip_gate(zip_path, repo_root, packet_dir) != 0:
            return 1

        print("RPPV_EXIT_BLOCKER_ZIP_GATE: PASS")
                    
        # 7. Validate Zip (RPPV-005 check final pass)
        # We verify the zip now exists.
        val_cmd.extend(["--zip-path", str(zip_path)])
        res = run_command(val_cmd, repo_root)
        report = json.loads(res.stdout)
        
        if report.get("outcome") != "PASS":
            print("Final Zip Validation FAILED.")
            print(json.dumps(report, indent=2))
            return 1
            
        print(f"Success! Packet built: {zip_path}")
        return 0

def run_zip_gate(zip_path: Path, repo_root: Path, packet_dir: Path) -> int:
    """
    RPPV Zip Hard Gate.
    Returns 0 on PASS, 1 on FAIL.
    Writes BLOCKED.md on failure.
    """
    rppv_cmd = [
        sys.executable, "-m", "scripts.packaging.validate_return_packet_preflight",
        "--repo-root", str(repo_root),
        "--packet-dir", str(packet_dir),
        "--stage-dir", str(packet_dir.parent / "stage"), # inferred staging
        "--zip-path", str(zip_path),
        "--mode", "auto",
        "--json"
    ]
    rppv_result = run_command(rppv_cmd, repo_root)

    if rppv_result.returncode != 0:
        # Gate FAIL: Emit BLOCKED.md and abort
        blocked_content = f"""# BLOCKED: RPPV Exit-Blocker Zip Gate FAIL

## Command Invoked
```
{' '.join(rppv_cmd)}
```

## RPPV Output (JSON)
```json
{rppv_result.stdout}
```

## RPPV Stderr
```
{rppv_result.stderr}
```

## Exit Code
{rppv_result.returncode}
"""
        blocked_path = packet_dir / "BLOCKED.md"
        blocked_path.write_text(blocked_content, encoding="utf-8")
        
        # Also write beside zip
        blocked_zip_path = zip_path.with_suffix(".zip.BLOCKED.md")
        blocked_zip_path.write_text(blocked_content, encoding="utf-8")
        
        print("RPPV_EXIT_BLOCKER_ZIP_GATE: FAIL")
        print(f"BLOCKED.md written to: {blocked_path}")
        print(f"BLOCKED.md written to: {blocked_zip_path}")
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())
