from __future__ import annotations

from pathlib import Path

import pytest

from runtime.validation.evidence import (
    EvidenceError,
    compute_manifest,
    enforce_evidence_tier,
    verify_manifest,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _build_light_evidence(evidence_root: Path) -> None:
    _write(evidence_root / "meta.json", "{}\n")
    _write(evidence_root / "exitcode.txt", "0\n")
    _write(evidence_root / "commands.jsonl", "{\"cmd\":\"true\"}\n")


def test_enforce_tier_missing_required_file(tmp_path: Path) -> None:
    evidence_root = tmp_path / "evidence"
    evidence_root.mkdir(parents=True, exist_ok=True)
    _write(evidence_root / "meta.json", "{}\n")
    _write(evidence_root / "commands.jsonl", "{\"cmd\":\"true\"}\n")

    with pytest.raises(EvidenceError) as exc:
        enforce_evidence_tier(evidence_root, "light")

    assert exc.value.code == "EVIDENCE_MISSING_REQUIRED_FILE"


def test_manifest_compute_verify_and_orphan_detection(tmp_path: Path) -> None:
    evidence_root = tmp_path / "evidence"
    _build_light_evidence(evidence_root)

    compute_manifest(evidence_root)
    enforce_evidence_tier(evidence_root, "light")
    verify_manifest(evidence_root)

    _write(evidence_root / "unexpected.log", "orphan\n")

    with pytest.raises(EvidenceError) as exc:
        verify_manifest(evidence_root)

    assert exc.value.code == "EVIDENCE_ORPHAN_FILE"


def test_manifest_hash_mismatch_detected(tmp_path: Path) -> None:
    evidence_root = tmp_path / "evidence"
    _build_light_evidence(evidence_root)

    compute_manifest(evidence_root)
    _write(evidence_root / "meta.json", "{\"changed\":true}\n")

    with pytest.raises(EvidenceError) as exc:
        verify_manifest(evidence_root)

    assert exc.value.code == "EVIDENCE_HASH_MISMATCH"
