"""Evidence tier enforcement and manifest compute/verify."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set

from runtime.validation.reporting import sha256_file, write_json_atomic


REQUIRED_FILES_BY_TIER: Dict[str, Set[str]] = {
    "light": {
        "meta.json",
        "exitcode.txt",
        "commands.jsonl",
        "evidence_manifest.json",
    },
    "standard": {
        "meta.json",
        "exitcode.txt",
        "commands.jsonl",
        "evidence_manifest.json",
        "stdout.txt",
        "stderr.txt",
        "git_head.txt",
        "git_status.txt",
    },
    "full": {
        "meta.json",
        "exitcode.txt",
        "commands.jsonl",
        "evidence_manifest.json",
        "stdout.txt",
        "stderr.txt",
        "git_head.txt",
        "git_status.txt",
        "git_diff_name_only.txt",
    },
}


class EvidenceError(RuntimeError):
    def __init__(self, code: str, message: str, next_action: str = "RECAPTURE_EVIDENCE"):
        self.code = code
        self.next_action = next_action
        super().__init__(message)


def _iter_files(root: Path, exclude_relpaths: Iterable[str]) -> Iterable[Path]:
    excluded = set(exclude_relpaths)
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if rel in excluded:
            continue
        yield path


def required_files_for_tier(tier: str, extras: List[str] | None = None) -> Set[str]:
    if tier not in REQUIRED_FILES_BY_TIER:
        raise EvidenceError("JOB_SPEC_INVALID", f"Unsupported evidence tier: {tier}", "HALT_SCHEMA_DRIFT")
    required = set(REQUIRED_FILES_BY_TIER[tier])
    if extras:
        required.update(extras)
    return required


def enforce_evidence_tier(evidence_root: Path, tier: str, extras: List[str] | None = None) -> None:
    missing = []
    for rel in sorted(required_files_for_tier(tier, extras)):
        if not (evidence_root / rel).exists():
            missing.append(rel)
    if missing:
        raise EvidenceError(
            "EVIDENCE_MISSING_REQUIRED_FILE",
            f"Missing required evidence files for tier '{tier}': {missing}",
        )


def compute_manifest(evidence_root: Path, manifest_path: Path | None = None) -> Dict[str, Any]:
    if manifest_path is None:
        manifest_path = evidence_root / "evidence_manifest.json"

    manifest_rel = manifest_path.relative_to(evidence_root).as_posix()
    files = []
    for path in _iter_files(evidence_root, exclude_relpaths=[manifest_rel]):
        rel = path.relative_to(evidence_root).as_posix()
        files.append(
            {
                "relpath": rel,
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
        )

    files_sorted = sorted(files, key=lambda entry: entry["relpath"])
    payload: Dict[str, Any] = {
        "schema_version": "evidence_manifest_v1",
        "files": files_sorted,
    }
    write_json_atomic(manifest_path, payload)
    return payload


def verify_manifest(evidence_root: Path, manifest_path: Path | None = None) -> Dict[str, Any]:
    if manifest_path is None:
        manifest_path = evidence_root / "evidence_manifest.json"

    if not manifest_path.exists():
        raise EvidenceError("EVIDENCE_MISSING_REQUIRED_FILE", "evidence_manifest.json is missing")

    with open(manifest_path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if payload.get("schema_version") != "evidence_manifest_v1":
        raise EvidenceError("EVIDENCE_HASH_MISMATCH", "Unsupported evidence manifest schema")

    entries = payload.get("files")
    if not isinstance(entries, list):
        raise EvidenceError("EVIDENCE_HASH_MISMATCH", "Manifest files must be a list")

    seen_relpaths: Set[str] = set()
    manifest_relpaths: Set[str] = set()
    for entry in entries:
        rel = entry.get("relpath")
        expected_sha = entry.get("sha256")
        if not isinstance(rel, str) or not isinstance(expected_sha, str):
            raise EvidenceError("EVIDENCE_HASH_MISMATCH", "Manifest entry is malformed")
        if rel in seen_relpaths:
            raise EvidenceError("EVIDENCE_HASH_MISMATCH", f"Duplicate relpath in manifest: {rel}")
        seen_relpaths.add(rel)
        manifest_relpaths.add(rel)

        file_path = evidence_root / rel
        if not file_path.exists():
            raise EvidenceError("EVIDENCE_MISSING_REQUIRED_FILE", f"Missing evidence file: {rel}")

        actual_sha = sha256_file(file_path)
        if actual_sha != expected_sha:
            raise EvidenceError(
                "EVIDENCE_HASH_MISMATCH",
                f"Hash mismatch for {rel}: expected {expected_sha}, got {actual_sha}",
            )

    manifest_rel = manifest_path.relative_to(evidence_root).as_posix()
    actual_relpaths = {
        path.relative_to(evidence_root).as_posix()
        for path in _iter_files(evidence_root, exclude_relpaths=[manifest_rel])
    }
    orphan_relpaths = sorted(actual_relpaths - manifest_relpaths)
    if orphan_relpaths:
        raise EvidenceError(
            "EVIDENCE_ORPHAN_FILE",
            f"Orphan evidence files detected: {orphan_relpaths}",
            next_action="RECAPTURE_EVIDENCE",
        )

    return payload
