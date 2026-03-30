"""
Tests for CLI Agent Dispatch module.

Validates subprocess spawning, timeout handling, partial result recovery,
and provider command construction — all with mocked subprocesses.
"""

import subprocess
from unittest.mock import patch

import pytest

from runtime.agents.cli_dispatch import (
    CLIDispatchConfig,
    CLIDispatchResult,
    CLIProvider,
    CLIProviderNotFound,
    _build_command,
    _resolve_binary,
    dispatch_cli_agent,
)

# ---------------------------------------------------------------------------
# CLIProvider enum
# ---------------------------------------------------------------------------


class TestCLIProvider:
    def test_values(self):
        assert CLIProvider.CODEX.value == "codex"
        assert CLIProvider.GEMINI.value == "gemini"
        assert CLIProvider.CLAUDE_CODE.value == "claude_code"

    def test_all_members(self):
        assert len(CLIProvider) == 3


# ---------------------------------------------------------------------------
# CLIDispatchConfig
# ---------------------------------------------------------------------------


class TestCLIDispatchConfig:
    def test_defaults(self):
        cfg = CLIDispatchConfig(provider=CLIProvider.CODEX)
        assert cfg.timeout_seconds == 300
        assert cfg.sandbox is True
        assert cfg.model == ""
        assert cfg.extra_args == ()

    def test_custom_values(self):
        cfg = CLIDispatchConfig(
            provider=CLIProvider.GEMINI,
            timeout_seconds=600,
            sandbox=False,
            model="gemini-3-pro",
            extra_args=("--verbose",),
        )
        assert cfg.provider == CLIProvider.GEMINI
        assert cfg.timeout_seconds == 600
        assert cfg.model == "gemini-3-pro"

    def test_invalid_timeout_rejected(self):
        with pytest.raises(ValueError, match="timeout_seconds must be positive"):
            CLIDispatchConfig(provider=CLIProvider.CODEX, timeout_seconds=0)

    def test_frozen(self):
        cfg = CLIDispatchConfig(provider=CLIProvider.CODEX)
        with pytest.raises(AttributeError):
            cfg.timeout_seconds = 999


# ---------------------------------------------------------------------------
# CLIDispatchResult
# ---------------------------------------------------------------------------


class TestCLIDispatchResult:
    def test_success_property(self):
        result = CLIDispatchResult(
            output="done",
            exit_code=0,
            latency_ms=100,
            provider=CLIProvider.CODEX,
            model="gpt-5.3-codex",
        )
        assert result.success is True

    def test_failure_exit_code(self):
        result = CLIDispatchResult(
            output="",
            exit_code=1,
            latency_ms=50,
            provider=CLIProvider.CODEX,
            model="",
        )
        assert result.success is False

    def test_partial_not_success(self):
        result = CLIDispatchResult(
            output="partial",
            exit_code=0,
            latency_ms=300000,
            provider=CLIProvider.CODEX,
            model="",
            partial=True,
        )
        assert result.success is False


# ---------------------------------------------------------------------------
# _resolve_binary
# ---------------------------------------------------------------------------


class TestResolveBinary:
    @patch("shutil.which", return_value="/usr/bin/codex")
    def test_codex_found(self, mock_which):
        assert _resolve_binary(CLIProvider.CODEX) == "/usr/bin/codex"
        mock_which.assert_called_with("codex")

    @patch("shutil.which", return_value="/usr/bin/gemini")
    def test_gemini_found(self, mock_which):
        assert _resolve_binary(CLIProvider.GEMINI) == "/usr/bin/gemini"
        mock_which.assert_called_with("gemini")

    @patch("shutil.which", return_value="/usr/bin/claude")
    def test_claude_code_found(self, mock_which):
        assert _resolve_binary(CLIProvider.CLAUDE_CODE) == "/usr/bin/claude"
        mock_which.assert_called_with("claude")

    @patch("shutil.which", return_value=None)
    def test_binary_not_found_raises(self, mock_which):
        with pytest.raises(CLIProviderNotFound, match="not found on PATH"):
            _resolve_binary(CLIProvider.CODEX)


