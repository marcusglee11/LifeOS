"""Tests: CLI agent dispatch receipts (Phase 1B — Constitutional Compliance)."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from runtime.agents.cli_dispatch import (
    CLIDispatchConfig,
    CLIProvider,
    dispatch_cli_agent,
)
from runtime.receipts.invocation_receipt import (
    get_or_create_collector,
    reset_invocation_receipt_collectors,
)

_RUN_ID = "test-1b-dispatch"


@pytest.fixture(autouse=True)
def _reset():
    reset_invocation_receipt_collectors()
    yield
    reset_invocation_receipt_collectors()


def _proc(returncode=0, stdout="done", stderr=""):
    p = MagicMock(spec=subprocess.CompletedProcess)
    p.returncode = returncode
    p.stdout = stdout
    p.stderr = stderr
    return p


def _config(provider=CLIProvider.CODEX, timeout=10):
    return CLIDispatchConfig(provider=provider, timeout_seconds=timeout)


# ---------------------------------------------------------------------------
# 1B-1: Successful dispatch produces receipt
# ---------------------------------------------------------------------------


def test_success_produces_receipt():
    with (
        patch("runtime.agents.cli_dispatch._resolve_binary", return_value="/usr/bin/codex"),
        patch("runtime.agents.cli_dispatch._build_command", return_value=["codex", "exec", "task"]),
        patch("subprocess.run", return_value=_proc()),
    ):
        result = dispatch_cli_agent("task", _config(), run_id=_RUN_ID)

    assert result.exit_code == 0
    collector = get_or_create_collector(_RUN_ID)
    assert len(collector.receipts) == 1
    r = collector.receipts[0]
    assert r.provider_id == "codex"
    assert r.mode == "cli"
    assert r.exit_status == 0
    assert r.error is None


# ---------------------------------------------------------------------------
# 1B-2: Non-zero exit code records receipt with error
# ---------------------------------------------------------------------------


def test_failure_produces_receipt_with_error():
    with (
        patch("runtime.agents.cli_dispatch._resolve_binary", return_value="/usr/bin/codex"),
        patch("runtime.agents.cli_dispatch._build_command", return_value=["codex", "exec", "task"]),
        patch("subprocess.run", return_value=_proc(returncode=2, stdout="", stderr="build failed")),
    ):
        result = dispatch_cli_agent("task", _config(), run_id=_RUN_ID)

    assert result.exit_code == 2
    r = get_or_create_collector(_RUN_ID).receipts[0]
    assert r.exit_status == 2
    assert "build failed" in (r.error or "")


# ---------------------------------------------------------------------------
# 1B-3: Timeout produces receipt with exit_status=-1
# ---------------------------------------------------------------------------


def test_timeout_produces_receipt():
    with (
        patch("runtime.agents.cli_dispatch._resolve_binary", return_value="/usr/bin/codex"),
        patch("runtime.agents.cli_dispatch._build_command", return_value=["codex", "exec", "task"]),
        patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=["codex"], timeout=10)),
    ):
        result = dispatch_cli_agent("task", _config(timeout=10), run_id=_RUN_ID)

    assert result.exit_code == -1
    assert result.partial is True
    r = get_or_create_collector(_RUN_ID).receipts[0]
    assert r.exit_status == -1
    assert "timeout" in (r.error or "")


# ---------------------------------------------------------------------------
# 1B-4: Empty run_id → no receipt
# ---------------------------------------------------------------------------


def test_empty_run_id_no_receipt():
    with (
        patch("runtime.agents.cli_dispatch._resolve_binary", return_value="/usr/bin/codex"),
        patch("runtime.agents.cli_dispatch._build_command", return_value=["codex", "exec", "task"]),
        patch("subprocess.run", return_value=_proc()),
    ):
        dispatch_cli_agent("task", _config(), run_id="")

    # No collector created for this run
    collector = get_or_create_collector("no-such-id-xyz")
    assert len(collector.receipts) == 0


# ---------------------------------------------------------------------------
# 1B-5: Provider value is stored in receipt
# ---------------------------------------------------------------------------


def test_provider_stored_in_receipt():
    with (
        patch("runtime.agents.cli_dispatch._resolve_binary", return_value="/usr/bin/claude"),
        patch("runtime.agents.cli_dispatch._build_command", return_value=["claude", "-p", "task"]),
        patch("subprocess.run", return_value=_proc()),
    ):
        dispatch_cli_agent("task", _config(provider=CLIProvider.CLAUDE_CODE), run_id=_RUN_ID)

    r = get_or_create_collector(_RUN_ID).receipts[0]
    assert r.provider_id == "claude_code"
