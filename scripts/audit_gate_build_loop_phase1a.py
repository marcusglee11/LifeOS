#!/usr/bin/env python3
"""
Audit Gate for Build Loop Phase 1a Bundle.

Deterministic, fail-closed validation of the Phase 1a bundle ZIP.
Exit codes:
  0 = PASS (all gates passed)
  2 = FAIL (gate violation)
  3 = BLOCKED (environment/tooling missing)

Usage:
  python scripts/audit_gate_build_loop_phase1a.py --zip PATH [--extract-dir PATH] [--pytest-args ARGS]
"""

import argparse
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

# Exit codes
EXIT_PASS = 0
EXIT_FAIL = 2
EXIT_BLOCKED = 3


class AuditGate:
    """Deterministic audit gate for Phase 1a bundle."""
    
    def __init__(self, zip_path: str, extract_dir: str = None, pytest_args: str = "-q"):
        self.zip_path = Path(zip_path)
        self.extract_dir = Path(extract_dir) if extract_dir else None
        self.pytest_args = pytest_args
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
        print("AUDIT GATE: Build Loop Phase 1a Bundle")
        print(f"{'='*60}")
        print(f"ZIP: {self.zip_path}")
        print()
        
        # Pre-check: ZIP exists
        if not self.zip_path.exists():
            print(f"BLOCKED: ZIP file not found: {self.zip_path}")
            return EXIT_BLOCKED
        
        # Setup extraction directory
        if self.extract_dir:
            self.temp_dir = self.extract_dir
            self.temp_dir.mkdir(parents=True, exist_ok=True)
        else:
            self.temp_dir = Path(tempfile.mkdtemp(prefix="audit_gate_"))
        
        print(f"Extract dir: {self.temp_dir}")
        print()
        print("Gate Checks:")
        
        try:
            # G1: ZIP integrity
            self._gate_g1_zip_integrity()
            
            # G2: ZIP portability
            self._gate_g2_zip_portability()
            
            # G3: ZIP hygiene
            self._gate_g3_zip_hygiene()
            
            # G4: Plan conformance
            self._gate_g4_plan_conformance()
            
            # G5: Python import sanity
            self._gate_g5_import_sanity()
            
            # G6: Pytest execution
            self._gate_g6_pytest()
            
            # G7: Package import completeness
            self._gate_g7_import_completeness()
            
        finally:
            # Cleanup temp dir if we created it
            if not self.extract_dir and self.temp_dir:
                import shutil
                try:
                    shutil.rmtree(self.temp_dir)
                except Exception:
                    pass
        
        # Summary
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
                        issues.append(f"Absolute path (starts with /): {name}")
                    if len(name) > 1 and name[1] == ":":
                        issues.append(f"Drive letter in path: {name}")
            
            if issues:
                self.log("G2 ZIP Portability", "FAIL", "\n".join(issues))
            else:
                self.log("G2 ZIP Portability", "PASS")
        except Exception as e:
            self.log("G2 ZIP Portability", "BLOCKED", f"Exception: {e}")
    
    def _gate_g3_zip_hygiene(self):
        """G3: ZIP hygiene (no pycache, no OS junk)."""
        issues = []
        forbidden_patterns = [
            "__pycache__/",
            ".pyc",
            ".pyo",
            "Thumbs.db",
            ".DS_Store",
        ]
        try:
            with zipfile.ZipFile(self.zip_path, 'r') as zf:
                for info in zf.infolist():
                    name = info.filename
                    for pattern in forbidden_patterns:
                        if pattern in name:
                            issues.append(f"Forbidden pattern '{pattern}' in: {name}")
                            break
            
            if issues:
                self.log("G3 ZIP Hygiene", "FAIL", "\n".join(issues))
            else:
                self.log("G3 ZIP Hygiene", "PASS")
        except Exception as e:
            self.log("G3 ZIP Hygiene", "BLOCKED", f"Exception: {e}")
    
    def _gate_g4_plan_conformance(self):
        """G4: Plan conformance (no file:// links, no move instructions)."""
        # First extract
        try:
            with zipfile.ZipFile(self.zip_path, 'r') as zf:
                zf.extractall(self.temp_dir)
        except Exception as e:
            self.log("G4 Plan Conformance", "BLOCKED", f"Extraction failed: {e}")
            return
        
        # Find implementation_plan.md
        plan_paths = list(self.temp_dir.rglob("implementation_plan.md"))
        if not plan_paths:
            # Not a critical failure - plan may not be in bundle
            self.log("G4 Plan Conformance", "PASS", "No implementation_plan.md in bundle (OK)")
            return
        
        issues = []
        for plan_path in plan_paths:
            try:
                content = plan_path.read_text(encoding="utf-8")
                lines = content.split("\n")
                
                for i, line in enumerate(lines, 1):
                    if "file:///" in line.lower():
                        issues.append(f"{plan_path.name}:{i}: contains 'file:///'")
                    if "Move from `docs/` root" in line:
                        issues.append(f"{plan_path.name}:{i}: contains 'Move from `docs/` root'")
            except Exception as e:
                issues.append(f"Error reading {plan_path}: {e}")
        
        if issues:
            self.log("G4 Plan Conformance", "FAIL", "\n".join(issues))
        else:
            self.log("G4 Plan Conformance", "PASS")
    
    def _gate_g5_import_sanity(self):
        """G5: Python import sanity from extracted ZIP."""
        try:
            result = subprocess.run(
                [sys.executable, "-c", "import runtime; import runtime.agents"],
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
            args = self.pytest_args.split() if self.pytest_args else ["-q"]
            result = subprocess.run(
                [sys.executable, "-m", "pytest"] + args,
                cwd=self.temp_dir,
                capture_output=True,
                text=True,
                timeout=120,
                env={**os.environ, "PYTHONPATH": str(self.temp_dir)},
            )
            if result.returncode == 0:
                self.log("G6 Pytest", "PASS", f"stdout:\n{result.stdout}")
            else:
                self.log("G6 Pytest", "FAIL", f"returncode={result.returncode}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}")
        except subprocess.TimeoutExpired:
            self.log("G6 Pytest", "BLOCKED", "Pytest timed out")
        except Exception as e:
            self.log("G6 Pytest", "BLOCKED", f"Exception: {e}")
    
    def _gate_g7_import_completeness(self):
        """G7: Check __init__.py doesn't import missing modules."""
        init_path = self.temp_dir / "runtime" / "agents" / "__init__.py"
        if not init_path.exists():
            self.log("G7 Import Completeness", "PASS", "No runtime/agents/__init__.py")
            return
        
        try:
            content = init_path.read_text(encoding="utf-8")
            
            # Simple regex for "from .X import" or "import runtime.agents.X"
            local_imports = re.findall(r'from\s+\.(\w+)\s+import', content)
            full_imports = re.findall(r'import\s+runtime\.agents\.(\w+)', content)
            
            all_imports = set(local_imports + full_imports)
            agents_dir = self.temp_dir / "runtime" / "agents"
            
            missing = []
            for mod in all_imports:
                mod_path = agents_dir / f"{mod}.py"
                if not mod_path.exists():
                    missing.append(mod)
            
            if missing:
                self.log("G7 Import Completeness", "FAIL", f"Missing modules: {', '.join(sorted(missing))}")
            else:
                self.log("G7 Import Completeness", "PASS", f"All {len(all_imports)} imported modules present")
        except Exception as e:
            self.log("G7 Import Completeness", "BLOCKED", f"Exception: {e}")


def main():
    parser = argparse.ArgumentParser(description="Audit Gate for Build Loop Phase 1a Bundle")
    parser.add_argument("--zip", required=True, help="Path to bundle ZIP")
    parser.add_argument("--extract-dir", help="Extraction directory (default: temp)")
    parser.add_argument("--pytest-args", default="-q", help="Pytest arguments (default: -q)")
    args = parser.parse_args()
    
    gate = AuditGate(args.zip, args.extract_dir, args.pytest_args)
    exit_code = gate.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
