"""Tests: COO invocation receipts (Phase 1A — Constitutional Compliance)."""
from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from runtime.orchestration.coo.invoke import InvocationError, invoke_coo_reasoning
from runtime.receipts.invocation_receipt import (
    get_or_create_collector,
    reset_invocation_receipt_collectors,
)
from runtime.util.canonical import compute_sha256


_RUN_ID = "test-run-1a"

_STUB_ENVELOPE = '{"status":"ok","result":{"payloads":[{"text":"schema_version: task_proposal.v1\\n"}]}}'


@pytest.fixture(autouse=True)
def _reset():
    reset_invocation_receipt_collectors()
    yield
    reset_invocation_receipt_collectors()


def _make_completed(returncode=0, stdout=_STUB_ENVELOPE, stderr=""):
    proc = MagicMock(spec=subprocess.CompletedProcess)
    proc.returncode = returncode
    proc.stdout = stdout
    proc.stderr = stderr
    return proc


# ---------------------------------------------------------------------------
# 1A-1: Successful invocation produces receipt
# ---------------------------------------------------------------------------

def test_success_produces_receipt():
    with patch("subprocess.run", return_value=_make_completed()):
        result = invoke_coo_reasoning(
            context={"backlog": []},
            mode="propose",
            repo_root=None,
            run_id=_RUN_ID,
        )

    collector = get_or_create_collector(_RUN_ID)
    assert len(collector.receipts) == 1
    r = collector.receipts[0]
    assert r.provider_id == "openclaw"
    assert r.mode == "cli"
    assert r.seat_id == "coo_propose"
    assert r.exit_status == 0
    assert r.schema_validation == "pass"
    assert r.error is None


# ---------------------------------------------------------------------------
# 1A-2: output_hash matches compute_sha256(stdout_text)
# ---------------------------------------------------------------------------

def test_receipt_output_hash_matches_content():
    with patch("subprocess.run", return_value=_make_completed()):
        invoke_coo_reasoning(
            context={}, mode="propose", repo_root=None, run_id=_RUN_ID,
        )

    r = get_or_create_collector(_RUN_ID).receipts[0]
    # The normalized text extracted from the envelope
    expected_text = "schema_version: task_proposal.v1\n"
    assert r.output_hash == compute_sha256(expected_text)


def test_chat_mode_uses_low_thinking():
    with patch("subprocess.run", return_value=_make_completed()) as mock_run:
        invoke_coo_reasoning(
            context={"message": "hello"},
            mode="chat",
            repo_root=None,
            run_id=_RUN_ID,
        )

    cmd = mock_run.call_args.kwargs["args"] if "args" in mock_run.call_args.kwargs else mock_run.call_args.args[0]
    thinking_index = cmd.index("--thinking")
    assert cmd[thinking_index + 1] == "low"


def test_non_chat_modes_keep_high_thinking():
    with patch("subprocess.run", return_value=_make_completed()) as mock_run:
        invoke_coo_reasoning(
            context={"backlog": []},
            mode="propose",
            repo_root=None,
            run_id=_RUN_ID,
        )

    cmd = mock_run.call_args.kwargs["args"] if "args" in mock_run.call_args.kwargs else mock_run.call_args.args[0]
    thinking_index = cmd.index("--thinking")
    assert cmd[thinking_index + 1] == "high"


# ---------------------------------------------------------------------------
# 1A-3: Non-zero exit code produces receipt with error, still raises
# ---------------------------------------------------------------------------

def test_bad_exit_produces_receipt_and_raises():
    with patch("subprocess.run", return_value=_make_completed(returncode=1, stdout="", stderr="boom")):
        with pytest.raises(InvocationError):
            invoke_coo_reasoning(
                context={}, mode="propose", repo_root=None, run_id=_RUN_ID,
            )

    collector = get_or_create_collector(_RUN_ID)
    assert len(collector.receipts) == 1
    r = collector.receipts[0]
    assert r.exit_status == 1
    assert "boom" in (r.error or "")


# ---------------------------------------------------------------------------
# 1A-4: Timeout produces receipt with exit_status=-1, still raises
# ---------------------------------------------------------------------------

def test_timeout_produces_receipt_and_raises():
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=["openclaw"], timeout=120)):
        with pytest.raises(InvocationError, match="timed out"):
            invoke_coo_reasoning(
                context={}, mode="propose", repo_root=None, run_id=_RUN_ID,
            )

    collector = get_or_create_collector(_RUN_ID)
    assert len(collector.receipts) == 1
    r = collector.receipts[0]
    assert r.exit_status == -1
    assert "timeout" in (r.error or "")


# ---------------------------------------------------------------------------
# 1A-5: Binary not found produces receipt, still raises
# ---------------------------------------------------------------------------

def test_binary_not_found_produces_receipt_and_raises():
    with patch("subprocess.run", side_effect=FileNotFoundError("openclaw")):
        with pytest.raises(InvocationError, match="not found"):
            invoke_coo_reasoning(
                context={}, mode="direct", repo_root=None, run_id=_RUN_ID,
            )

    collector = get_or_create_collector(_RUN_ID)
    assert len(collector.receipts) == 1
    r = collector.receipts[0]
    assert r.exit_status == -1
    assert r.seat_id == "coo_direct"


# ---------------------------------------------------------------------------
# 1A-6: Empty run_id → no receipt emitted (no-op)
# ---------------------------------------------------------------------------

def test_empty_run_id_no_receipt():
    with patch("subprocess.run", return_value=_make_completed()):
        invoke_coo_reasoning(
            context={}, mode="propose", repo_root=None, run_id="",
        )

    # No collector was created because run_id is empty
    collector = get_or_create_collector("no-such-run-id-xyz")
    assert len(collector.receipts) == 0


# ---------------------------------------------------------------------------
# 1A-7: JSON decode failure produces receipt with schema_validation=fail
# ---------------------------------------------------------------------------

def test_json_decode_failure_produces_receipt():
    with patch("subprocess.run", return_value=_make_completed(stdout="not json !!!")):
        with pytest.raises(InvocationError, match="not valid JSON"):
            invoke_coo_reasoning(
                context={}, mode="propose", repo_root=None, run_id=_RUN_ID,
            )

    r = get_or_create_collector(_RUN_ID).receipts[0]
    assert r.schema_validation == "fail"
    assert "JSON decode" in (r.error or "")
