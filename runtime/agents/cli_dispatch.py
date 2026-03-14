"""
CLI Agent Dispatch - Spawn CLI-based LLM agents as subprocesses.

Enables LifeOS to dispatch prompts to CLI agents (Codex, Gemini, Claude Code)
that have full tool use, file access, and sandbox capabilities — not just
REST API text completions.

Architecture note:
  - This module sits alongside opencode_client.py (REST API calls)
  - CLI dispatch is for heavyweight tasks (build, design review, security audit)
  - REST API path remains for lightweight single-turn completions
  - All outputs feed into the same AgentResponse/hash chain pipeline
"""

from __future__ import annotations

import enum
import logging
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from runtime.receipts.invocation_receipt import record_invocation_receipt

logger = logging.getLogger(__name__)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class CLIProvider(enum.Enum):
    """Supported CLI agent providers."""
    CODEX = "codex"
    GEMINI = "gemini"
    CLAUDE_CODE = "claude_code"


class CLIDispatchError(Exception):
    """Base exception for CLI dispatch failures."""
    pass


class CLIProviderNotFound(CLIDispatchError):
    """CLI binary not found on PATH."""
    pass


class CLIDispatchTimeout(CLIDispatchError):
    """CLI agent exceeded timeout."""
    pass


@dataclass(frozen=True)
class CLIDispatchConfig:
    """Configuration for a CLI agent dispatch."""
    provider: CLIProvider
    timeout_seconds: int = 300
    sandbox: bool = True
    model: str = ""
    extra_args: tuple[str, ...] = ()

    def __post_init__(self):
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")


@dataclass
class CLIDispatchResult:
    """Result from a CLI agent execution."""
    output: str
    exit_code: int
    latency_ms: int
    provider: CLIProvider
    model: str
    partial: bool = False
    errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return self.exit_code == 0 and not self.partial


# Provider → binary name mapping
_PROVIDER_BINARIES: dict[CLIProvider, str] = {
    CLIProvider.CODEX: "codex",
    CLIProvider.GEMINI: "gemini",
    CLIProvider.CLAUDE_CODE: "claude",
}


def _resolve_binary(provider: CLIProvider, binary_override: str = "") -> str:
    """Resolve CLI binary path, raising CLIProviderNotFound if absent."""
    binary = binary_override or _PROVIDER_BINARIES.get(provider)
    if binary is None:
        raise CLIProviderNotFound(f"Unknown provider: {provider}")
    path = shutil.which(binary)
    if path is None:
        raise CLIProviderNotFound(
            f"CLI binary '{binary}' not found on PATH for provider {provider.value}"
        )
    return path


def _build_command(
    binary: str,
    provider: CLIProvider,
    prompt: str,
    config: CLIDispatchConfig,
) -> list[str]:
    """
    Build the subprocess command for a CLI agent.

    Each provider has its own CLI interface:
      - codex exec "<prompt>"
      - gemini -p "<model>" (prompt via stdin)
      - claude -p "<prompt>" --output-format text
    """
    if provider == CLIProvider.CODEX:
        cmd = [binary, "exec"]
        if config.model:
            cmd.extend(["--model", config.model])
        if not config.sandbox:
            cmd.append("--full-auto")
        cmd.append(prompt)
        return cmd + list(config.extra_args)

    if provider == CLIProvider.GEMINI:
        cmd = [binary]
        if config.model:
            cmd.extend(["-m", config.model])
        cmd.extend(["-p", prompt])
        return cmd + list(config.extra_args)

    if provider == CLIProvider.CLAUDE_CODE:
        cmd = [binary, "-p", prompt, "--output-format", "text"]
        if config.model:
            cmd.extend(["--model", config.model])
        return cmd + list(config.extra_args)

    raise CLIDispatchError(f"No command template for provider: {provider.value}")


def dispatch_cli_agent(
    prompt: str,
    config: CLIDispatchConfig,
    cwd: Optional[str] = None,
    env: Optional[dict[str, str]] = None,
    binary_override: str = "",
    run_id: str = "",
) -> CLIDispatchResult:
    """
    Dispatch a prompt to a CLI-based LLM agent.

    Spawns the agent as a subprocess, captures output with timeout,
    and returns a structured result.

    Args:
        prompt: The prompt/task to send to the CLI agent.
        config: CLIDispatchConfig with provider, timeout, model, etc.
        cwd: Working directory for the subprocess (default: current dir).
        env: Optional environment variables to pass to subprocess.
        binary_override: Optional binary name to use instead of the default.
        run_id: Content-addressable run ID for receipt emission (empty = no receipt).

    Returns:
        CLIDispatchResult with output, exit code, latency, etc.

    Raises:
        CLIProviderNotFound: If the CLI binary is not on PATH.
        CLIDispatchError: On unexpected subprocess errors.
    """
    binary = _resolve_binary(config.provider, binary_override)
    cmd = _build_command(binary, config.provider, prompt, config)

    logger.info(
        "CLI dispatch: provider=%s model=%s timeout=%ds",
        config.provider.value,
        config.model or "default",
        config.timeout_seconds,
    )

    start = time.monotonic()
    start_ts = _utc_now()
    errors: list[str] = []

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=config.timeout_seconds,
            cwd=cwd,
            env=env,
        )
        elapsed_ms = int((time.monotonic() - start) * 1000)
        end_ts = _utc_now()

        output = result.stdout or ""
        if result.returncode != 0 and result.stderr:
            errors.append(result.stderr.strip())

        record_invocation_receipt(
            run_id=run_id,
            provider_id=config.provider.value,
            mode="cli",
            seat_id=config.provider.value,
            start_ts=start_ts,
            end_ts=end_ts,
            exit_status=result.returncode,
            output_content=output,
            error=errors[0] if errors else None,
        )

        return CLIDispatchResult(
            output=output,
            exit_code=result.returncode,
            latency_ms=elapsed_ms,
            provider=config.provider,
            model=config.model,
            partial=False,
            errors=errors,
        )

    except subprocess.TimeoutExpired as exc:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        end_ts = _utc_now()
        # Recover partial output if available
        partial_output = ""
        if exc.stdout:
            partial_output = exc.stdout if isinstance(exc.stdout, str) else exc.stdout.decode("utf-8", errors="replace")
        errors.append(f"Timeout after {config.timeout_seconds}s")

        record_invocation_receipt(
            run_id=run_id,
            provider_id=config.provider.value,
            mode="cli",
            seat_id=config.provider.value,
            start_ts=start_ts,
            end_ts=end_ts,
            exit_status=-1,
            output_content=partial_output,
            error=f"timeout after {config.timeout_seconds}s",
        )

        return CLIDispatchResult(
            output=partial_output,
            exit_code=-1,
            latency_ms=elapsed_ms,
            provider=config.provider,
            model=config.model,
            partial=True,
            errors=errors,
        )

    except FileNotFoundError:
        raise CLIProviderNotFound(
            f"CLI binary '{binary}' disappeared between resolve and exec"
        )

    except OSError as exc:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        raise CLIDispatchError(
            f"OS error spawning {config.provider.value}: {exc}"
        ) from exc
