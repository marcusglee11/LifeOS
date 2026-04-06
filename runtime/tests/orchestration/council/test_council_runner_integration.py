"""Integration tests for the council runner hardening changes.

Tests:
- blocked_provider fast-exit + provider_health.json written before LLM calls
- happy-path dry-run emits run_manifest.json and run_log.json
- malformed seat output triggers exactly one retry then fails cleanly
- close_build.py stage banner ordering
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[4]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_runner(args: list[str], env: dict | None = None) -> subprocess.CompletedProcess:
    """Run run_council_review.py with the given args."""
    cmd = [sys.executable, str(REPO_ROOT / "scripts" / "workflow" / "run_council_review.py")] + args
    merged_env = {**os.environ, **(env or {})}
    return subprocess.run(cmd, capture_output=True, text=True, env=merged_env, cwd=REPO_ROOT)


def _run_close_build(args: list[str]) -> subprocess.CompletedProcess:
    """Run close_build.py with the given args."""
    cmd = [sys.executable, str(REPO_ROOT / "scripts" / "workflow" / "close_build.py")] + args
    return subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_ROOT)


def _minimal_ccp(tmp_path: Path) -> Path:
    ccp = {
        "header": {
            "aur_id": "AUR-INTEGRATION-TEST",
            "aur_type": "code",
            "change_class": "new",
            "blast_radius": "module",
            "reversibility": "moderate",
            "uncertainty": "medium",
            "touches": ["runtime_core"],
            "safety_critical": False,
            "run_type": "review",
            "model_plan_v1": {
                "primary": "openrouter/moonshotai/kimi-k2.5",
                "independent": "openrouter/z-ai/glm-5",
                "seat_overrides": {
                    "Chair": "openrouter/minimax/minimax-m2.5",
                },
            },
        },
        "sections": {
            "objective": "Integration test: verify runner hardening.",
            "scope": "Integration test scope.",
            "constraints": ["No external calls in dry-run."],
            "artifacts": [
                {"id": "runtime/tests/", "type": "modified", "description": "Integration test artifacts"},
            ],
        },
    }
    ccp_path = tmp_path / "test.ccp.yaml"
    ccp_path.write_text(yaml.dump(ccp), encoding="utf-8")
    return ccp_path


# ---------------------------------------------------------------------------
# 1. blocked_provider fast-exit
# ---------------------------------------------------------------------------


def test_blocked_provider_exits_2_and_writes_provider_health(tmp_path):
    """With invalid API key, runner exits 2 and writes provider_health.json."""
    ccp_path = _minimal_ccp(tmp_path)
    archive_dir = tmp_path / "archive"

    result = _run_runner(
        ["--ccp", str(ccp_path), "--archive-dir", str(archive_dir)],
        env={"ZEN_REVIEWER_KEY": ""},  # force auth failure
    )

    assert result.returncode == 2, f"Expected exit 2, got {result.returncode}\n{result.stderr}"

    health_file = archive_dir / "provider_health.json"
    assert health_file.exists(), "provider_health.json must exist after blocked_provider"

    health = json.loads(health_file.read_text())
    assert isinstance(health, dict)
    # At least one entry should be unavailable
    statuses = {v.get("status") for v in health.values()}
    assert "provider_unavailable" in statuses

    # run_manifest.json should also exist
    assert (archive_dir / "run_manifest.json").exists(), "run_manifest.json must exist even on block"

    # No live_result.json — no LLM calls were made
    assert not (archive_dir / "live_result.json").exists(), "live_result.json must not exist on preflight block"


# ---------------------------------------------------------------------------
# 2. Happy-path dry-run emits all required artifacts
# ---------------------------------------------------------------------------


def test_dry_run_emits_run_manifest(tmp_path):
    """Dry-run with valid env should emit run_manifest.json and run_log.json."""
    ccp_path = _minimal_ccp(tmp_path)
    archive_dir = tmp_path / "archive"

    result = _run_runner(
        ["--ccp", str(ccp_path), "--dry-run", "--archive-dir", str(archive_dir)],
        env={"ZEN_REVIEWER_KEY": "test-key-for-dry-run"},
    )

    assert result.returncode == 0, f"Dry-run failed:\n{result.stdout}\n{result.stderr}"

    manifest_path = archive_dir / "run_manifest.json"
    assert manifest_path.exists()

    manifest = json.loads(manifest_path.read_text())
    assert manifest["seat_map"], "seat_map must be populated"
    assert manifest["prompt_hashes"], "prompt_hashes must be populated"
    assert manifest["preflight_timeout_seconds"] > 0
    assert manifest["seat_timeout_seconds"] > 0

    run_log_path = archive_dir / "run_log.json"
    assert run_log_path.exists()
    log = json.loads(run_log_path.read_text())
    stages = [entry["stage"] for entry in log]
    assert "init" in stages
    assert "preflight" in stages


def test_dry_run_honors_declared_carry_forward_models(tmp_path):
    """Declared carry-forward providers must bypass preflight blocking."""
    ccp_path = _minimal_ccp(tmp_path)
    ccp = yaml.safe_load(ccp_path.read_text(encoding="utf-8"))
    header = ccp["header"]
    header["carry_forward_allowed"] = True
    header["carry_forward_models"] = [
        "openrouter/moonshotai/kimi-k2.5",
        "openrouter/z-ai/glm-5",
        "openrouter/minimax/minimax-m2.5",
    ]
    ccp_path.write_text(yaml.dump(ccp), encoding="utf-8")

    archive_dir = tmp_path / "archive"
    result = _run_runner(
        ["--ccp", str(ccp_path), "--dry-run", "--archive-dir", str(archive_dir)],
        env={"ZEN_REVIEWER_KEY": ""},
    )

    assert result.returncode == 0, f"Dry-run failed:\n{result.stdout}\n{result.stderr}"
    assert (archive_dir / "provider_health.json").exists()
    assert (archive_dir / "run_manifest.json").exists()


# ---------------------------------------------------------------------------
# 3. Malformed seat output: one retry then seat_schema_invalid
# ---------------------------------------------------------------------------


def test_seat_output_parser_retry_exactly_once():
    """Parser issues exactly one correction retry, then marks schema_invalid."""
    from runtime.orchestration.council.models import SeatFailureClass
    from runtime.orchestration.council.seat_output_parser import parse_seat_output

    bad_output = "verdict: BadValue"  # missing required fields; invalid verdict

    retry_count = [0]

    def counting_retry(raw: str, error_ctx: str) -> str:
        retry_count[0] += 1
        return raw  # still bad

    result = parse_seat_output(bad_output, seat_name="Architecture", retry_fn=counting_retry)
    assert retry_count[0] == 1, "Exactly one retry must be issued"
    assert result.provider_status == SeatFailureClass.seat_schema_invalid.value


# ---------------------------------------------------------------------------
# 4. close_build.py stage banner ordering
# ---------------------------------------------------------------------------


def test_close_build_json_mode_produces_single_blob(tmp_path):
    """--json mode must produce a parseable JSON blob, not interleaved output."""
    result = _run_close_build(["--dry-run", "--json", "--repo-root", str(REPO_ROOT)])
    # Must produce valid JSON on stdout
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        pytest.fail(f"close_build --json produced non-JSON stdout: {exc}\n{result.stdout[:500]}")

    assert "exit_code" in data
    assert "stdout" in data
    assert "ok" in data


def test_close_build_streaming_mode_no_json_blob(tmp_path):
    """Without --json, output must NOT be a top-level JSON blob."""
    result = _run_close_build(["--dry-run", "--repo-root", str(REPO_ROOT)])
    # If it happens to produce empty output (e.g. closure_pack not installed),
    # that's still fine — we just verify it's not a JSON blob.
    if result.stdout.strip():
        try:
            data = json.loads(result.stdout)
            # If it parsed as JSON, it should NOT have the blob keys from --json mode
            assert "exit_code" not in data or "ok" not in data, (
                "Streaming mode must not emit the --json structured blob"
            )
        except json.JSONDecodeError:
            pass  # Expected: streaming output is not a JSON blob
