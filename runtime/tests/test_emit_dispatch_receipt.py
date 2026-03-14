"""Tests: emit_dispatch_receipt.py produces valid receipt (Phase 1C)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


_SCRIPT = Path(__file__).parents[2] / "scripts" / "workflow" / "emit_dispatch_receipt.py"
# Actual worktree/repo root where `runtime` package lives
_PYTHON_ROOT = Path(__file__).parents[2]


def _run(tmp_path: Path, topic: str = "test-topic", exit_code: int = 0) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--topic", topic,
            "--worktree", str(tmp_path / "worktrees" / topic),
            "--exit-code", str(exit_code),
            "--repo-root", str(tmp_path),
            "--python-root", str(_PYTHON_ROOT),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )


# ---------------------------------------------------------------------------
# 1C-1: Successful run produces receipt index file
# ---------------------------------------------------------------------------

def test_emits_receipt_index(tmp_path: Path):
    result = _run(tmp_path)
    assert result.returncode == 0, result.stderr

    receipts_dir = tmp_path / "artifacts" / "receipts"
    index_files = list(receipts_dir.rglob("index.json"))
    assert len(index_files) == 1, f"Expected 1 index.json, found: {index_files}"

    index = json.loads(index_files[0].read_text())
    assert index["receipt_count"] == 1
    assert index["receipts"][0]["provider_id"] == "codex"
    assert index["receipts"][0]["mode"] == "cli"
    assert index["receipts"][0]["exit_status"] == 0


# ---------------------------------------------------------------------------
# 1C-2: Non-zero exit records error in receipt
# ---------------------------------------------------------------------------

def test_failure_exit_code_recorded(tmp_path: Path):
    result = _run(tmp_path, exit_code=1)
    assert result.returncode == 0, result.stderr  # script itself should succeed

    index_file = next((tmp_path / "artifacts" / "receipts").rglob("index.json"))
    index = json.loads(index_file.read_text())
    receipt = index["receipts"][0]
    assert receipt["exit_status"] == 1
    assert receipt["error"] is not None


# ---------------------------------------------------------------------------
# 1C-3: Receipt schema_version is consistent with invocation_index_v1
# ---------------------------------------------------------------------------

def test_receipt_schema_version(tmp_path: Path):
    _run(tmp_path)
    index_file = next((tmp_path / "artifacts" / "receipts").rglob("index.json"))
    index = json.loads(index_file.read_text())
    assert index["schema_version"] == "invocation_index_v1"


# ---------------------------------------------------------------------------
# 1C-4: seat_id encodes topic slug
# ---------------------------------------------------------------------------

def test_seat_id_encodes_topic(tmp_path: Path):
    _run(tmp_path, topic="my-feature")
    index_file = next((tmp_path / "artifacts" / "receipts").rglob("index.json"))
    index = json.loads(index_file.read_text())
    assert "my-feature" in index["receipts"][0]["seat_id"]
