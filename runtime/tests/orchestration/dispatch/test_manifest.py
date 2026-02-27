"""Tests for RunManifest append-only JSONL canonical manifest."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from runtime.orchestration.dispatch.manifest import RunManifest, MANIFEST_RELATIVE_PATH


def test_append_and_read(tmp_path):
    manifest = RunManifest(tmp_path)
    manifest.append({"order_id": "o1", "outcome": "SUCCESS"})
    manifest.append({"order_id": "o2", "outcome": "CLEAN_FAIL"})

    entries = manifest.read_all()
    assert len(entries) == 2
    assert entries[0]["order_id"] == "o1"
    assert entries[0]["outcome"] == "SUCCESS"
    assert entries[1]["order_id"] == "o2"


def test_manifest_path(tmp_path):
    manifest = RunManifest(tmp_path)
    assert manifest.path == tmp_path / MANIFEST_RELATIVE_PATH


def test_manifest_creates_parent_dirs(tmp_path):
    deep_root = tmp_path / "nested" / "repo"
    manifest = RunManifest(deep_root)
    manifest.append({"test": "entry"})
    assert manifest.path.exists()


def test_read_empty_returns_empty(tmp_path):
    manifest = RunManifest(tmp_path)
    assert manifest.read_all() == []


def test_entries_have_recorded_at(tmp_path):
    manifest = RunManifest(tmp_path)
    manifest.append({"order_id": "o1"})
    entries = manifest.read_all()
    assert "recorded_at" in entries[0]


def test_append_is_jsonl(tmp_path):
    manifest = RunManifest(tmp_path)
    manifest.append({"k": "v1"})
    manifest.append({"k": "v2"})

    lines = manifest.path.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 2
    for line in lines:
        parsed = json.loads(line)
        assert isinstance(parsed, dict)


def test_read_tolerates_corrupt_lines(tmp_path):
    manifest = RunManifest(tmp_path)
    manifest.append({"order_id": "good"})

    # Manually inject a corrupt line
    with open(manifest.path, "a", encoding="utf-8") as f:
        f.write("NOT JSON\n")

    manifest.append({"order_id": "also_good"})

    entries = manifest.read_all()
    # Should have 2 valid entries, skipping the corrupt one
    assert len(entries) == 2
    ids = {e["order_id"] for e in entries}
    assert ids == {"good", "also_good"}
