"""Tests for shadow agent capture."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from runtime.agents.shadow_capture import (
    ShadowCaptureResult,
    capture_shadow_agent,
)


def test_capture_stub_when_provider_disabled(tmp_path):
    """Stub manifest written when provider is disabled."""
    with patch(
        "runtime.agents.shadow_capture._check_provider_available",
        return_value=(False, "provider 'claude_code' is disabled"),
    ):
        result = capture_shadow_agent(
            run_id="run_disabled",
            task_payload={"task": "test task"},
            repo_root=tmp_path,
            provider_name="claude_code",
        )

    assert result.available is False
    assert result.error is not None
    assert "disabled" in result.error

    manifest_path = tmp_path / "artifacts" / "shadow" / "run_disabled" / "manifest.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text("utf-8"))
    assert manifest["stub"] is True
    assert manifest["schema_version"] == "shadow_capture_v1"


def test_capture_stub_when_binary_missing(tmp_path):
    """Stub manifest when provider enabled but binary not found."""
    with patch(
        "runtime.agents.shadow_capture._check_provider_available",
        return_value=(False, "binary 'claude' not found on PATH"),
    ):
        result = capture_shadow_agent(
            run_id="run_no_binary",
            task_payload={"task": "test"},
            repo_root=tmp_path,
        )

    assert result.available is False
    assert "not found" in result.error

    manifest_path = tmp_path / "artifacts" / "shadow" / "run_no_binary" / "manifest.json"
    assert manifest_path.exists()


def test_capture_with_available_provider(tmp_path):
    """Full capture when provider is available."""
    mock_result = MagicMock()
    mock_result.output = "shadow agent output"
    mock_result.exit_code = 0
    mock_result.latency_ms = 1500

    with patch(
        "runtime.agents.shadow_capture._check_provider_available",
        return_value=(True, ""),
    ), patch(
        "runtime.agents.cli_dispatch.dispatch_cli_agent",
        return_value=mock_result,
    ):
        result = capture_shadow_agent(
            run_id="run_available",
            task_payload={"task": "build something"},
            repo_root=tmp_path,
        )

    assert result.available is True
    assert result.exit_code == 0
    assert result.output_hash is not None
    assert result.latency_ms == 1500

    # Verify output file written
    output_path = tmp_path / "artifacts" / "shadow" / "run_available" / "output.txt"
    assert output_path.exists()
    assert output_path.read_text("utf-8") == "shadow agent output"

    manifest_path = tmp_path / "artifacts" / "shadow" / "run_available" / "manifest.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text("utf-8"))
    assert manifest["stub"] is False
    assert manifest["exit_code"] == 0


def test_capture_error_handling(tmp_path):
    """Capture handles exceptions gracefully."""
    with patch(
        "runtime.agents.shadow_capture._check_provider_available",
        side_effect=RuntimeError("boom"),
    ):
        result = capture_shadow_agent(
            run_id="run_error",
            task_payload={"task": "test"},
            repo_root=tmp_path,
        )

    assert result.available is False
    assert "boom" in result.error


def test_manifest_schema(tmp_path):
    """Manifest has correct schema_version and required fields."""
    with patch(
        "runtime.agents.shadow_capture._check_provider_available",
        return_value=(False, "provider disabled for test"),
    ):
        capture_shadow_agent(
            run_id="run_schema",
            task_payload={"task": "test"},
            repo_root=tmp_path,
        )

    manifest_path = tmp_path / "artifacts" / "shadow" / "run_schema" / "manifest.json"
    manifest = json.loads(manifest_path.read_text("utf-8"))
    assert manifest["schema_version"] == "shadow_capture_v1"
    assert "run_id" in manifest
    assert "provider" in manifest
    assert "timestamp" in manifest
    assert "stub" in manifest
