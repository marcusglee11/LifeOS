#!/usr/bin/env python3
"""
Doc Verifier (v2)
=================

Semantic validation for doc stewardship results.
Checks INDEX hygiene, link integrity, and can verify proposed changes
against a simulated post-change state.

Usage:
    from verifiers.doc_verifier import DocVerifier
    verifier = DocVerifier()
    outcome = verifier.verify(result)
    outcome = verifier.verify_with_proposed_changes(files_modified, diffs)
"""

import os
import re
import tempfile
import shutil
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
import subprocess


@dataclass
class Finding:
    """A verification finding."""
    severity: str  # ERROR | WARNING | INFO
    category: str  # INDEX_HYGIENE | LINK_INTEGRITY | TIMESTAMP | DIFF_VALIDATION
    message: str
    location: str = ""


@dataclass
class VerifierOutcome:
    """Outcome from verification."""
    passed: bool
    findings: List[Finding] = field(default_factory=list)
    summary: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def error_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "ERROR")
    
    @property
    def warning_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "WARNING")


class DocVerifier:
    """Semantic verifier for doc stewardship with proposed changes support."""
    
    def __init__(self, docs_dir: Path = None):
        self.docs_dir = Path(docs_dir) if docs_dir else Path(__file__).parent.parent.parent / "docs"
    
    def verify(self, result=None) -> VerifierOutcome:
        """Run all verification checks on current state."""
        findings = []
        
        # Run all checks
        findings.extend(self.check_index_hygiene())
        findings.extend(self.check_timestamp_freshness())
        findings.extend(self.check_root_cleanliness())
        
        # Determine pass/fail
        error_count = sum(1 for f in findings if f.severity == "ERROR")
        warning_count = sum(1 for f in findings if f.severity == "WARNING")
        
        passed = error_count == 0
        summary = f"{error_count} errors, {warning_count} warnings"
        
        return VerifierOutcome(
            passed=passed,
            findings=findings,
            summary=summary,
            details={"error_count": error_count, "warning_count": warning_count}
        )
    
    def verify_with_proposed_changes(self, files_modified: List[Dict], 
                                      proposed_diffs: str) -> VerifierOutcome:
        """
        Verify proposed changes by applying them to a temp workspace.
        This validates the POST-change state, not current state.
        Returns outcome and populates after_sha256 in files_modified if successful.
        """
        findings = []
        
        # Validate we have something to verify
        if not files_modified and not proposed_diffs:
            findings.append(Finding("WARNING", "DIFF_VALIDATION", "No changes proposed to verify"))
            return VerifierOutcome(True, findings, "No changes proposed", {"proposed_files": 0})
        
        # Validate diff format
        if proposed_diffs:
            diff_findings = self._validate_diff_format(proposed_diffs)
            findings.extend(diff_findings)
            # Fail fast if diff is invalid (P0 requirement)
            if any(f.severity == "ERROR" for f in diff_findings):
                return VerifierOutcome(False, findings, "Invalid diff format", {"error_count": 1})
        
        # Validate proposed file paths are allowed
        path_findings = self._validate_proposed_paths(files_modified)
        findings.extend(path_findings)
        
        # Create temp workspace and apply patch
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                temp_docs = temp_path / "docs"
                temp_docs.mkdir()
                
                # Copy current files to temp
                for fm in files_modified:
                    path = fm.get("path")
                    if path and (self.docs_dir.parent / path).exists():
                        src = self.docs_dir.parent / path
                        dst = temp_path / path
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src, dst)
                
                # Apply patch
                patch_file = temp_path / "changes.patch"
                patch_file.write_text(proposed_diffs, encoding="utf-8")
                
                # Attempt git apply with robustness flags
                # --recount: Fix incorrect line counts in hunk headers (common LLM error)
                # --ignore-space-change: Ignore whitespace differences in context
                # --verbose: Get more detail on failure
                cmd = ["git", "apply", "--recount", "--ignore-space-change", "--verbose", str(patch_file)]
                res = subprocess.run(cmd, cwd=str(temp_path), capture_output=True, text=True)
                
                if res.returncode != 0:
                    findings.append(Finding(
                        severity="ERROR",
                        category="PATCH_APPLICATION",
                        message=f"Git apply failed: {res.stderr}",
                        location="proposed_diffs"
                    ))
                else:
                    findings.append(Finding("INFO", "PATCH_APPLICATION", "Patch applied successfully"))
                    
                    # Compute after_sha256 for modified files
                    for fm in files_modified:
                        path = fm.get("path")
                        target = temp_path / path
                        if target.exists():
                            import hashlib
                            sha = hashlib.sha256(target.read_bytes()).hexdigest()
                            fm["after_sha256"] = sha
                    
                    # Run verification on temp state
                    # Create a new verifier pointing to temp docs
                    # Note: we need to handle if docs root is different in temp
                    temp_verifier = DocVerifier(docs_dir=temp_docs)
                    
                    # Run checks on temp verifier
                    hygiene_findings = temp_verifier.check_index_hygiene()
                    # Re-map findings locations from temp to original
                    for f in hygiene_findings:
                        f.location = f.location.replace(str(temp_docs), str(self.docs_dir))
                    
                    findings.extend(hygiene_findings)

        except Exception as e:
            findings.append(Finding("ERROR", "VERIFICATION_SYSTEM", f"Verifier exception: {e}"))
        
        # Determine pass/fail
        error_count = sum(1 for f in findings if f.severity == "ERROR")
        warning_count = sum(1 for f in findings if f.severity == "WARNING")
        
        passed = error_count == 0
        summary = f"{error_count} errors, {warning_count} warnings (post-change verified)"
        
        return VerifierOutcome(
            passed=passed,
            findings=findings,
            summary=summary,
            details={
                "error_count": error_count,
                "warning_count": warning_count,
                "proposed_files": len(files_modified)
            }
        )
    
    def check_index_hygiene(self) -> List[Finding]:
        """Check docs/INDEX.md for hygiene issues."""
        findings = []
        index_path = self.docs_dir / "INDEX.md"
        
        if not index_path.exists():
            findings.append(Finding(
                severity="ERROR",
                category="INDEX_HYGIENE",
                message="INDEX.md not found",
                location=str(index_path)
            ))
            return findings
        
        content = index_path.read_text(encoding="utf-8")
        
        # Check for Last Updated timestamp
        if "Last Updated" not in content and "last updated" not in content.lower():
            findings.append(Finding(
                severity="WARNING",
                category="INDEX_HYGIENE",
                message="INDEX.md missing 'Last Updated' timestamp",
                location=str(index_path)
            ))
        
        # Check for basic structure
        if "##" not in content:
            findings.append(Finding(
                severity="WARNING",
                category="INDEX_HYGIENE",
                message="INDEX.md may be missing section headers",
                location=str(index_path)
            ))
        
        # Check for broken internal links (bounded check)
        link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        link_count = 0
        for match in re.finditer(link_pattern, content):
            if link_count >= 50:  # bounded
                break
            link_count += 1
            link_text, link_target = match.groups()
            
            # Skip external links
            if link_target.startswith("http"):
                continue
            
            # Skip anchor links
            if link_target.startswith("#"):
                continue
                
            if link_target.startswith("file://"):
                # Absolute file link - check if exists
                target_path = link_target.replace("file:///", "").replace("file://", "")
                if not Path(target_path).exists():
                    findings.append(Finding(
                        severity="WARNING",
                        category="LINK_INTEGRITY",
                        message=f"Broken link: {link_text} -> {link_target}",
                        location=str(index_path)
                    ))
            else:
                # Relative link - check if exists
                # Handle line number references
                clean_target = link_target.split("#")[0]
                if clean_target:
                    target_path = self.docs_dir / clean_target
                    if not target_path.exists():
                        findings.append(Finding(
                            severity="WARNING",
                            category="LINK_INTEGRITY",
                            message=f"Broken relative link: {link_text} -> {link_target}",
                            location=str(index_path)
                        ))
        
        return findings
    
    def check_timestamp_freshness(self) -> List[Finding]:
        """Check if INDEX.md timestamp is reasonably fresh."""
        findings = []
        index_path = self.docs_dir / "INDEX.md"
        
        if not index_path.exists():
            return findings
        
        content = index_path.read_text(encoding="utf-8")
        
        # Look for timestamp patterns
        date_patterns = [
            r'Last Updated[:\s]+(\d{4}-\d{2}-\d{2})',
            r'\*\*Last Updated\*\*[:\s]+(\d{4}-\d{2}-\d{2})',
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                try:
                    timestamp = datetime.strptime(match.group(1), "%Y-%m-%d")
                    days_old = (datetime.now() - timestamp).days
                    if days_old > 30:
                        findings.append(Finding(
                            severity="INFO",
                            category="TIMESTAMP",
                            message=f"INDEX.md timestamp is {days_old} days old",
                            location=str(index_path)
                        ))
                except ValueError:
                    pass
                break
        
        return findings
    
    def check_root_cleanliness(self) -> List[Finding]:
        """Check that docs/ root only contains allowed files."""
        findings = []
        
        # Allowed at docs/ root
        allowed_root_files = {
            "INDEX.md",
            "LifeOS_Universal_Corpus.md",
            "LifeOS_Strategic_Corpus.md",
            ".obsidian"  # Obsidian config is okay
        }
        
        if not self.docs_dir.exists():
            return findings
        
        for item in self.docs_dir.iterdir():
            if item.is_file() and item.name not in allowed_root_files:
                findings.append(Finding(
                    severity="WARNING",
                    category="INDEX_HYGIENE",
                    message=f"Stray file at docs/ root: {item.name}",
                    location=str(item)
                ))
        
        return findings
    
    def _validate_diff_format(self, diff_content: str) -> List[Finding]:
        """Validate that proposed diffs are in recognizable format."""
        findings = []
        
        if not diff_content.strip():
            return findings
        
        # Check for unified diff markers
        has_diff_header = "---" in diff_content or "+++" in diff_content or "@@" in diff_content
        has_description = len(diff_content) > 10
        
        if not has_diff_header and has_description:
            # Prose description is NO LONGER ACCEPTABLE (Phase 1 Strict)
            findings.append(Finding(
                severity="ERROR",
                category="DIFF_VALIDATION",
                message="Strict Diff Enforcement: Proposed changes are in prose format, must be valid UNIFIED DIFF",
                location=""
            ))
        elif not has_description:
            findings.append(Finding(
                severity="ERROR",  # Changed to ERROR
                category="DIFF_VALIDATION",
                message="Proposed changes content is very short or empty",
                location=""
            ))
        
        return findings
    
    def _validate_proposed_paths(self, files_modified: List[Dict]) -> List[Finding]:
        """Validate that proposed file paths are in allowed locations."""
        findings = []
        
        forbidden = ["docs/00_foundations/", "docs/01_governance/", "GEMINI.md"]
        allowed = ["docs/"]
        
        for fm in files_modified:
            path = fm.get("path", "")
            
            # Check forbidden
            for f in forbidden:
                if path.startswith(f) or path == f:
                    findings.append(Finding(
                        severity="ERROR",
                        category="DIFF_VALIDATION",
                        message=f"Proposed change to forbidden path: {path}",
                        location=path
                    ))
                    break
            
            # Check allowed
            in_allowed = any(path.startswith(a) for a in allowed)
            if not in_allowed and path:
                findings.append(Finding(
                    severity="WARNING",
                    category="DIFF_VALIDATION",
                    message=f"Proposed change outside allowed paths: {path}",
                    location=path
                ))
        
        return findings
    
    def _check_proposed_post_state(self, proposed_diffs: str) -> List[Finding]:
        """
        Check that proposed post-state would be valid.
        For now, just validates the diff looks reasonable.
        Full temp-workspace simulation deferred to later phase.
        """
        findings = []
        
        # Basic sanity: if updating timestamp, check format is correct
        if "Last Updated" in proposed_diffs:
            # Check for valid date format in the proposed change
            date_match = re.search(r'Last Updated[:\s]+(\d{4}-\d{2}-\d{2})', proposed_diffs)
            if date_match:
                try:
                    datetime.strptime(date_match.group(1), "%Y-%m-%d")
                    findings.append(Finding(
                        severity="INFO",
                        category="DIFF_VALIDATION",
                        message=f"Timestamp change validated: {date_match.group(1)}",
                        location=""
                    ))
                except ValueError:
                    findings.append(Finding(
                        severity="ERROR",
                        category="DIFF_VALIDATION",
                        message=f"Invalid date format in proposed change: {date_match.group(1)}",
                        location=""
                    ))
        
        return findings


# === CLI for standalone testing ===
def main():
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description="Doc Verifier")
    parser.add_argument("--docs-dir", type=str, default=None,
                        help="Path to docs directory")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON")
    
    args = parser.parse_args()
    
    docs_dir = Path(args.docs_dir) if args.docs_dir else None
    verifier = DocVerifier(docs_dir=docs_dir)
    outcome = verifier.verify()
    
    if args.json:
        print(json.dumps({
            "passed": outcome.passed,
            "summary": outcome.summary,
            "details": outcome.details,
            "findings": [asdict(f) for f in outcome.findings]
        }, indent=2))
    else:
        print(f"VERIFIER OUTCOME: {'PASS' if outcome.passed else 'FAIL'}")
        print(f"Summary: {outcome.summary}")
        for f in outcome.findings:
            print(f"  [{f.severity}] {f.category}: {f.message}")
    
    return 0 if outcome.passed else 1


if __name__ == "__main__":
    exit(main())
