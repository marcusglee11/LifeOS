"""Thin adapter for invoking the live OpenClaw COO agent."""

from __future__ import annotations

import json
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from runtime.receipts.invocation_receipt import record_invocation_receipt


class InvocationError(RuntimeError):
    """Raised when the OpenClaw subprocess fails, times out, or returns unusable output."""


class ProposalNormalizationError(ValueError):
    """Raised when proposal indentation recovery detects unknown or ambiguous structure."""


_ITEM_KEYS = {
    "task_id": frozenset(
        {
            "rationale",
            "proposed_action",
            "urgency_override",
            "suggested_owner",
        }
    ),
    "proposal_id": frozenset(
        {
            "title",
            "rationale",
            "operation_kind",
            "action_id",
            "args",
            "requires_approval",
            "suggested_owner",
        }
    ),
}
_ITEM_START_PREFIXES = tuple(f"- {key}:" for key in _ITEM_KEYS) + tuple(
    f"-{key}:" for key in _ITEM_KEYS
)


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
    active_item_key: str | None = None

    for line in lines:
        stripped = line.strip()
        if not line or not stripped:
            result.append(line)
            continue

        if line.startswith(_ITEM_START_PREFIXES):
            active_item_key = stripped.split(":", 1)[0].lstrip("- ").strip()
            result.append(line)
            continue

        if active_item_key is not None and not line.startswith(" "):
            if ":" not in line:
                raise ProposalNormalizationError(
                    f"Malformed COO proposal line for {active_item_key}: {line!r}"
                )
            key = line.split(":", 1)[0].strip().lstrip("- ")
            if key in _ITEM_KEYS[active_item_key]:
                result.append("  " + line)
                continue
            if key in _ITEM_KEYS:
                active_item_key = None
            else:
                raise ProposalNormalizationError(
                    f"Unknown COO proposal sub-key for {active_item_key}: {key!r}"
                )

        result.append(line)

    return "\n".join(result)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _thinking_level_for_mode(mode: str) -> str:
    if mode == "chat":
        return "low"
    return "high"


