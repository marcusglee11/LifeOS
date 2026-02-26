"""Shadow agent capture — dispatch same task to shadow CLI agent, never gate.

Captures CLI agent output for comparison logging alongside the primary pipeline.
When provider is unavailable, writes a stub manifest. Never raises to caller.
"""
from __future__ import annotations

import logging
import shutil
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from runtime.util.atomic_write import atomic_write_json
from runtime.util.canonical import compute_sha256

logger = logging.getLogger(__name__)


@dataclass
class ShadowCaptureResult:
    run_id: str
    provider: str
    available: bool
    output_path: Optional[Path]
    output_hash: Optional[str]
    exit_code: Optional[int]
    latency_ms: Optional[int]
    error: Optional[str] = None


def _write_manifest(
    output_dir: Path,
    run_id: str,
    provider_name: str,
    *,
    stub: bool = False,
    reason: str = "",
    exit_code: Optional[int] = None,
    output_hash: Optional[str] = None,
    latency_ms: Optional[int] = None,
    error: Optional[str] = None,
) -> Path:
    """Write manifest.json for the shadow capture."""
    manifest = {
        "schema_version": "shadow_capture_v1",
        "run_id": run_id,
        "provider": provider_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "stub": stub,
    }
    if stub:
        manifest["reason"] = reason
    else:
        manifest["exit_code"] = exit_code
        manifest["output_hash"] = output_hash
        manifest["latency_ms"] = latency_ms
    if error:
        manifest["error"] = error

    manifest_path = output_dir / "manifest.json"
    atomic_write_json(manifest_path, manifest)
    return manifest_path


def _check_provider_available(provider_name: str) -> tuple[bool, str]:
    """Check if CLI provider is enabled and binary exists."""
    try:
        from runtime.agents.models import get_cli_provider_config
        cli_cfg = get_cli_provider_config(provider_name)
        if cli_cfg is None:
            return False, f"provider '{provider_name}' not configured"
        if not cli_cfg.enabled:
            return False, f"provider '{provider_name}' is disabled"
        if shutil.which(cli_cfg.binary) is None:
            return False, f"binary '{cli_cfg.binary}' not found on PATH"
        return True, ""
    except Exception as exc:
        return False, str(exc)


def capture_shadow_agent(
    run_id: str,
    task_payload: Dict[str, Any],
    repo_root: Path,
    provider_name: str = "claude_code",
    timeout_seconds: int = 300,
) -> ShadowCaptureResult:
    """Dispatch to shadow CLI agent. Never raises.

    If provider is unavailable (disabled, binary missing), writes a stub manifest.

    Args:
        run_id: Current run identifier.
        task_payload: Task specification to send to the agent.
        repo_root: Repository root path.
        provider_name: CLI provider to use (default: claude_code).
        timeout_seconds: Maximum execution time.

    Returns:
        ShadowCaptureResult with capture details.
    """
    output_dir = Path(repo_root) / "artifacts" / "shadow" / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        available, reason = _check_provider_available(provider_name)
        if not available:
            _write_manifest(
                output_dir, run_id, provider_name,
                stub=True,
                reason=reason or "shadow agent not configured",
            )
            return ShadowCaptureResult(
                run_id=run_id,
                provider=provider_name,
                available=False,
                output_path=output_dir / "manifest.json",
                output_hash=None,
                exit_code=None,
                latency_ms=None,
                error=reason or "shadow agent not configured",
            )

        # Dispatch via CLI
        from runtime.agents.cli_dispatch import (
            CLIProvider,
            CLIDispatchConfig,
            dispatch_cli_agent,
        )

        provider_enum = CLIProvider(provider_name)
        config = CLIDispatchConfig(
            provider=provider_enum,
            timeout_seconds=timeout_seconds,
        )
        prompt = task_payload.get("task", str(task_payload))

        result = dispatch_cli_agent(prompt=prompt, config=config, cwd=repo_root)

        # Write output to file
        output_path = output_dir / "output.txt"
        output_path.write_text(result.output, encoding="utf-8")
        output_hash = compute_sha256(result.output)

        _write_manifest(
            output_dir, run_id, provider_name,
            exit_code=result.exit_code,
            output_hash=output_hash,
            latency_ms=result.latency_ms,
        )

        return ShadowCaptureResult(
            run_id=run_id,
            provider=provider_name,
            available=True,
            output_path=output_path,
            output_hash=output_hash,
            exit_code=result.exit_code,
            latency_ms=result.latency_ms,
        )

    except Exception as exc:
        logger.warning("Shadow agent capture failed (run_id=%s): %s", run_id, exc)
        try:
            _write_manifest(
                output_dir, run_id, provider_name,
                stub=True,
                reason="capture_error",
                error=str(exc),
            )
        except Exception:
            pass
        return ShadowCaptureResult(
            run_id=run_id,
            provider=provider_name,
            available=False,
            output_path=None,
            output_hash=None,
            exit_code=None,
            latency_ms=None,
            error=str(exc),
        )
