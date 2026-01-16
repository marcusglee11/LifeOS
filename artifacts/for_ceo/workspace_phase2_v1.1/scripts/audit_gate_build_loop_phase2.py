#!/usr/bin/env python3
"""
Audit Gate for Build Loop Phase 2 Bundle.

Deterministic, fail-closed validation of Phase 2 bundle.
Exit codes:
  0 = PASS (all gates passed)
  2 = FAIL (gate violation)
  3 = BLOCKED (environment/tooling missing)

Usage:
  python scripts/audit_gate_build_loop_phase2.py --zip PATH [--extract-dir PATH]
"""

import argparse
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

EXIT_PASS = 0
EXIT_FAIL = 2
EXIT_BLOCKED = 3


class AuditGate:
    """Deterministic audit gate for Phase 2 bundle."""
    
    def __init__(self, zip_path: str, extract_dir: str = None):
        self.zip_path = Path(zip_path)
        self.extract_dir = Path(extract_dir) if extract_dir else None
        self.temp_dir = None
        self.results = []
        self.all_passed = True
    
    def log(self, gate: str, status: str, details: str = ""):
        """Log a gate result."""
        self.results.append((gate, status, details))
        if status != "PASS":
            self.all_passed = False
        status_emoji = {"PASS": "✓", "FAIL": "✗", "BLOCKED": "⊘"}.get(status, "?")
        print(f"  [{status_emoji}] {gate}: {status}")
        if details:
            for line in details.strip().split("\n"):
                print(f"      {line}")
    
    def run(self) -> int:
        """Run all gate checks. Returns exit code."""
        print(f"\n{'='*60}")
        print("AUDIT GATE: Build Loop Phase 2 Bundle")
        print(f"{'='*60}")
        print(f"ZIP: {self.zip_path}")
        print()
        
        if not self.zip_path.exists():
            print(f"BLOCKED: ZIP file not found: {self.zip_path}")
            return EXIT_BLOCKED
        
        if self.extract_dir:
            self.temp_dir = self.extract_dir
            self.temp_dir.mkdir(parents=True, exist_ok=True)
        else:
            self.temp_dir = Path(tempfile.mkdtemp(prefix="audit_gate_p2_"))
        
        print(f"Extract dir: {self.temp_dir}")
        print()
        print("Gate Checks:")
        
        try:
            self._gate_g1_zip_integrity()
            self._gate_g2_zip_portability()
            self._gate_g3_manifest_format()
            self._gate_g4_manifest_hashes()
            self._gate_g5_import_sanity()
            self._gate_g6_pytest()
        finally:
            if not self.extract_dir and self.temp_dir:
                import shutil
                try:
                    shutil.rmtree(self.temp_dir)
                except Exception:
                    pass
        
        print()
        print(f"{'='*60}")
        passed = sum(1 for _, s, _ in self.results if s == "PASS")
        failed = sum(1 for _, s, _ in self.results if s == "FAIL")
        blocked = sum(1 for _, s, _ in self.results if s == "BLOCKED")
        print(f"SUMMARY: {passed} PASS, {failed} FAIL, {blocked} BLOCKED")
        
        if self.all_passed:
            print("RESULT: PASS")
            return EXIT_PASS
        elif blocked > 0:
            print("RESULT: BLOCKED")
            return EXIT_BLOCKED
        else:
            print("RESULT: FAIL")
            return EXIT_FAIL
    
    def _gate_g1_zip_integrity(self):
        """G1: ZIP integrity check."""
        try:
            with zipfile.ZipFile(self.zip_path, 'r') as zf:
                bad_file = zf.testzip()
                if bad_file is None:
                    self.log("G1 ZIP Integrity", "PASS")
                else:
                    self.log("G1 ZIP Integrity", "FAIL", f"Corrupted file: {bad_file}")
        except Exception as e:
            self.log("G1 ZIP Integrity", "FAIL", f"Exception: {e}")
    
    def _gate_g2_zip_portability(self):
        """G2: ZIP portability (no backslashes, no absolute paths)."""
        issues = []
        try:
            with zipfile.ZipFile(self.zip_path, 'r') as zf:
                for info in zf.infolist():
                    name = info.filename
                    if "\\" in name:
                        issues.append(f"Backslash in path: {name}")
                    if name.startswith("/"):
                        issues.append(f"Absolute path: {name}")
            
            if issues:
                self.log("G2 ZIP Portability", "FAIL", "\n".join(issues))
            else:
                self.log("G2 ZIP Portability", "PASS")
        except Exception as e:
            self.log("G2 ZIP Portability", "BLOCKED", f"Exception: {e}")
    
    def _gate_g3_manifest_format(self):
        """G3: Manifest format validation (P0 requirement)."""
        # Extract first
        try:
            with zipfile.ZipFile(self.zip_path, 'r') as zf:
                zf.extractall(self.temp_dir)
        except Exception as e:
            self.log("G3 Manifest Format", "BLOCKED", f"Extraction failed: {e}")
            return
        
        manifest_path = self.temp_dir / "manifest.txt"
        if not manifest_path.exists():
            self.log("G3 Manifest Format", "FAIL", "manifest.txt not found in bundle")
            return
        
        issues = []
        line_pattern = re.compile(r'^[0-9a-f]{64}  [^\s].*$')
        paths = []
        
        try:
            content = manifest_path.read_text(encoding="utf-8")
            for i, line in enumerate(content.strip().split("\n"), 1):
                if not line.strip():
                    continue
                # Check for ellipsis/truncation
                if "..." in line:
                    issues.append(f"Line {i}: contains truncation ellipsis '...'")
                # Check format: 64-hex + 2 spaces + path
                if not line_pattern.match(line):
                    issues.append(f"Line {i}: invalid format: {line[:80]}")
                else:
                    # Extract path for sort check
                    parts = line.split("  ", 1)
                    if len(parts) == 2:
                        paths.append(parts[1])
            
            # Check paths are sorted (P0 enforcement)
            sorted_paths = sorted(paths)
            if paths != sorted_paths:
                issues.append("Manifest paths are NOT lexicographically sorted")
                for j, (actual, expected) in enumerate(zip(paths, sorted_paths)):
                    if actual != expected:
                        issues.append(f"  First mismatch at line {j+1}: '{actual}' should be '{expected}'")
                        break
            
            if issues:
                self.log("G3 Manifest Format", "FAIL", "\n".join(issues))
            else:
                self.log("G3 Manifest Format", "PASS", f"Valid format, {len(paths)} paths sorted")
        except Exception as e:
            self.log("G3 Manifest Format", "BLOCKED", f"Exception: {e}")
    
    def _gate_g4_manifest_hashes(self):
        """G4: Verify manifest SHA256 hashes match actual files."""
        manifest_path = self.temp_dir / "manifest.txt"
        if not manifest_path.exists():
            self.log("G4 Manifest Hashes", "BLOCKED", "manifest.txt not found")
            return
        
        import hashlib
        issues = []
        verified = 0
        
        try:
            content = manifest_path.read_text(encoding="utf-8")
            for line in content.strip().split("\n"):
                if not line.strip():
                    continue
                parts = line.split("  ", 1)
                if len(parts) != 2:
                    continue
                expected_hash, rel_path = parts
                file_path = self.temp_dir / rel_path
                
                if not file_path.exists():
                    issues.append(f"Missing file: {rel_path}")
                    continue
                
                with open(file_path, "rb") as f:
                    actual_hash = hashlib.sha256(f.read()).hexdigest()
                
                if actual_hash != expected_hash:
                    issues.append(f"Hash mismatch: {rel_path}")
                else:
                    verified += 1
            
            if issues:
                self.log("G4 Manifest Hashes", "FAIL", "\n".join(issues))
            else:
                self.log("G4 Manifest Hashes", "PASS", f"Verified {verified} files")
        except Exception as e:
            self.log("G4 Manifest Hashes", "BLOCKED", f"Exception: {e}")
    
    def _gate_g5_import_sanity(self):
        """G5: Python import sanity from extracted ZIP."""
        try:
            result = subprocess.run(
                [sys.executable, "-c", 
                 "import runtime.orchestration.operations; "
                 "import runtime.orchestration.mission_journal; "
                 "import runtime.governance.envelope_enforcer; "
                 "import runtime.governance.self_mod_protection"],
                cwd=self.temp_dir,
                capture_output=True,
                text=True,
                timeout=30,
                env={**os.environ, "PYTHONPATH": str(self.temp_dir)},
            )
            if result.returncode == 0:
                self.log("G5 Import Sanity", "PASS")
            else:
                self.log("G5 Import Sanity", "FAIL", f"stderr:\n{result.stderr}")
        except subprocess.TimeoutExpired:
            self.log("G5 Import Sanity", "BLOCKED", "Import timed out")
        except Exception as e:
            self.log("G5 Import Sanity", "BLOCKED", f"Exception: {e}")
    
    def _gate_g6_pytest(self):
        """G6: Pytest execution from extracted ZIP."""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "-q"],
                cwd=self.temp_dir,
                capture_output=True,
                text=True,
                timeout=120,
                env={**os.environ, "PYTHONPATH": str(self.temp_dir)},
            )
            if result.returncode == 0:
                self.log("G6 Pytest", "PASS", f"stdout:\n{result.stdout}")
            else:
                self.log("G6 Pytest", "FAIL", 
                         f"returncode={result.returncode}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}")
        except subprocess.TimeoutExpired:
            self.log("G6 Pytest", "BLOCKED", "Pytest timed out")
        except Exception as e:
            self.log("G6 Pytest", "BLOCKED", f"Exception: {e}")


def main():
    parser = argparse.ArgumentParser(description="Audit Gate for Build Loop Phase 2 Bundle")
    parser.add_argument("--zip", required=True, help="Path to bundle ZIP")
    parser.add_argument("--extract-dir", help="Extraction directory (default: temp)")
    args = parser.parse_args()
    
    gate = AuditGate(args.zip, args.extract_dir)
    exit_code = gate.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