# ---------------------------------------------------------------------------
# _build_command
# ---------------------------------------------------------------------------


class TestBuildCommand:
    def test_codex_basic(self):
        cfg = CLIDispatchConfig(provider=CLIProvider.CODEX)
        cmd = _build_command("/usr/bin/codex", CLIProvider.CODEX, "do stuff", cfg)
        assert cmd == ["/usr/bin/codex", "exec", "do stuff"]

    def test_codex_with_model(self):
        cfg = CLIDispatchConfig(provider=CLIProvider.CODEX, model="gpt-5.3-codex")
        cmd = _build_command("/usr/bin/codex", CLIProvider.CODEX, "do stuff", cfg)
        assert "--model" in cmd
        assert "gpt-5.3-codex" in cmd

    def test_codex_no_sandbox(self):
        cfg = CLIDispatchConfig(provider=CLIProvider.CODEX, sandbox=False)
        cmd = _build_command("/usr/bin/codex", CLIProvider.CODEX, "do stuff", cfg)
        assert "--full-auto" in cmd

    def test_gemini_basic(self):
        cfg = CLIDispatchConfig(provider=CLIProvider.GEMINI)
        cmd = _build_command("/usr/bin/gemini", CLIProvider.GEMINI, "analyze this", cfg)
        assert cmd == ["/usr/bin/gemini", "-p", "analyze this"]

    def test_gemini_with_model(self):
        cfg = CLIDispatchConfig(provider=CLIProvider.GEMINI, model="gemini-3-pro")
        cmd = _build_command("/usr/bin/gemini", CLIProvider.GEMINI, "analyze", cfg)
        assert "-m" in cmd
        assert "gemini-3-pro" in cmd

    def test_claude_code_basic(self):
        cfg = CLIDispatchConfig(provider=CLIProvider.CLAUDE_CODE)
        cmd = _build_command("/usr/bin/claude", CLIProvider.CLAUDE_CODE, "review code", cfg)
        assert cmd == ["/usr/bin/claude", "-p", "review code", "--output-format", "text"]

    def test_claude_code_with_model(self):
        cfg = CLIDispatchConfig(provider=CLIProvider.CLAUDE_CODE, model="claude-opus-4-6")
        cmd = _build_command("/usr/bin/claude", CLIProvider.CLAUDE_CODE, "review", cfg)
        assert "--model" in cmd
        assert "claude-opus-4-6" in cmd

    def test_extra_args_appended(self):
        cfg = CLIDispatchConfig(
            provider=CLIProvider.CODEX,
            extra_args=("--verbose", "--dry-run"),
        )
        cmd = _build_command("/usr/bin/codex", CLIProvider.CODEX, "task", cfg)
        assert cmd[-2:] == ["--verbose", "--dry-run"]


# ---------------------------------------------------------------------------
# dispatch_cli_agent (mocked subprocess)
# ---------------------------------------------------------------------------


