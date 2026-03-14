"""Thin adapter for invoking the live OpenClaw COO agent."""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from runtime.receipts.invocation_receipt import record_invocation_receipt
from runtime.util.canonical import compute_sha256


class InvocationError(RuntimeError):
    """Raised when the OpenClaw subprocess fails, times out, or returns unusable output."""


# Sub-keys that appear in proposals list items and must be indented 2 spaces.
_PROPOSALS_SUB_KEYS = frozenset({
    "rationale",
    "proposed_action",
    "urgency_override",
    "suggested_owner",
})


def _normalize_proposal_indentation(text: str) -> str:
    """Normalize proposals YAML so sub-keys are indented under their list items.

    The live COO sometimes outputs proposals with sub-keys at column 0:
      proposals:
      - task_id: T-001
      rationale: "..."          <- should be indented by 2 spaces

    This normalizer adds the missing indentation so yaml.safe_load() can parse it.
    """
    lines = text.split("\n")
    result: list[str] = []
    in_item = False

    for line in lines:
        if line.startswith("- task_id:") or line.startswith("-task_id:"):
            in_item = True
            result.append(line)
            continue

        if in_item and line and not line.startswith(" "):
            key = line.split(":")[0].strip().lstrip("- ")
            if key in _PROPOSALS_SUB_KEYS:
                result.append("  " + line)
                continue
            else:
                in_item = False

        result.append(line)

    return "\n".join(result)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def invoke_coo_reasoning(
    context: dict,
    mode: str,
    repo_root: Path,
    timeout_s: int = 120,
    run_id: str = "",
) -> str:
    """
    Invoke the live OpenClaw COO with the given context.

    Returns raw COO output text (YAML body).
    Raises InvocationError on subprocess failure or timeout.

    :param context: Context dict to pass as the message body (serialized to JSON).
    :param mode: "propose" | "direct" — included in context for COO routing.
    :param repo_root: Repository root path (unused in CLI invocation; kept for future SDK use).
    :param timeout_s: Subprocess timeout in seconds.
    :param run_id: Content-addressable run ID for receipt emission (empty = no receipt).
    """
    payload = dict(context)
    payload["mode"] = mode

    message = json.dumps(payload, sort_keys=True)

    cmd = [
        "openclaw",
        "agent",
        "--agent", "main",
        "--message", message,
        "--json",
    ]

    start_ts = _utc_now()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired as exc:
        end_ts = _utc_now()
        record_invocation_receipt(
            run_id=run_id,
            provider_id="openclaw",
            mode="cli",
            seat_id=f"coo_{mode}",
            start_ts=start_ts,
            end_ts=end_ts,
            exit_status=-1,
            output_content="",
            schema_validation="n/a",
            error=f"timeout after {timeout_s}s",
        )
        raise InvocationError(
            f"OpenClaw agent timed out after {timeout_s}s"
        ) from exc
    except FileNotFoundError as exc:
        end_ts = _utc_now()
        record_invocation_receipt(
            run_id=run_id,
            provider_id="openclaw",
            mode="cli",
            seat_id=f"coo_{mode}",
            start_ts=start_ts,
            end_ts=end_ts,
            exit_status=-1,
            output_content="",
            schema_validation="n/a",
            error="openclaw binary not found",
        )
        raise InvocationError(
            "openclaw binary not found — is OpenClaw installed and on PATH?"
        ) from exc

    end_ts = _utc_now()

    if result.returncode != 0:
        stderr_snippet = result.stderr[:500] if result.stderr else "(no stderr)"
        record_invocation_receipt(
            run_id=run_id,
            provider_id="openclaw",
            mode="cli",
            seat_id=f"coo_{mode}",
            start_ts=start_ts,
            end_ts=end_ts,
            exit_status=result.returncode,
            output_content=result.stdout or "",
            schema_validation="n/a",
            error=stderr_snippet,
        )
        raise InvocationError(
            f"openclaw exited {result.returncode}: {stderr_snippet}"
        )

    try:
        envelope = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        record_invocation_receipt(
            run_id=run_id,
            provider_id="openclaw",
            mode="cli",
            seat_id=f"coo_{mode}",
            start_ts=start_ts,
            end_ts=end_ts,
            exit_status=result.returncode,
            output_content=result.stdout or "",
            schema_validation="fail",
            error=f"JSON decode error: {exc}",
        )
        raise InvocationError(
            f"openclaw output is not valid JSON: {exc}"
        ) from exc

    if envelope.get("status") != "ok":
        record_invocation_receipt(
            run_id=run_id,
            provider_id="openclaw",
            mode="cli",
            seat_id=f"coo_{mode}",
            start_ts=start_ts,
            end_ts=end_ts,
            exit_status=result.returncode,
            output_content=result.stdout or "",
            schema_validation="fail",
            error=f"openclaw status={envelope.get('status')!r}",
        )
        raise InvocationError(
            f"openclaw returned status={envelope.get('status')!r}"
        )

    try:
        payloads = envelope["result"]["payloads"]
        raw_text: str = payloads[0]["text"]
    except (KeyError, IndexError, TypeError) as exc:
        record_invocation_receipt(
            run_id=run_id,
            provider_id="openclaw",
            mode="cli",
            seat_id=f"coo_{mode}",
            start_ts=start_ts,
            end_ts=end_ts,
            exit_status=result.returncode,
            output_content=result.stdout or "",
            schema_validation="fail",
            error=f"unexpected output shape: {exc}",
        )
        raise InvocationError(
            f"Unexpected openclaw output shape: {exc}"
        ) from exc

    normalized = _normalize_proposal_indentation(raw_text)

    record_invocation_receipt(
        run_id=run_id,
        provider_id="openclaw",
        mode="cli",
        seat_id=f"coo_{mode}",
        start_ts=start_ts,
        end_ts=end_ts,
        exit_status=0,
        output_content=normalized,
        schema_validation="pass",
    )

    return normalized
