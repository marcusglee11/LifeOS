"""Thin adapter for invoking the live OpenClaw COO agent."""
from __future__ import annotations

import json
import subprocess
import uuid
from pathlib import Path


class InvocationError(RuntimeError):
    """Raised when the OpenClaw subprocess fails, times out, or returns unusable output."""


# Sub-keys that appear in proposals list items and must be indented 2 spaces.
_PROPOSALS_SUB_KEYS = frozenset({
    "rationale",
    "proposed_action",
    "urgency_override",
    "suggested_owner",
})

_DIRECT_OUTPUT_SCHEMA = {
    "description": (
        "Required output format for direct mode. "
        "Output MUST be valid YAML using schema_version: escalation_packet.v1. "
        "Do NOT use a 'schema:' key. "
        "Do NOT write analysis prose outside the YAML document. "
        "Do NOT omit the required 'type' field."
    ),
    "escalation_packet_example": """\
schema_version: escalation_packet.v1
generated_at: "2026-03-12T00:00:00Z"
run_id: "coo-direct-001"
type: "protected_path_modification"
context:
  summary: "Protected governance change requested."
  objective_ref: "bootstrap"
  task_ref: ""
analysis:
  issue: "Requested change touches protected governance surfaces."
options:
  - label: "Escalate to CEO"
    tradeoff: "Governance-safe and slower."
  - label: "Defer"
    tradeoff: "No immediate change."
recommendation: "Escalate to CEO."
""",
}


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


def invoke_coo_reasoning(
    context: dict,
    mode: str,
    repo_root: Path,
    timeout_s: int = 120,
) -> str:
    """
    Invoke the live OpenClaw COO with the given context.

    Returns raw COO output text (YAML body).
    Raises InvocationError on subprocess failure or timeout.

    :param context: Context dict to pass as the message body (serialized to JSON).
    :param mode: "propose" | "direct" — included in context for COO routing.
    :param repo_root: Repository root path (unused in CLI invocation; kept for future SDK use).
    :param timeout_s: Subprocess timeout in seconds.
    """
    payload = dict(context)
    payload["mode"] = mode
    if mode == "direct" and "output_schema" not in payload:
        payload["output_schema"] = _DIRECT_OUTPUT_SCHEMA
        payload["mode_contract"] = (
            "Return only escalation_packet.v1 YAML. "
            "The top-level keys must include schema_version, type, context, analysis, options, and recommendation."
        )
        payload["response_style"] = "strict_yaml_only"

    message = json.dumps(payload, sort_keys=True)

    cmd = [
        "openclaw",
        "agent",
        "--agent", "main",
        "--session-id", f"lifeos-coo-{mode}-{uuid.uuid4().hex}",
        "--message", message,
        "--json",
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired as exc:
        raise InvocationError(
            f"OpenClaw agent timed out after {timeout_s}s"
        ) from exc
    except FileNotFoundError as exc:
        raise InvocationError(
            "openclaw binary not found — is OpenClaw installed and on PATH?"
        ) from exc

    if result.returncode != 0:
        stderr_snippet = result.stderr[:500] if result.stderr else "(no stderr)"
        raise InvocationError(
            f"openclaw exited {result.returncode}: {stderr_snippet}"
        )

    try:
        envelope = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise InvocationError(
            f"openclaw output is not valid JSON: {exc}"
        ) from exc

    # Gateway mode returns {"status":"ok","result":{"payloads":[...]}}
    # Embedded fallback returns {"payloads":[...],"meta":{...}} with no top-level status.
    if isinstance(envelope, dict) and envelope.get("status") == "ok":
        payload_root: object = envelope.get("result")
    else:
        payload_root = envelope

    try:
        if not isinstance(payload_root, dict):
            raise TypeError(f"unexpected payload root type: {type(payload_root).__name__}")
        payloads = payload_root["payloads"]
        raw_text: str = payloads[0]["text"]
    except (KeyError, IndexError, TypeError) as exc:
        raise InvocationError(
            f"Unexpected openclaw output shape: {exc}"
        ) from exc

    return _normalize_proposal_indentation(raw_text)