def _estimate_token_usage(input_text: str, output_text: str = "") -> dict[str, int | str]:
    prompt_tokens = max(0, len(input_text) // 4)
    completion_tokens = max(0, len(output_text) // 4)
    total_tokens = prompt_tokens + completion_tokens
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "estimated_tokens": total_tokens,
        "token_source": "estimated",
    }


def invoke_coo_reasoning(
    context: dict,
    mode: str,
    repo_root: Path,
    timeout_s: int = 120,
    run_id: str = "",
    agent: str = "main",
    _retry_delays: tuple[float, ...] = (1.0, 3.0),
) -> str:
    """
    Invoke the live OpenClaw COO with the given context.

    Returns raw COO output text (YAML body).
    Raises InvocationError on subprocess failure or timeout.

    :param context: Context dict to pass as the message body (serialized to JSON).
    :param mode: "propose" | "direct" | "chat" — included in context for COO routing.
    :param repo_root: Repository root path (unused in CLI invocation; kept for future SDK use).
    :param timeout_s: Subprocess timeout in seconds.
    :param run_id: Content-addressable run ID for receipt emission (empty = no receipt).
    """
    payload = dict(context)
    payload["mode"] = mode

    _schema_for_mode = {
        "propose": "task_proposal.v1 or nothing_to_propose.v1",
        "direct": "operation_proposal.v1 or escalation_packet.v1",
        "chat": "natural language or inline operation_proposal.v1",
    }
    _required_schema = _schema_for_mode.get(mode, "unknown")

    if mode == "propose":
        message = (
            f"[MACHINE_API mode={mode}]\n"
            "Draft the task proposal packet for CEO review.\n"
            "This is the DRAFTING stage — the CEO will approve or reject AFTER seeing your output.\n"  # noqa: E501
            "Your output IS the proposal document. Output it as YAML and nothing else.\n\n"
            "OUTPUT FORMAT (strict):\n"
            "- First line MUST be exactly: schema_version: task_proposal.v1\n"
            "- OR if nothing to propose: schema_version: nothing_to_propose.v1\n"
            "- No prose before or after the YAML. No explanation. No questions.\n"
            "- Do NOT read any files — all context provided below.\n\n"
            f"Context:\n{json.dumps(payload, sort_keys=True)}"
        )
    elif mode == "direct":
        message = (
            f"[MACHINE_API mode={mode}]\n"
            "Classify this direct CEO objective.\n"
            "If it fits an allowlisted workspace/internal action, emit operation_proposal.v1 YAML.\n"  # noqa: E501
            "Otherwise emit escalation_packet.v1 YAML.\n"
            "Output YAML and nothing else.\n\n"
            "OUTPUT FORMAT (strict):\n"
            "- First line MUST be exactly: schema_version: operation_proposal.v1\n"
            "- OR first line MUST be exactly: schema_version: escalation_packet.v1\n"
            "- No prose before or after the YAML.\n"
            "- Do NOT read any files — all context provided below.\n\n"
            "MUTATION EXAMPLE:\n"
            "schema_version: operation_proposal.v1\n"
            "proposal_id: OP-a1b2c3d4\n"
            'title: "Write COO workspace note"\n'
            'rationale: "The request is a workspace mutation that fits the allowlisted ops lane."\n'
            "operation_kind: mutation\n"
            "action_id: workspace.file.write\n"
            "args:\n"
            "  path: /workspace/notes/example.md\n"
            '  content: "Hello from COO."\n'
            "requires_approval: true\n"
            "suggested_owner: lifeos\n\n"
            "Example (artifact write):\n"
            "schema_version: operation_proposal.v1\n"
            "proposal_id: OP-a1b2c3d4\n"
            "title: Write batch summary\n"
            "rationale: Record batch2 closure\n"
            "operation_kind: mutation\n"
            "action_id: artifact.file.write\n"
            "args:\n"
            "  path: plans/batch2-summary.md\n"
            '  content: "# Batch 2 Summary\\n\\nCompleted."\n'
            "requires_approval: true\n"
            "suggested_owner: lifeos\n\n"
            "QUERY EXAMPLE:\n"
            "schema_version: operation_proposal.v1\n"
            "proposal_id: OP-b2c3d4e5\n"
            'title: "List COO workspace notes"\n'
            'rationale: "The request is a workspace inspection query that fits the allowlisted ops lane."\n'
            "operation_kind: query\n"
            "action_id: workspace.file.list\n"
            "args:\n"
            "  path: /workspace/notes\n"
            "requires_approval: true\n"
            "suggested_owner: lifeos\n\n"
            "ESCALATION EXAMPLE:\n"
            "schema_version: escalation_packet.v1\n"
            "type: governance_surface_touch\n"
            'objective: "the CEO objective text"\n'
            "options:\n"
            "  - option_id: A\n"
            '    title: "Option title"\n'
            '    action: "What this option does"\n'
            "  - option_id: B\n"
            '    title: "Alternative title"\n'
            '    action: "What this alternative does"\n\n'
            "Rules:\n"
            "- operation_proposal.v1 is for allowlisted workspace/internal actions only\n"
            "- action_id: one of workspace.file.read, workspace.file.list, workspace.status.inspect, workspace.file.write, workspace.file.edit, lifeos.note.record, artifact.file.write, artifact.dir.ensure, artifact.file.archive\n"
            "- /workspace/... paths refer to the COO workspace root\n"
            "- type: one of governance_surface_touch, ambiguous_task, "
            "policy_violation, protected_path_modification, "
            "budget_escalation, unknown_action_category\n"
            "- options: non-empty list with option_id, title, action per item\n"
            "- Do NOT add any text before or after the YAML.\n\n"
            f"Context:\n{json.dumps(payload, sort_keys=True)}"
        )
    elif mode == "chat":
        message = (
            "You are in chat mode.\n"
            "Respond conversationally to the user message below.\n"
            "If the user is asking for an allowlisted workspace/internal action, include a valid "
            "operation_proposal.v1 YAML block inline in your response.\n"
            "Do not use markdown fences around the YAML block.\n"
            "Allowlisted actions: workspace.file.read, workspace.file.list, workspace.status.inspect, workspace.file.write, workspace.file.edit, lifeos.note.record, artifact.file.write, artifact.dir.ensure, artifact.file.archive.\n"
            "/workspace/... paths refer to the COO workspace root.\n\n"
            f"User message:\n{json.dumps(payload, sort_keys=True)}"
        )
    else:
        message = (
            f"[MACHINE_API mode={mode}] "
            f"Output {_required_schema} YAML only. First line: schema_version:\n\n"
            + json.dumps(payload, sort_keys=True)
        )

    # Use a fresh session ID per invocation so machine API calls are stateless.
    # This prevents OpenClaw's session-recovery mechanism from injecting a
    # "Continue where you left off" user message before our actual payload,
    # and stops conversation history from accumulating across invocations.
    session_id = str(uuid.uuid4())

    cmd = [
        "openclaw",
        "agent",
        "--agent",
        agent,
        "--session-id",
        session_id,
        "--thinking",
        _thinking_level_for_mode(mode),
        "--message",
        message,
        "--json",
    ]

    # Retry only for modes where transient failures are recoverable. For
    # propose mode, a missing binary is treated as a deterministic
    # configuration failure and should fail fast.
    _retry_schedule = list(_retry_delays) if mode in ("chat", "direct", "propose") else []
    _last_transient_exc: BaseException | None = None
    result: subprocess.CompletedProcess | None = None
    start_ts = _utc_now()

    for _retry_num in range(len(_retry_schedule) + 1):
        if _retry_num > 0:
            time.sleep(_retry_schedule[_retry_num - 1])
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_s,
                stdin=subprocess.DEVNULL,
            )
            _last_transient_exc = None
            break
        except subprocess.TimeoutExpired as exc:
            _last_transient_exc = exc
        except FileNotFoundError as exc:
            if mode == "propose":
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
                    token_usage=_estimate_token_usage(message),
                    error="openclaw binary not found",
                )
                raise InvocationError(
                    "openclaw binary not found — is OpenClaw installed and on PATH?"
                ) from exc
            _last_transient_exc = exc

    if _last_transient_exc is not None:
        end_ts = _utc_now()
        if isinstance(_last_transient_exc, subprocess.TimeoutExpired):
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
                token_usage=_estimate_token_usage(message),
                error=f"timeout after {timeout_s}s",
            )
            raise InvocationError(
                f"OpenClaw agent timed out after {timeout_s}s"
            ) from _last_transient_exc

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
            token_usage=_estimate_token_usage(message),
            error="openclaw binary not found",
        )
        raise InvocationError(
            "openclaw binary not found — is OpenClaw installed and on PATH?"
        ) from _last_transient_exc

    assert result is not None

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
            token_usage=_estimate_token_usage(message, result.stdout or ""),
            error=stderr_snippet,
        )
        raise InvocationError(f"openclaw exited {result.returncode}: {stderr_snippet}")

    if not result.stdout.strip():
        stderr_snippet = result.stderr[:600].strip() if result.stderr else "(no stderr output)"
        record_invocation_receipt(
            run_id=run_id,
            provider_id="openclaw",
            mode="cli",
            seat_id=f"coo_{mode}",
            start_ts=start_ts,
            end_ts=end_ts,
            exit_status=result.returncode,
            output_content="",
            schema_validation="fail",
            token_usage=_estimate_token_usage(message),
            error=f"empty stdout: {stderr_snippet}",
        )
        raise InvocationError(
            f"openclaw produced no output (exit 0). stderr: {stderr_snippet}"
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
            token_usage=_estimate_token_usage(message, result.stdout or ""),
            error=f"JSON decode error: {exc}",
        )
        raise InvocationError(f"openclaw output is not valid JSON: {exc}") from exc

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
            token_usage=_estimate_token_usage(message, result.stdout or ""),
            error=f"openclaw status={envelope.get('status')!r}",
        )
        raise InvocationError(f"openclaw returned status={envelope.get('status')!r}")

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
            token_usage=_estimate_token_usage(message, result.stdout or ""),
            error=f"unexpected output shape: {exc}",
        )
        raise InvocationError(f"Unexpected openclaw output shape: {exc}") from exc

    try:
        normalized = _normalize_proposal_indentation(raw_text)
    except ProposalNormalizationError as exc:
        record_invocation_receipt(
            run_id=run_id,
            provider_id="openclaw",
            mode="cli",
            seat_id=f"coo_{mode}",
            start_ts=start_ts,
            end_ts=end_ts,
            exit_status=result.returncode,
            output_content=raw_text,
            schema_validation="fail",
            token_usage=_estimate_token_usage(message, raw_text),
            error=f"proposal normalization failed: {exc}",
        )
        raise InvocationError(f"COO output normalization failed: {exc}") from exc

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
        token_usage=_estimate_token_usage(message, normalized),
    )

    return normalized