class TestDispatchCLIAgent:
    @patch("runtime.agents.cli_dispatch._resolve_binary", return_value="/usr/bin/codex")
    @patch("subprocess.run")
    def test_successful_dispatch(self, mock_run, mock_resolve):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="Analysis complete:\n- File has 3 functions",
            stderr="",
        )
        cfg = CLIDispatchConfig(provider=CLIProvider.CODEX, model="gpt-5.3-codex")
        result = dispatch_cli_agent("describe runtime/engine.py", cfg)

        assert result.success is True
        assert result.exit_code == 0
        assert "Analysis complete" in result.output
        assert result.provider == CLIProvider.CODEX
        assert result.model == "gpt-5.3-codex"
        assert result.latency_ms >= 0
        assert result.partial is False

    @patch("runtime.agents.cli_dispatch._resolve_binary", return_value="/usr/bin/codex")
    @patch("subprocess.run")
    def test_nonzero_exit_captures_stderr(self, mock_run, mock_resolve):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=1,
            stdout="",
            stderr="Error: model not available",
        )
        cfg = CLIDispatchConfig(provider=CLIProvider.CODEX)
        result = dispatch_cli_agent("bad prompt", cfg)

        assert result.success is False
        assert result.exit_code == 1
        assert "model not available" in result.errors[0]

    @patch("runtime.agents.cli_dispatch._resolve_binary", return_value="/usr/bin/codex")
    @patch("subprocess.run")
    def test_timeout_returns_partial(self, mock_run, mock_resolve):
        exc = subprocess.TimeoutExpired(cmd=["codex"], timeout=10)
        exc.stdout = "Partial analysis:\n- Found 2 issues"
        mock_run.side_effect = exc
        cfg = CLIDispatchConfig(provider=CLIProvider.CODEX, timeout_seconds=10)
        result = dispatch_cli_agent("long task", cfg)

        assert result.success is False
        assert result.partial is True
        assert result.exit_code == -1
        assert "Partial analysis" in result.output
        assert any("Timeout" in e for e in result.errors)

    @patch("runtime.agents.cli_dispatch._resolve_binary", return_value="/usr/bin/codex")
    @patch("subprocess.run")
    def test_timeout_no_partial_output(self, mock_run, mock_resolve):
        exc = subprocess.TimeoutExpired(cmd=["codex"], timeout=10)
        exc.stdout = None
        mock_run.side_effect = exc
        cfg = CLIDispatchConfig(provider=CLIProvider.CODEX, timeout_seconds=10)
        result = dispatch_cli_agent("long task", cfg)

        assert result.partial is True
        assert result.output == ""

    @patch("shutil.which", return_value=None)
    def test_provider_not_found_raises(self, mock_which):
        cfg = CLIDispatchConfig(provider=CLIProvider.CODEX)
        with pytest.raises(CLIProviderNotFound):
            dispatch_cli_agent("anything", cfg)

    @patch("runtime.agents.cli_dispatch._resolve_binary", return_value="/usr/bin/gemini")
    @patch("subprocess.run")
    def test_gemini_dispatch(self, mock_run, mock_resolve):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="Security review: no issues found",
            stderr="",
        )
        cfg = CLIDispatchConfig(provider=CLIProvider.GEMINI, model="gemini-3-pro")
        result = dispatch_cli_agent("security review", cfg)

        assert result.success is True
        assert result.provider == CLIProvider.GEMINI
        assert "Security review" in result.output

    @patch("runtime.agents.cli_dispatch._resolve_binary", return_value="/usr/bin/claude")
    @patch("subprocess.run")
    def test_claude_code_dispatch(self, mock_run, mock_resolve):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="Synthesis complete",
            stderr="",
        )
        cfg = CLIDispatchConfig(provider=CLIProvider.CLAUDE_CODE, model="claude-opus-4-6")
        result = dispatch_cli_agent("synthesize findings", cfg)

        assert result.success is True
        assert result.provider == CLIProvider.CLAUDE_CODE

    @patch("runtime.agents.cli_dispatch._resolve_binary", return_value="/usr/bin/codex")
    @patch("subprocess.run")
    def test_cwd_passed_to_subprocess(self, mock_run, mock_resolve):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="ok",
            stderr="",
        )
        cfg = CLIDispatchConfig(provider=CLIProvider.CODEX)
        dispatch_cli_agent("task", cfg, cwd="/some/path")

        call_kwargs = mock_run.call_args
        assert call_kwargs.kwargs["cwd"] == "/some/path"

    @patch("runtime.agents.cli_dispatch._resolve_binary", return_value="/usr/bin/codex")
    @patch("subprocess.run")
    def test_env_passed_to_subprocess(self, mock_run, mock_resolve):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="ok",
            stderr="",
        )
        cfg = CLIDispatchConfig(provider=CLIProvider.CODEX)
        custom_env = {"MY_KEY": "value"}
        dispatch_cli_agent("task", cfg, env=custom_env)

        call_kwargs = mock_run.call_args
        assert call_kwargs.kwargs["env"] == custom_env
