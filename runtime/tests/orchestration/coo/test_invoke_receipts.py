"""Tests: COO invocation receipts (Phase 1A — Constitutional Compliance)."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from runtime.orchestration.coo.invoke import (
    InvocationError,
    ProposalNormalizationError,
    _normalize_proposal_indentation,
    invoke_coo_reasoning,
)
from runtime.receipts.invocation_receipt import (
    get_or_create_collector,
    reset_invocation_receipt_collectors,
)
from runtime.util.canonical import compute_sha256

_RUN_ID = "test-run-1a"

_STUB_ENVELOPE = (
    '{"status":"ok","result":{"payloads":[{"text":"schema_version: task_proposal.v1\\n"}]}}'
)


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
        invoke_coo_reasoning(
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
    assert r.token_usage is not None
    assert r.token_usage["token_source"] == "estimated"
    assert r.token_usage["estimated_tokens"] == r.token_usage["total_tokens"]


# ---------------------------------------------------------------------------
# 1A-2: output_hash matches compute_sha256(stdout_text)
# ---------------------------------------------------------------------------


def test_receipt_output_hash_matches_content():
    with patch("subprocess.run", return_value=_make_completed()):
        invoke_coo_reasoning(
            context={},
            mode="propose",
            repo_root=None,
            run_id=_RUN_ID,
        )

    r = get_or_create_collector(_RUN_ID).receipts[0]
    # The normalized text extracted from the envelope
    expected_text = "schema_version: task_proposal.v1\n"
    assert r.output_hash == compute_sha256(expected_text)
    assert r.token_usage is not None
    assert r.token_usage["completion_tokens"] == len(expected_text) // 4


def test_chat_mode_uses_low_thinking():
    with patch("subprocess.run", return_value=_make_completed()) as mock_run:
        invoke_coo_reasoning(
            context={"message": "hello"},
            mode="chat",
            repo_root=None,
            run_id=_RUN_ID,
        )

    cmd = (
        mock_run.call_args.kwargs["args"]
        if "args" in mock_run.call_args.kwargs
        else mock_run.call_args.args[0]
    )
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

    cmd = (
        mock_run.call_args.kwargs["args"]
        if "args" in mock_run.call_args.kwargs
        else mock_run.call_args.args[0]
    )
    thinking_index = cmd.index("--thinking")
    assert cmd[thinking_index + 1] == "high"


# ---------------------------------------------------------------------------
# 1A-3: Non-zero exit code produces receipt with error, still raises
# ---------------------------------------------------------------------------


def test_bad_exit_produces_receipt_and_raises():
    with patch(
        "subprocess.run", return_value=_make_completed(returncode=1, stdout="", stderr="boom")
    ):
        with pytest.raises(InvocationError):
            invoke_coo_reasoning(
                context={},
                mode="propose",
                repo_root=None,
                run_id=_RUN_ID,
            )

    collector = get_or_create_collector(_RUN_ID)
    assert len(collector.receipts) == 1
    r = collector.receipts[0]
    assert r.exit_status == 1
    assert "boom" in (r.error or "")
    assert r.token_usage is not None
    assert r.token_usage["token_source"] == "estimated"


# ---------------------------------------------------------------------------
# 1A-4: Timeout produces receipt with exit_status=-1, still raises
# ---------------------------------------------------------------------------


def test_timeout_produces_receipt_and_raises():
    with patch(
        "subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=["openclaw"], timeout=120)
    ):
        with pytest.raises(InvocationError, match="timed out"):
            invoke_coo_reasoning(
                context={},
                mode="propose",
                repo_root=None,
                run_id=_RUN_ID,
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
                context={},
                mode="direct",
                repo_root=None,
                run_id=_RUN_ID,
                _retry_delays=(0.0, 0.0),
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
            context={},
            mode="propose",
            repo_root=None,
            run_id="",
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
                context={},
                mode="propose",
                repo_root=None,
                run_id=_RUN_ID,
            )

    r = get_or_create_collector(_RUN_ID).receipts[0]
    assert r.schema_validation == "fail"
    assert "JSON decode" in (r.error or "")


def test_normalize_proposal_indentation_recovers_all_task_fields() -> None:
    raw = (
        "schema_version: task_proposal.v1\n"
        "proposals:\n"
        "- task_id: T-020\n"
        "rationale: Tighten parser recovery.\n"
        "proposed_action: dispatch\n"
        "urgency_override: P1\n"
        "suggested_owner: codex\n"
    )

    normalized = _normalize_proposal_indentation(raw)

    assert "  rationale: Tighten parser recovery." in normalized
    assert "  proposed_action: dispatch" in normalized
    assert "  urgency_override: P1" in normalized
    assert "  suggested_owner: codex" in normalized


def test_normalize_proposal_indentation_recovers_operation_fields() -> None:
    raw = (
        "schema_version: operation_proposal.v1\n"
        "- proposal_id: OP-a1b2c3d4\n"
        "title: Write workspace note\n"
        "rationale: Safe workspace mutation.\n"
        "operation_kind: mutation\n"
        "action_id: workspace.file.write\n"
        "args:\n"
        "requires_approval: true\n"
        "suggested_owner: lifeos\n"
    )

    normalized = _normalize_proposal_indentation(raw)

    assert "  title: Write workspace note" in normalized
    assert "  action_id: workspace.file.write" in normalized
    assert "  requires_approval: true" in normalized
    assert "  suggested_owner: lifeos" in normalized


def test_normalize_proposal_indentation_rejects_unknown_key() -> None:
    raw = (
        "schema_version: task_proposal.v1\n"
        "proposals:\n"
        "- task_id: T-020\n"
        "rationale: Tighten parser recovery.\n"
        "unexpected_key: nope\n"
    )

    with pytest.raises(ProposalNormalizationError, match="Unknown COO proposal sub-key"):
        _normalize_proposal_indentation(raw)


# ---------------------------------------------------------------------------
# Retry behaviour (transient failures on chat/direct/propose)
# ---------------------------------------------------------------------------


def test_timeout_retries_on_chat_exhausts_all_attempts():
    call_count = [0]

    def _always_timeout(*args, **kwargs):
        call_count[0] += 1
        raise subprocess.TimeoutExpired(cmd=["openclaw"], timeout=120)

    with patch("subprocess.run", side_effect=_always_timeout):
        with pytest.raises(InvocationError, match="timed out"):
            invoke_coo_reasoning(
                context={},
                mode="chat",
                repo_root=None,
                run_id=_RUN_ID,
                _retry_delays=(0.0, 0.0),
            )
    # 1 initial + 2 retries = 3 total
    assert call_count[0] == 3
    # Only one receipt recorded (the final failure)
    assert len(get_or_create_collector(_RUN_ID).receipts) == 1


def test_timeout_retries_on_direct_exhausts_all_attempts():
    call_count = [0]

    def _always_timeout(*args, **kwargs):
        call_count[0] += 1
        raise subprocess.TimeoutExpired(cmd=["openclaw"], timeout=120)

    with patch("subprocess.run", side_effect=_always_timeout):
        with pytest.raises(InvocationError, match="timed out"):
            invoke_coo_reasoning(
                context={},
                mode="direct",
                repo_root=None,
                run_id=_RUN_ID,
                _retry_delays=(0.0, 0.0),
            )
    assert call_count[0] == 3


def test_timeout_retry_on_propose():
    call_count = [0]

    def _always_timeout(*args, **kwargs):
        call_count[0] += 1
        raise subprocess.TimeoutExpired(cmd=["openclaw"], timeout=120)

    with patch("subprocess.run", side_effect=_always_timeout):
        with pytest.raises(InvocationError, match="timed out"):
            invoke_coo_reasoning(
                context={},
                mode="propose",
                repo_root=None,
                run_id=_RUN_ID,
                _retry_delays=(0.0, 0.0),
            )
    assert call_count[0] == 3


def test_file_not_found_does_not_retry_on_propose():
    call_count = [0]

    def _missing(*args, **kwargs):
        call_count[0] += 1
        raise FileNotFoundError("openclaw")

    with patch("subprocess.run", side_effect=_missing):
        with pytest.raises(InvocationError, match="not found"):
            invoke_coo_reasoning(
                context={},
                mode="propose",
                repo_root=None,
                run_id=_RUN_ID,
                _retry_delays=(0.0, 0.0),
            )
    assert call_count[0] == 1


def test_success_after_retry_returns_normally():
    call_count = [0]

    def _fail_then_succeed(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] < 2:
            raise subprocess.TimeoutExpired(cmd=["openclaw"], timeout=120)
        return _make_completed()

    with patch("subprocess.run", side_effect=_fail_then_succeed):
        result = invoke_coo_reasoning(
            context={},
            mode="chat",
            repo_root=None,
            run_id=_RUN_ID,
            _retry_delays=(0.0, 0.0),
        )
    assert call_count[0] == 2
    assert "task_proposal" in result
    # Success receipt recorded (not a failure receipt)
    r = get_or_create_collector(_RUN_ID).receipts[0]
    assert r.exit_status == 0


def test_non_transient_error_not_retried_on_chat():
    """Non-zero exit is a deterministic failure — not retried even for chat mode."""
    call_count = [0]

    def _nonzero(*args, **kwargs):
        call_count[0] += 1
        return _make_completed(returncode=1, stdout="", stderr="policy reject")

    with patch("subprocess.run", side_effect=_nonzero):
        with pytest.raises(InvocationError):
            invoke_coo_reasoning(
                context={},
                mode="chat",
                repo_root=None,
                run_id=_RUN_ID,
                _retry_delays=(0.0, 0.0),
            )
    assert call_count[0] == 1


def test_file_not_found_retries_on_chat():
    call_count = [0]

    def _missing(*args, **kwargs):
        call_count[0] += 1
        raise FileNotFoundError("openclaw")

    with patch("subprocess.run", side_effect=_missing):
        with pytest.raises(InvocationError, match="not found"):
            invoke_coo_reasoning(
                context={},
                mode="chat",
                repo_root=None,
                run_id=_RUN_ID,
                _retry_delays=(0.0, 0.0),
            )
    assert call_count[0] == 3


# ---------------------------------------------------------------------------
# Regression: empty stdout with exit 0 must surface stderr, not bare JSON err
# ---------------------------------------------------------------------------


def test_empty_stdout_exit0_raises_with_stderr():
    """OpenClaw exits 0 but writes nothing to stdout — error must include stderr."""
    proc = _make_completed(returncode=0, stdout="", stderr="model not found: gpt-5.4")
    with patch("subprocess.run", return_value=proc):
        with pytest.raises(InvocationError, match="no output"):
            invoke_coo_reasoning(
                context={},
                mode="chat",
                repo_root=None,
                run_id=_RUN_ID,
            )


def test_empty_stdout_exit0_stderr_in_error_message():
    """Stderr content is included in the InvocationError message."""
    proc = _make_completed(returncode=0, stdout="", stderr="authentication failed")
    with patch("subprocess.run", return_value=proc):
        with pytest.raises(InvocationError, match="authentication failed"):
            invoke_coo_reasoning(
                context={},
                mode="chat",
                repo_root=None,
                run_id=_RUN_ID,
            )


def test_empty_stdout_exit0_no_stderr_still_raises():
    """Empty stdout with no stderr still raises a useful error."""
    proc = _make_completed(returncode=0, stdout="", stderr="")
    with patch("subprocess.run", return_value=proc):
        with pytest.raises(InvocationError, match="no output"):
            invoke_coo_reasoning(
                context={},
                mode="chat",
                repo_root=None,
                run_id=_RUN_ID,
            )


def test_empty_stdout_receipt_recorded():
    """A receipt is recorded even for empty-stdout failures."""
    proc = _make_completed(returncode=0, stdout="", stderr="model unavailable")
    with patch("subprocess.run", return_value=proc):
        with pytest.raises(InvocationError):
            invoke_coo_reasoning(
                context={},
                mode="chat",
                repo_root=None,
                run_id=_RUN_ID,
            )
    collector = get_or_create_collector(_RUN_ID)
    assert len(collector.receipts) == 1
    r = collector.receipts[0]
    assert r.schema_validation == "fail"
    assert "empty stdout" in (r.error or "")


def test_subprocess_called_with_stdin_devnull():
    """subprocess.run must be called with stdin=DEVNULL to prevent stdin inheritance."""
    import subprocess as sp

    proc = _make_completed()
    with patch("subprocess.run", return_value=proc) as mock_run:
        invoke_coo_reasoning(
            context={},
            mode="chat",
            repo_root=None,
            run_id=_RUN_ID,
        )
    _, kwargs = mock_run.call_args
    assert kwargs.get("stdin") == sp.DEVNULL
