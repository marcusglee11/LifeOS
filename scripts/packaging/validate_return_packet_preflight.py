#!/usr/bin/env python3
"""
Return-Packet Preflight Validator (RPPV v2.6a)

Mandatory-by-default preflight gate for return packets.
Implements checks RPPV-001 through RPPV-014 per Plan v2.6a.

Usage:
    python -m scripts.packaging.validate_return_packet_preflight \
        --repo-root <path> --packet-dir <path> --stage-dir <path> \
        --zip-path <path> --mode auto --json
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import yaml

# ============================================================================
# CONSTANTS (Single Source of Truth)
# ============================================================================

EOF_SENTINEL = "__EOF_SENTINEL__"
TEST_RESULT_MARKER = "TEST_RESULT: PASS"
TEST_EXIT_CODE_MARKER = "TEST_EXIT_CODE: 0"

# Canonical file ordering for digest computation
REQUIRED_FILES = [
    "00_manifest.json",
    "07_git_diff.patch",
    "08_evidence_manifest.sha256",
    # PRIMARY_NARRATIVE_FILE is determined dynamically
]

OPTIONAL_FILES = [
    "01_patch_summary.md",
    "02_git_status.txt",
    "03_test_log_full.txt",
    "04_validator_output.json",
    "review_packet.json",
    "audit_report.md",
]

NARRATIVE_PRECEDENCE = ["FIX_RETURN.md", "README.md", "RESULT.md"]

TEXT_EXTENSIONS = {".md", ".txt", ".json", ".yaml", ".yml", ".patch"}

# Files excluded from digest (outputs of this validator)
DIGEST_EXCLUDES = {"preflight_report.json", "preflight_log.txt"}


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class CheckResult:
    """Result of a single check."""
    id: str
    category: str
    status: str  # PASS, FAIL, SKIP, BLOCK
    message: str


@dataclass
class PreflightResult:
    """Overall preflight result."""
    outcome: str  # PASS, FAIL, BLOCK
    packet_digest: str
    env_digest: str
    timestamp: str
    skipped: bool = False
    context: dict = field(default_factory=dict)
    results: list = field(default_factory=list)
    failed_ids: list = field(default_factory=list)
    skipped_ids: list = field(default_factory=list)
    blocked_ids: list = field(default_factory=list)


# ============================================================================
# DIGEST COMPUTATION
# ============================================================================

def normalize_content(content: bytes, is_text: bool) -> bytes:
    """Normalize content: CRLF -> LF for text files."""
    if is_text:
        return content.replace(b"\r\n", b"\n")
    return content


def compute_file_digest_contribution(filename: str, content: bytes) -> bytes:
    """Compute the digest contribution for a single file.
    
    Framing: len(P)[4 bytes big-endian] + P + len(C)[8 bytes big-endian] + C
    """
    path_bytes = filename.encode("utf-8")
    return (
        len(path_bytes).to_bytes(4, "big") +
        path_bytes +
        len(content).to_bytes(8, "big") +
        content
    )


def compute_packet_digest(packet_dir: Path, primary_narrative: Optional[str]) -> str:
    """Compute packet_digest over REQUIRED + OPTIONAL-if-present files."""
    hasher = hashlib.sha256()
    
    # Build ordered file list
    files_to_hash = []
    
    # REQUIRED files (in order)
    for fname in REQUIRED_FILES:
        fpath = packet_dir / fname
        if fpath.exists():
            files_to_hash.append((fname, fpath))
    
    # Add primary narrative
    if primary_narrative:
        fpath = packet_dir / primary_narrative
        if fpath.exists():
            files_to_hash.append((primary_narrative, fpath))
    
    # OPTIONAL files (in order, only if present)
    for fname in OPTIONAL_FILES:
        fpath = packet_dir / fname
        if fpath.exists():
            files_to_hash.append((fname, fpath))
    
    # Compute digest
    for fname, fpath in files_to_hash:
        if fname in DIGEST_EXCLUDES:
            continue
        content = fpath.read_bytes()
        is_text = fpath.suffix.lower() in TEXT_EXTENSIONS
        normalized = normalize_content(content, is_text)
        contribution = compute_file_digest_contribution(fname, normalized)
        hasher.update(contribution)
    
    return hasher.hexdigest()


def compute_env_digest(repo_root: Path, validator_path: Path) -> str:
    """Compute env_digest over external inputs that affect correctness."""
    hasher = hashlib.sha256()
    
    # Files to include (sorted lexicographically)
    env_files = []
    
    allowlist_path = repo_root / "config" / "packaging" / "preflight_allowlist.yaml"
    if allowlist_path.exists():
        env_files.append(("config/packaging/preflight_allowlist.yaml", allowlist_path))
    
    if validator_path.exists():
        rel_path = str(validator_path.relative_to(repo_root)) if validator_path.is_relative_to(repo_root) else str(validator_path)
        env_files.append((rel_path, validator_path))
    
    env_files.sort(key=lambda x: x[0])
    
    for rel_path, fpath in env_files:
        content = fpath.read_bytes()
        is_text = fpath.suffix.lower() in TEXT_EXTENSIONS
        normalized = normalize_content(content, is_text)
        contribution = compute_file_digest_contribution(rel_path, normalized)
        hasher.update(contribution)
    
    return hasher.hexdigest()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_primary_narrative(packet_dir: Path) -> Optional[str]:
    """Get the primary narrative file per precedence list."""
    for fname in NARRATIVE_PRECEDENCE:
        if (packet_dir / fname).exists():
            return fname
    return None


def load_allowlist(repo_root: Path) -> list:
    """Load allowlist from canonical YAML file."""
    allowlist_path = repo_root / "config" / "packaging" / "preflight_allowlist.yaml"
    if not allowlist_path.exists():
        return []
    with open(allowlist_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("allowlist", [])


def extract_patch_paths(patch_content: str) -> list:
    """Extract file paths from git diff headers."""
    paths = []
    for match in re.finditer(r"^diff --git a/(.+?) b/(.+?)$", patch_content, re.MULTILINE):
        paths.append(match.group(2))  # Use b/ path
    return paths


def check_path_in_allowlist(path: str, allowlist: list) -> bool:
    """Check if a path matches any allowlist entry."""
    for allowed in allowlist:
        if allowed.endswith("/"):
            # Directory prefix
            if path.startswith(allowed) or path.startswith(allowed.rstrip("/")):
                return True
        else:
            # Exact path
            if path == allowed:
                return True
    return False


# ============================================================================
# CHECKS
# ============================================================================

def check_rppv_001(stage_dir: Path, repo_root: Path) -> CheckResult:
    """RPPV-001: stage_dir is outside repo_root."""
    try:
        stage_resolved = stage_dir.resolve()
        repo_resolved = repo_root.resolve()
        
        if stage_resolved.is_relative_to(repo_resolved):
            return CheckResult(
                id="RPPV-001",
                category="Hygiene",
                status="FAIL",
                message=f"stage_dir {stage_dir} is inside repo_root {repo_root}"
            )
        return CheckResult(
            id="RPPV-001",
            category="Hygiene",
            status="PASS",
            message="stage_dir is outside repo_root"
        )
    except Exception as e:
        return CheckResult(
            id="RPPV-001",
            category="Hygiene",
            status="FAIL",
            message=f"Error checking paths: {e}"
        )


def check_rppv_002(packet_dir: Path, repo_root: Path) -> CheckResult:
    """RPPV-002: Patch paths match allowlist YAML."""
    patch_path = packet_dir / "07_git_diff.patch"
    if not patch_path.exists():
        return CheckResult(
            id="RPPV-002",
            category="Hygiene",
            status="SKIP",
            message="07_git_diff.patch not found"
        )
    
    allowlist = load_allowlist(repo_root)
    if not allowlist:
        return CheckResult(
            id="RPPV-002",
            category="Hygiene",
            status="FAIL",
            message="Allowlist not found or empty"
        )
    
    patch_content = patch_path.read_text(encoding="utf-8", errors="replace")
    patch_paths = extract_patch_paths(patch_content)
    
    violations = []
    for p in patch_paths:
        if not check_path_in_allowlist(p, allowlist):
            violations.append(p)
    
    if violations:
        return CheckResult(
            id="RPPV-002",
            category="Hygiene",
            status="FAIL",
            message=f"Paths not in allowlist: {violations[:5]}"
        )
    
    return CheckResult(
        id="RPPV-002",
        category="Hygiene",
        status="PASS",
        message=f"All {len(patch_paths)} paths in allowlist"
    )


def check_rppv_003(packet_dir: Path, repo_root: Path) -> CheckResult:
    """RPPV-003: Patch byte-match invariant (git diff) with LF normalization."""
    patch_path = packet_dir / "07_git_diff.patch"
    if not patch_path.exists():
        return CheckResult(
            id="RPPV-003",
            category="Coherence",
            status="FAIL",
            message="07_git_diff.patch not found"
        )
    
    allowlist = load_allowlist(repo_root)
    if not allowlist:
        return CheckResult(
            id="RPPV-003",
            category="Coherence",
            status="FAIL",
            message="Allowlist not found"
        )
    
    # Read and normalize actual patch
    actual_bytes = patch_path.read_bytes().replace(b"\r\n", b"\n")
    actual_hash = hashlib.sha256(actual_bytes).hexdigest()
    
    # Generate expected patch
    try:
        cmd = ["git", "diff", "--no-color", "--"] + allowlist
        result = subprocess.run(
            cmd,
            cwd=repo_root,
            capture_output=True,
            timeout=30
        )
        expected_bytes = result.stdout.replace(b"\r\n", b"\n")
        expected_hash = hashlib.sha256(expected_bytes).hexdigest()
    except Exception as e:
        return CheckResult(
            id="RPPV-003",
            category="Coherence",
            status="FAIL",
            message=f"Error running git diff: {e}"
        )
    
    if actual_hash != expected_hash:
        return CheckResult(
            id="RPPV-003",
            category="Coherence",
            status="FAIL",
            message=f"Patch mismatch: actual={actual_hash[:16]}... expected={expected_hash[:16]}..."
        )
    
    return CheckResult(
        id="RPPV-003",
        category="Coherence",
        status="PASS",
        message="Patch matches git diff --no-color"
    )


def check_rppv_004(packet_dir: Path) -> CheckResult:
    """RPPV-004: REQUIRED file set exists."""
    missing = []
    
    for fname in REQUIRED_FILES:
        if not (packet_dir / fname).exists():
            missing.append(fname)
    
    # Check primary narrative
    primary = get_primary_narrative(packet_dir)
    if not primary:
        missing.append("PRIMARY_NARRATIVE (FIX_RETURN.md|README.md|RESULT.md)")
    
    if missing:
        return CheckResult(
            id="RPPV-004",
            category="Content",
            status="FAIL",
            message=f"Missing required files: {missing}"
        )
    
    return CheckResult(
        id="RPPV-004",
        category="Content",
        status="PASS",
        message="All required files present"
    )


def check_rppv_005(zip_path: Path) -> CheckResult:
    """RPPV-005: Zip contains a single top-level folder."""
    if not zip_path or not zip_path.exists():
        return CheckResult(
            id="RPPV-005",
            category="Content",
            status="SKIP",
            message="Zip path not provided or not found"
        )
    
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            top_level = set()
            for name in zf.namelist():
                parts = name.split("/")
                if parts[0]:
                    top_level.add(parts[0])
            
            if len(top_level) != 1:
                return CheckResult(
                    id="RPPV-005",
                    category="Content",
                    status="FAIL",
                    message=f"Expected 1 top-level folder, found {len(top_level)}: {list(top_level)[:5]}"
                )
    except Exception as e:
        return CheckResult(
            id="RPPV-005",
            category="Content",
            status="FAIL",
            message=f"Error reading zip: {e}"
        )
    
    return CheckResult(
        id="RPPV-005",
        category="Content",
        status="PASS",
        message="Single top-level folder in zip"
    )


def check_rppv_006(packet_dir: Path) -> CheckResult:
    """RPPV-006: Non-empty patch (>=1 diff header)."""
    patch_path = packet_dir / "07_git_diff.patch"
    if not patch_path.exists():
        return CheckResult(
            id="RPPV-006",
            category="Content",
            status="FAIL",
            message="07_git_diff.patch not found"
        )
    
    content = patch_path.read_text(encoding="utf-8", errors="replace")
    if "diff --git" not in content:
        return CheckResult(
            id="RPPV-006",
            category="Content",
            status="FAIL",
            message="Patch contains no diff headers"
        )
    
    return CheckResult(
        id="RPPV-006",
        category="Content",
        status="PASS",
        message="Patch contains diff headers"
    )


def check_rppv_007(packet_dir: Path) -> CheckResult:
    """RPPV-007: 00_manifest.json parseable + complete."""
    manifest_path = packet_dir / "00_manifest.json"
    if not manifest_path.exists():
        return CheckResult(
            id="RPPV-007",
            category="Content",
            status="FAIL",
            message="00_manifest.json not found"
        )
    
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Basic structure check
        if not isinstance(data, dict):
            return CheckResult(
                id="RPPV-007",
                category="Content",
                status="FAIL",
                message="Manifest is not a JSON object"
            )
    except json.JSONDecodeError as e:
        return CheckResult(
            id="RPPV-007",
            category="Content",
            status="FAIL",
            message=f"Manifest JSON parse error: {e}"
        )
    
    return CheckResult(
        id="RPPV-007",
        category="Content",
        status="PASS",
        message="Manifest is valid JSON"
    )


def check_rppv_008(packet_dir: Path) -> CheckResult:
    """RPPV-008: Manifest hashes verify against bytes."""
    manifest_path = packet_dir / "08_evidence_manifest.sha256"
    if not manifest_path.exists():
        return CheckResult(
            id="RPPV-008",
            category="Content",
            status="FAIL",
            message="08_evidence_manifest.sha256 not found"
        )
    
    try:
        content = manifest_path.read_text(encoding="utf-8")
        failures = []
        
        for line in content.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) >= 2:
                expected_hash = parts[0].lower()
                filename = parts[1].lstrip("*")
                
                file_path = packet_dir / filename
                if file_path.exists():
                    actual_hash = hashlib.sha256(file_path.read_bytes()).hexdigest().lower()
                    if actual_hash != expected_hash:
                        failures.append(f"{filename}: expected {expected_hash[:16]}..., got {actual_hash[:16]}...")
        
        if failures:
            return CheckResult(
                id="RPPV-008",
                category="Content",
                status="FAIL",
                message=f"Hash mismatches: {failures[:3]}"
            )
    except Exception as e:
        return CheckResult(
            id="RPPV-008",
            category="Content",
            status="FAIL",
            message=f"Error verifying hashes: {e}"
        )
    
    return CheckResult(
        id="RPPV-008",
        category="Content",
        status="PASS",
        message="All manifest hashes verified"
    )


def check_rppv_009(packet_dir: Path) -> CheckResult:
    """RPPV-009: EOF sentinel on primary narrative file."""
    primary = get_primary_narrative(packet_dir)
    if not primary:
        return CheckResult(
            id="RPPV-009",
            category="Sentinel",
            status="FAIL",
            message="No primary narrative file found"
        )
    
    narrative_path = packet_dir / primary
    content = narrative_path.read_text(encoding="utf-8", errors="replace")
    
    # Get last non-empty line
    lines = content.strip().split("\n")
    last_line = lines[-1].strip() if lines else ""
    
    if last_line != EOF_SENTINEL:
        return CheckResult(
            id="RPPV-009",
            category="Sentinel",
            status="FAIL",
            message=f"Last line of {primary} is '{last_line[:30]}...', expected '{EOF_SENTINEL}'"
        )
    
    return CheckResult(
        id="RPPV-009",
        category="Sentinel",
        status="PASS",
        message=f"EOF sentinel present in {primary}"
    )


def check_rppv_010(packet_dir: Path) -> CheckResult:
    """RPPV-010: WARN only if ellipsis present AND sentinel missing."""
    primary = get_primary_narrative(packet_dir)
    if not primary:
        return CheckResult(
            id="RPPV-010",
            category="Sentinel",
            status="SKIP",
            message="No primary narrative file"
        )
    
    narrative_path = packet_dir / primary
    content = narrative_path.read_text(encoding="utf-8", errors="replace")
    
    # Check for ellipsis
    has_ellipsis = "..." in content or "…" in content
    
    # Check for sentinel
    lines = content.strip().split("\n")
    last_line = lines[-1].strip() if lines else ""
    has_sentinel = last_line == EOF_SENTINEL
    
    if has_ellipsis and not has_sentinel:
        return CheckResult(
            id="RPPV-010",
            category="Sentinel",
            status="FAIL",  # WARN treated as FAIL for strictness
            message=f"Ellipsis found in {primary} but no EOF sentinel"
        )
    
    return CheckResult(
        id="RPPV-010",
        category="Sentinel",
        status="PASS",
        message="No ellipsis/sentinel conflict"
    )


def check_rppv_011(packet_dir: Path) -> CheckResult:
    """RPPV-011: If 01_patch_summary.md present, summary ↔ diff coherent."""
    summary_path = packet_dir / "01_patch_summary.md"
    if not summary_path.exists():
        return CheckResult(
            id="RPPV-011",
            category="Coherence",
            status="SKIP",
            message="01_patch_summary.md not present"
        )
    
    # Basic check: summary exists and is non-empty
    content = summary_path.read_text(encoding="utf-8", errors="replace")
    if len(content.strip()) < 10:
        return CheckResult(
            id="RPPV-011",
            category="Coherence",
            status="FAIL",
            message="Patch summary is too short"
        )
    
    return CheckResult(
        id="RPPV-011",
        category="Coherence",
        status="PASS",
        message="Patch summary present and non-empty"
    )


def check_rppv_012(packet_dir: Path) -> CheckResult:
    """RPPV-012: If 03_test_log_full.txt present, require TEST_RESULT: PASS and TEST_EXIT_CODE: 0."""
    log_path = packet_dir / "03_test_log_full.txt"
    if not log_path.exists():
        return CheckResult(
            id="RPPV-012",
            category="Coherence",
            status="SKIP",
            message="03_test_log_full.txt not present"
        )
    
    content = log_path.read_text(encoding="utf-8", errors="replace")
    
    has_pass = TEST_RESULT_MARKER in content
    has_exit_0 = TEST_EXIT_CODE_MARKER in content
    
    if not has_pass or not has_exit_0:
        missing = []
        if not has_pass:
            missing.append(TEST_RESULT_MARKER)
        if not has_exit_0:
            missing.append(TEST_EXIT_CODE_MARKER)
        return CheckResult(
            id="RPPV-012",
            category="Coherence",
            status="FAIL",
            message=f"Missing markers: {missing}"
        )
    
    return CheckResult(
        id="RPPV-012",
        category="Coherence",
        status="PASS",
        message="Test log contains PASS markers"
    )


def check_rppv_013(packet_dir: Path, is_exit_blocker: bool) -> CheckResult:
    """RPPV-013: If exit-blocker context true, certification cmd used."""
    if not is_exit_blocker:
        return CheckResult(
            id="RPPV-013",
            category="Coherence",
            status="SKIP",
            message="Not an exit-blocker context"
        )
    
    # Check for certification evidence
    log_path = packet_dir / "03_test_log_full.txt"
    if not log_path.exists():
        return CheckResult(
            id="RPPV-013",
            category="Coherence",
            status="FAIL",
            message="Exit-blocker requires test log"
        )
    
    content = log_path.read_text(encoding="utf-8", errors="replace")
    
    # Look for certification command signature
    if "run_certification_tests" in content or "pytest" in content:
        return CheckResult(
            id="RPPV-013",
            category="Coherence",
            status="PASS",
            message="Certification command evidence found"
        )
    
    return CheckResult(
        id="RPPV-013",
        category="Coherence",
        status="FAIL",
        message="No certification command evidence in log"
    )


def check_rppv_014(packet_dir: Path, repo_root: Path) -> CheckResult:
    """RPPV-014: git apply --check succeeds in temp worktree."""
    patch_path = packet_dir / "07_git_diff.patch"
    if not patch_path.exists():
        return CheckResult(
            id="RPPV-014",
            category="Replay",
            status="FAIL",
            message="07_git_diff.patch not found"
        )
    
    worktree_dir = None
    try:
        # Create temp dir for worktree
        with tempfile.TemporaryDirectory(prefix="rppv_wt_") as tmp_dir:
            worktree_dir = Path(tmp_dir)
            
            # Create detached worktree at HEAD
            subprocess.run(
                ["git", "worktree", "add", "--detach", str(worktree_dir)],
                cwd=repo_root,
                check=True,
                capture_output=True
            )
            
            try:
                # Run git apply --check in worktree
                # Patch path is absolute, so it works.
                result = subprocess.run(
                    ["git", "apply", "--check", str(patch_path.resolve())],
                    cwd=worktree_dir,
                    capture_output=True,
                    timeout=30
                )
                
                if result.returncode != 0:
                    stderr = result.stderr.decode("utf-8", errors="replace")[:200]
                    return CheckResult(
                        id="RPPV-014",
                        category="Replay",
                        status="FAIL",
                        message=f"git apply --check failed in clean worktree: {stderr}"
                    )
            finally:
                # Cleanup worktree
                # Need to use 'git worktree remove' AND process cleanup?
                # tempfile handles dir, but git might complain if not removed from its list.
                pass
                
        # Outside tempfile context, dir is gone. Prune git worktrees?
        subprocess.run(["git", "worktree", "prune"], cwd=repo_root, check=False, capture_output=True)

    except Exception as e:
        # Cleanup
        subprocess.run(["git", "worktree", "prune"], cwd=repo_root, check=False, capture_output=True)
        return CheckResult(
            id="RPPV-014",
            category="Replay",
            status="FAIL",
            message=f"Error running git apply in worktree: {e}"
        )
    
    return CheckResult(
        id="RPPV-014",
        category="Replay",
        status="PASS",
        message="Patch applies cleanly to HEAD"
    )


# ============================================================================
# WAIVER BINDING
# ============================================================================

def check_waiver_skip(
    packet_dir: Path,
    repo_root: Path,
    skip_requested: bool
) -> Optional[CheckResult]:
    """Check waiver binding for skip requests. Returns BLOCK result if invalid."""
    if not skip_requested:
        return None
    
    review_packet_path = packet_dir / "review_packet.json"
    if not review_packet_path.exists():
        return CheckResult(
            id="WAIVER",
            category="Skip",
            status="BLOCK",
            message="Skip requires review_packet.json for run_id binding"
        )
    
    try:
        with open(review_packet_path, "r", encoding="utf-8") as f:
            review_data = json.load(f)
    except Exception as e:
        return CheckResult(
            id="WAIVER",
            category="Skip",
            status="BLOCK",
            message=f"Error reading review_packet.json: {e}"
        )
    
    run_id = review_data.get("run_id")
    if not run_id:
        return CheckResult(
            id="WAIVER",
            category="Skip",
            status="BLOCK",
            message="review_packet.json missing run_id field"
        )
    
    waiver_path = repo_root / "artifacts" / "loop_state" / f"WAIVER_DECISION_{run_id}.json"
    if not waiver_path.exists():
        return CheckResult(
            id="WAIVER",
            category="Skip",
            status="BLOCK",
            message=f"Waiver artifact not found: {waiver_path}"
        )
    
    try:
        with open(waiver_path, "r", encoding="utf-8") as f:
            waiver_data = json.load(f)
    except Exception as e:
        return CheckResult(
            id="WAIVER",
            category="Skip",
            status="BLOCK",
            message=f"Error reading waiver: {e}"
        )
    
    decision = waiver_data.get("decision")
    if decision != "APPROVE":
        return CheckResult(
            id="WAIVER",
            category="Skip",
            status="BLOCK",
            message=f"Waiver decision is '{decision}', need 'APPROVE'"
        )
    
    return None  # Waiver valid


# ============================================================================
# MAIN VALIDATOR
# ============================================================================

def run_preflight(
    repo_root: Path,
    packet_dir: Path,
    stage_dir: Path,
    zip_path: Optional[Path],
    mode: str = "auto",
    skip_preflight: bool = False,
    json_output: bool = False
) -> PreflightResult:
    """Run all preflight checks."""
    
    # Get primary narrative and compute digests
    primary_narrative = get_primary_narrative(packet_dir)
    validator_path = Path(__file__).resolve()
    
    packet_digest = compute_packet_digest(packet_dir, primary_narrative)
    env_digest = compute_env_digest(repo_root, validator_path)
    timestamp = datetime.now(timezone.utc).isoformat()
    
    # Check for idempotent skip
    report_path = packet_dir / "preflight_report.json"
    if report_path.exists():
        try:
            with open(report_path, "r", encoding="utf-8") as f:
                prev_report = json.load(f)
            
            if (
                prev_report.get("outcome") == "PASS" and
                prev_report.get("packet_digest") == packet_digest and
                prev_report.get("env_digest") == env_digest
            ):
                return PreflightResult(
                    outcome="PASS",
                    packet_digest=packet_digest,
                    env_digest=env_digest,
                    timestamp=timestamp,
                    skipped=True,
                    context=prev_report.get("context", {}),
                    results=[],
                    failed_ids=[],
                    skipped_ids=[],
                    blocked_ids=[]
                )
        except Exception:
            pass  # Continue with full validation
    
    # Check waiver for skip requests
    waiver_result = check_waiver_skip(packet_dir, repo_root, skip_preflight)
    if waiver_result:
        return PreflightResult(
            outcome="BLOCK",
            packet_digest=packet_digest,
            env_digest=env_digest,
            timestamp=timestamp,
            skipped=False,
            context={"skip_requested": True},
            results=[waiver_result],
            failed_ids=[],
            skipped_ids=[],
            blocked_ids=[waiver_result.id]
        )
    
    # Detect context
    is_exit_blocker = False
    review_packet_path = packet_dir / "review_packet.json"
    if review_packet_path.exists():
        try:
            with open(review_packet_path, "r", encoding="utf-8") as f:
                review_data = json.load(f)
            is_exit_blocker = review_data.get("review_type") == "exit_blocker"
        except Exception:
            pass
    
    context = {
        "mode": mode,
        "exit_blocker": is_exit_blocker,
        "return_packet": True,
        "primary_narrative": primary_narrative
    }
    
    # Run all checks
    results = []
    
    results.append(check_rppv_001(stage_dir, repo_root))
    results.append(check_rppv_002(packet_dir, repo_root))
    results.append(check_rppv_003(packet_dir, repo_root))
    results.append(check_rppv_004(packet_dir))
    results.append(check_rppv_005(zip_path))
    results.append(check_rppv_006(packet_dir))
    results.append(check_rppv_007(packet_dir))
    results.append(check_rppv_008(packet_dir))
    results.append(check_rppv_009(packet_dir))
    results.append(check_rppv_010(packet_dir))
    results.append(check_rppv_011(packet_dir))
    results.append(check_rppv_012(packet_dir))
    results.append(check_rppv_013(packet_dir, is_exit_blocker))
    results.append(check_rppv_014(packet_dir, repo_root))
    
    # Collect outcomes
    failed_ids = sorted([r.id for r in results if r.status == "FAIL"])
    skipped_ids = sorted([r.id for r in results if r.status == "SKIP"])
    blocked_ids = sorted([r.id for r in results if r.status == "BLOCK"])
    
    if blocked_ids:
        outcome = "BLOCK"
    elif failed_ids:
        outcome = "FAIL"
    else:
        outcome = "PASS"
    
    return PreflightResult(
        outcome=outcome,
        packet_digest=packet_digest,
        env_digest=env_digest,
        timestamp=timestamp,
        skipped=False,
        context=context,
        results=results,
        failed_ids=failed_ids,
        skipped_ids=skipped_ids,
        blocked_ids=blocked_ids
    )


def main():
    parser = argparse.ArgumentParser(description="Return-Packet Preflight Validator (RPPV v2.6a)")
    parser.add_argument("--repo-root", type=Path, required=True, help="Git repository root")
    parser.add_argument("--packet-dir", type=Path, required=True, help="Packet directory")
    parser.add_argument("--stage-dir", type=Path, required=True, help="Staging directory (must be outside repo)")
    parser.add_argument("--zip-path", type=Path, help="Path to zip file")
    parser.add_argument("--mode", default="auto", choices=["auto"], help="Validation mode")
    parser.add_argument("--skip-preflight", action="store_true", help="Request preflight skip (requires valid waiver)")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    
    args = parser.parse_args()
    
    result = run_preflight(
        repo_root=args.repo_root,
        packet_dir=args.packet_dir,
        stage_dir=args.stage_dir,
        zip_path=args.zip_path,
        mode=args.mode,
        skip_preflight=args.skip_preflight,
        json_output=args.json
    )
    
    # Write report
    report_path = args.packet_dir / "preflight_report.json"
    report_data = {
        "outcome": result.outcome,
        "packet_digest": result.packet_digest,
        "env_digest": result.env_digest,
        "timestamp": result.timestamp,
        "skipped": result.skipped,
        "context": result.context,
        "results": [
            {
                "id": r.id,
                "category": r.category,
                "status": r.status,
                "message": r.message
            }
            for r in result.results
        ],
        "failed_ids": result.failed_ids,
        "skipped_ids": result.skipped_ids,
        "blocked_ids": result.blocked_ids
    }
    
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2, sort_keys=True)
    
    if args.json:
        print(json.dumps(report_data, indent=2, sort_keys=True))
    else:
        print(f"Outcome: {result.outcome}")
        if result.skipped:
            print("  (Skipped - digests match prior PASS)")
        if result.failed_ids:
            print(f"  Failed: {result.failed_ids}")
        if result.blocked_ids:
            print(f"  Blocked: {result.blocked_ids}")
    
    # Exit code: 0 for PASS, 1 for FAIL/BLOCK
    exit(0 if result.outcome == "PASS" else 1)


if __name__ == "__main__":
    main()
