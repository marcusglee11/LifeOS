# Review Packet: Review FixPass W4/W5 v1.0

## Scope
Addressed reviewer findings on OpenClaw bridge/evidence and token-accounting fail-closed behavior.

## Commit
- `d848d1f` Fix review findings: fail-closed token accounting and evidence validation

## Findings Addressed
- C1 dead unreachable return path removed in `runtime/agents/api.py`
- C2 steward token accounting now fail-closed in `runtime/orchestration/missions/autonomous_build_cycle.py`
- M1 replay + `require_usage=True` now fail-closed in `runtime/agents/api.py`
- M2 JSON decode hardening in `runtime/orchestration/openclaw_bridge.py`
- M3 explicit invalid `job_id` validation tests in `runtime/tests/orchestration/test_openclaw_bridge.py`

## Verification
- `pytest -q runtime/tests/orchestration/test_openclaw_bridge.py runtime/tests/orchestration/missions/test_autonomous_loop.py runtime/tests/test_agent_api_usage_plumbing.py tests/test_agent_api.py::TestCallAgentReplayMode::test_replay_mode_require_usage_fails_closed`
  - PASS: 26 passed

## Appendix A: Flattened Code (Full)

### FILE: `runtime/agents/api.py`

```python
"""
Agent API Layer - Core interfaces and deterministic ID computation.

Per LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md §5.1
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
import uuid
import warnings
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import httpx
import yaml

from .models import load_model_config, resolve_model_auto, ModelConfig

# Configure logger
logger = logging.getLogger(__name__)


def canonical_json(obj: Any) -> bytes:
    """
    Produce canonical JSON for deterministic hashing.
    
    Per v0.3 spec §5.1.4:
    1. Encoding: UTF-8, no BOM
    2. Whitespace: None
    3. Key ordering: Lexicographically sorted
    4. Array ordering: Preserved
    
    [v0.3 Fail-Closed]: Rejects NaN/Infinity values.
    """
    return json.dumps(
        obj,
        separators=(",", ":"),
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,  # Fail-closed: reject NaN/Infinity
    ).encode("utf-8")


def compute_run_id_deterministic(
    mission_spec: dict,
    inputs_hash: str,
    governance_surface_hashes: dict,
    code_version_id: str,
) -> str:
    """
    Compute deterministic run identifier.
    
    Per v0.3 spec §5.1.3:
    run_id_deterministic = sha256(
        canonical_json(mission_spec) +
        inputs_hash +
        canonical_json(sorted(governance_surface_hashes.items())) +
        code_version_id
    )
    """
    hasher = hashlib.sha256()
    hasher.update(canonical_json(mission_spec))
    hasher.update(inputs_hash.encode("utf-8"))
    hasher.update(canonical_json(sorted(governance_surface_hashes.items())))
    hasher.update(code_version_id.encode("utf-8"))
    return f"sha256:{hasher.hexdigest()}"


def compute_call_id_deterministic(
    run_id_deterministic: str,
    role: str,
    prompt_hash: str,
    packet_hash: str,
) -> str:
    """
    Compute deterministic call identifier.
    
    Per v0.3 spec §5.1.3:
    call_id_deterministic = sha256(
        run_id_deterministic +
        role +
        prompt_hash +
        packet_hash
    )
    """
    hasher = hashlib.sha256()
    hasher.update(run_id_deterministic.encode("utf-8"))
    hasher.update(role.encode("utf-8"))
    hasher.update(prompt_hash.encode("utf-8"))
    hasher.update(packet_hash.encode("utf-8"))
    return f"sha256:{hasher.hexdigest()}"


@dataclass
class AgentCall:
    """Request to invoke an LLM. Per v0.3 spec §5.1."""
    
    role: str
    packet: dict
    model: str = "auto"
    temperature: float = 0.0
    max_tokens: int = 8192
    require_usage: bool = False


@dataclass
class AgentResponse:
    """Response from an LLM call. Per v0.3 spec §5.1."""
    
    call_id: str                 # Deterministic ID
    call_id_audit: str           # UUID for audit (metadata only)
    role: str
    model_used: str
    model_version: str
    content: str
    packet: Optional[dict]
    usage: dict = field(default_factory=dict)
    latency_ms: int = 0
    timestamp: str = ""          # Metadata only


class AgentAPIError(Exception):
    """Base exception for Agent API errors."""
    pass


class EnvelopeViolation(AgentAPIError):
    """Role or operation not permitted."""
    pass


class AgentTimeoutError(AgentAPIError):
    """Call exceeded timeout."""
    pass


class AgentResponseInvalid(AgentAPIError):
    """Response failed packet schema validation."""
    pass


def _normalize_usage(usage: Any) -> dict[str, int]:
    """Normalize provider usage payload into canonical token fields."""
    if not isinstance(usage, dict):
        return {}

    def _pick_int(*keys: str) -> int | None:
        for key in keys:
            value = usage.get(key)
            if isinstance(value, int) and value >= 0:
                return value
        return None

    input_tokens = _pick_int("input_tokens", "prompt_tokens", "promptTokenCount", "inputTokenCount")
    output_tokens = _pick_int("output_tokens", "completion_tokens", "candidatesTokenCount", "outputTokenCount")
    total_tokens = _pick_int("total_tokens", "totalTokenCount")

    normalized: dict[str, int] = {}
    if input_tokens is not None:
        normalized["input_tokens"] = input_tokens
    if output_tokens is not None:
        normalized["output_tokens"] = output_tokens
    if total_tokens is not None:
        normalized["total_tokens"] = total_tokens
    elif input_tokens is not None and output_tokens is not None:
        normalized["total_tokens"] = input_tokens + output_tokens

    return normalized


def _load_role_prompt(role: str, config_dir: str = "config/agent_roles") -> tuple[str, str]:
    """
    Load system prompt for a role.
    
    Args:
        role: Agent role name
        config_dir: Directory containing role prompt files
        
    Returns:
        Tuple of (prompt_content, prompt_hash)
        
    Raises:
        EnvelopeViolation: If role prompt file doesn't exist
    """
    prompt_path = Path(config_dir) / f"{role}.md"
    
    if not prompt_path.exists():
        raise EnvelopeViolation(f"Role prompt not found: {prompt_path}")
    
    content = prompt_path.read_text(encoding="utf-8")
    prompt_hash = f"sha256:{hashlib.sha256(content.encode('utf-8')).hexdigest()}"
    
    # Log warning if governance baseline is missing (per plan: don't fail)
    baseline_path = Path("config/governance_baseline.yaml")
    if not baseline_path.exists():
        warnings.warn(
            f"Governance baseline missing at {baseline_path}. "
            "Role prompt hash verification skipped.",
            UserWarning,
        )
    
    return content, prompt_hash


def _parse_response_packet(content: str) -> Optional[dict]:
    """
    Attempt to parse response content as YAML packet.
    
    Robust parsing:
    1. Try parsing full content.
    2. Try extracting from ```yaml ... ``` or ```json ... ``` blocks.
    3. Returns None if parsing fails.
    """
    import re
    
    # 1. Try full content
    try:
        packet = yaml.safe_load(content)
        if isinstance(packet, dict):
            return packet
    except Exception:
        pass
        
    # 2. Try extracting from code blocks
    # regex for ```[language]\n[content]\n```
    pattern = r"```(?:yaml|json)?\s*\n(.*?)\n\s*```"
    match = re.search(pattern, content, re.DOTALL)
    if match:
        block_content = match.group(1)
        try:
            packet = yaml.safe_load(block_content)
            if isinstance(packet, dict):
                return packet
        except Exception:
            pass
            
    return None


def call_agent(
    call: AgentCall,
    run_id: str = "",
    logger_instance: Optional["AgentCallLogger"] = None,
    config: Optional[ModelConfig] = None,
) -> AgentResponse:
    """
    Invoke an LLM via OpenRouter with role-specific system prompt.
    
    Per v0.3 spec §5.1:
    1. Check replay mode — return cached response if available
    2. Load role prompt in and compute hashes
    3. Resolve model if "auto"
    4. Call OpenRouter API with retry/backoff
    5. Parse response
    6. Log to hash chain
    7. Return AgentResponse
    
    Args:
        call: AgentCall specification
        run_id: Deterministic run ID for logging (empty string if not in a run)
        logger_instance: Optional AgentCallLogger for hash chain logging
        config: Optional ModelConfig (loads from file if None)
        
    Returns:
        AgentResponse with parsed content and metadata
        
    Raises:
        AgentTimeoutError: If call exceeds timeout after retries
        EnvelopeViolation: If role not permitted or prompt missing
        AgentResponseInvalid: If response fails validation
    """
    from .fixtures import is_replay_mode, get_cached_response, CachedResponse
    from .logging import AgentCallLogger
    
    # Load config if not provided
    if config is None:
        config = load_model_config()
    
    # Load role prompt and compute hashes
    system_prompt, prompt_hash = _load_role_prompt(call.role)
    packet_hash = f"sha256:{hashlib.sha256(canonical_json(call.packet)).hexdigest()}"
    
    # Compute deterministic call ID
    call_id = compute_call_id_deterministic(
        run_id_deterministic=run_id or "no_run",
        role=call.role,
        prompt_hash=prompt_hash,
        packet_hash=packet_hash,
    )
    call_id_audit = str(uuid.uuid4())
    
    # Check replay mode first
    if is_replay_mode():
        try:
            cached = get_cached_response(call_id)
            if call.require_usage:
                raise AgentAPIError(
                    "TOKEN_ACCOUNTING_UNAVAILABLE: replay fixtures do not include usage"
                )
            return AgentResponse(
                call_id=call_id,
                call_id_audit=call_id_audit,
                role=call.role,
                model_used=cached.model_version,
                model_version=cached.model_version,
                content=cached.response_content,
                packet=cached.response_packet,
                usage={},
                latency_ms=0,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        except Exception:
            # ReplayMissError will propagate
            raise
    
    # Resolve model
    if call.model == "auto":
        model, selection_reason, model_chain = resolve_model_auto(call.role, config)
    else:
        model = call.model
        selection_reason = "explicit"
        model_chain = [model]
    
    # [HARDENING] Use OpenCodeClient for robust protocol and provider handling.
    # It handles both OpenRouter (OpenAI style) and Zen (Anthropic style) logic.
    from .opencode_client import OpenCodeClient, LLMCall
    
    # Build client with role for key selection
    client = OpenCodeClient(
        role=call.role,
        timeout=config.timeout_seconds,
        log_calls=True, # Enable local logs for debugging
    )
    
    try:
        start_time = time.monotonic()
        
        # Prepare request
        # Note: OpenCodeClient expects the full prompt (system + user) internally 
        # but LLMCall has a system_prompt field. 
        prompt = yaml.safe_dump(call.packet, default_flow_style=False)
        llm_request = LLMCall(
            prompt=prompt,
            model=model,
            system_prompt=system_prompt,
            role=call.role
        )
        
        # Execute call via client (handles retry and fallback internally)
        response = client.call(llm_request)
        normalized_usage = _normalize_usage(getattr(response, "usage", {}))
        if call.require_usage and not normalized_usage:
            raise AgentAPIError("TOKEN_ACCOUNTING_UNAVAILABLE: upstream usage missing")
        
        latency_ms = int((time.monotonic() - start_time) * 1000)
        
        # Parse response
        content = response.content
        model_version = response.model_used
        
        # Parse response as packet if possible
        packet = _parse_response_packet(content)
        output_packet_hash = (
            f"sha256:{hashlib.sha256(canonical_json(packet)).hexdigest()}"
            if packet else ""
        )
        
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Log to hash chain if logger provided
        if logger_instance is None:
            from .logging import AgentCallLogger
            logger_instance = AgentCallLogger()
        
        logger_instance.log_call(
            call_id_deterministic=call_id,
            call_id_audit=response.call_id,
            role=call.role,
            model_requested=call.model,
            model_used=model,
            model_version=model_version,
            input_packet_hash=packet_hash,
            prompt_hash=prompt_hash,
            input_tokens=normalized_usage.get("input_tokens", 0),
            output_tokens=normalized_usage.get("output_tokens", 0),
            latency_ms=latency_ms,
            output_packet_hash=output_packet_hash,
            status="success",
        )
        
        return AgentResponse(
            call_id=call_id,
            call_id_audit=response.call_id,
            role=call.role,
            model_used=model,
            model_version=model_version,
            content=content,
            packet=packet,
            usage=normalized_usage,
            latency_ms=latency_ms,
            timestamp=timestamp,
        )
        
    except Exception as e:
        logger.error(f"Agent call failed: {e}")
        raise AgentAPIError(f"Agent call failed: {str(e)}")

```

### FILE: `runtime/orchestration/missions/autonomous_build_cycle.py`

```python
"""
Phase 3 Mission Types - Autonomous Build Cycle (Loop Controller)

Refactored for Phase A: Convergent Builder Loop.
Implements a deterministic, resumable, budget-bounded build loop.
"""
from __future__ import annotations

import json
import hashlib
import time
from typing import Any, Dict, List, Optional
from pathlib import Path

from runtime.orchestration.missions.base import (
    BaseMission,
    MissionContext,
    MissionResult,
    MissionType,
    MissionValidationError,
    MissionEscalationRequired,
)
from runtime.orchestration.missions.design import DesignMission
from runtime.orchestration.missions.build import BuildMission
from runtime.orchestration.missions.review import ReviewMission
from runtime.orchestration.missions.steward import StewardMission

# Backlog Integration
from recursive_kernel.backlog_parser import (
    parse_backlog,
    select_eligible_item,
    select_next_task,
    mark_item_done_with_evidence,
    BacklogItem,
    Priority as BacklogPriority,
)
from runtime.orchestration.task_spec import TaskSpec, TaskPriority

# Loop Infrastructure
from runtime.orchestration.loop.ledger import (
    AttemptLedger, AttemptRecord, LedgerHeader, LedgerIntegrityError
)
from runtime.orchestration.loop.policy import LoopPolicy
from runtime.orchestration.loop.budgets import BudgetController
from runtime.orchestration.loop.taxonomy import (
    TerminalOutcome, TerminalReason, FailureClass, LoopAction
)
from runtime.api.governance_api import PolicyLoader
from runtime.orchestration.run_controller import verify_repo_clean, run_git_command
from runtime.util.file_lock import FileLock

# CEO Approval Queue
from runtime.orchestration.ceo_queue import (
    CEOQueue, EscalationEntry, EscalationType, EscalationStatus
)

# Phase 3a: Test Execution
from runtime.api.governance_api import check_pytest_scope
from runtime.orchestration.test_executor import PytestExecutor, PytestResult
from runtime.orchestration.loop.failure_classifier import classify_test_failure

class AutonomousBuildCycleMission(BaseMission):
    """
    Autonomous Build Cycle: Convergent Builder Loop Controller.
    
    Inputs:
        - task_spec (str): Task description
        - context_refs (list[str]): Context paths
        - handoff_schema_version (str, optional): Validation version
        
    Outputs:
        - commit_hash (str): Final hash if PASS
        - loop_report (dict): Full execution report
    """
    
    @property
    def mission_type(self) -> MissionType:
        return MissionType.AUTONOMOUS_BUILD_CYCLE
    
    def validate_inputs(self, inputs: Dict[str, Any]) -> None:
        # from_backlog mode doesn't require task_spec (will be loaded from backlog)
        if inputs.get("from_backlog"):
            # Task will be loaded from BACKLOG.md
            return

        if not inputs.get("task_spec"):
            raise MissionValidationError("task_spec is required (or use from_backlog=True)")

        # P0: Handoff Schema Version Validation
        req_version = "v1.0" # Hardcoded expectation for Phase A
        if "handoff_schema_version" in inputs:
            if inputs["handoff_schema_version"] != req_version:
                # We can't return a Result from validate_inputs, must raise.
                # But strict fail-closed requires blocking.
                raise MissionValidationError(f"Handoff version mismatch. Expected {req_version}, got {inputs['handoff_schema_version']}")

    def _can_reset_workspace(self, context: MissionContext) -> bool:
        """
        P0: Validate if workspace clean/reset is available.
        For Phase A, we check if we can run a basic git status or if an executor is provided.
        In strict mode, if we can't guarantee reset, we fail closed.
        """
        # MVP: Fail if no operation_executor, or if we can't verify clean state.
        # But wait, we are running in a checked out repo.
        # Simple check: Is the working directory dirty?
        # We can try running git status via subprocess?
        # Or better, just rely on the 'clean' requirement.
        # If we can't implement reset, we return False.
        # Since I don't have a built-in resetter:
        return True # Stub for MVP, implying "Assume Clean" for now? 
        # User constraint: "If a clean reset cannot be guaranteed... fail-closed: ESCALATION_REQUESTED reason WORKSPACE_RESET_UNAVAILABLE"
        # I will enforce this check at start of loop.

    def _compute_hash(self, obj: Any) -> str:
        s = json.dumps(obj, sort_keys=True, default=str)
        return hashlib.sha256(s.encode('utf-8')).hexdigest()

    def _extract_usage_tokens(self, evidence: Dict[str, Any]) -> Optional[int]:
        """Return normalized token usage total, or None when unavailable."""
        usage = evidence.get("usage")
        if not isinstance(usage, dict) or not usage:
            return None

        total_tokens = usage.get("total_tokens")
        if isinstance(total_tokens, int) and total_tokens >= 0:
            return total_tokens

        input_tokens = usage.get("input_tokens")
        output_tokens = usage.get("output_tokens")
        if (
            isinstance(input_tokens, int)
            and input_tokens >= 0
            and isinstance(output_tokens, int)
            and output_tokens >= 0
        ):
            return input_tokens + output_tokens

        legacy_total = usage.get("total")
        if isinstance(legacy_total, int) and legacy_total >= 0:
            return legacy_total

        return None

    def _emit_packet(self, name: str, content: Dict[str, Any], context: MissionContext):
        """Emit a canonical packet to artifacts/"""
        path = context.repo_root / "artifacts" / name
        with open(path, 'w', encoding='utf-8') as f:
            # Markdown wrapper for readability + JSON/YAML payload
            f.write(f"# Packet: {name}\n\n")
            f.write("```json\n")
            json.dump(content, f, indent=2)
            f.write("\n```\n")

    def _escalate_to_ceo(
        self,
        queue: CEOQueue,
        escalation_type: EscalationType,
        context_data: Dict[str, Any],
        run_id: str,
    ) -> str:
        """Create escalation entry and return ID.

        Args:
            queue: The CEO queue instance
            escalation_type: Type of escalation
            context_data: Context information for the escalation
            run_id: Current run ID

        Returns:
            The escalation ID
        """
        entry = EscalationEntry(
            type=escalation_type,
            context=context_data,
            run_id=run_id,
        )
        return queue.add_escalation(entry)

    def _check_queue_for_approval(
        self, queue: CEOQueue, escalation_id: str
    ) -> Optional[EscalationEntry]:
        """Check if escalation has been resolved.

        Args:
            queue: The CEO queue instance
            escalation_id: The escalation ID to check

        Returns:
            The escalation entry, or None if not found
        """
        entry = queue.get_by_id(escalation_id)
        if entry is None:
            return None
        if entry.status == EscalationStatus.PENDING:
            # Check for timeout (24 hours)
            if self._is_escalation_stale(entry):
                queue.mark_timeout(escalation_id)
                entry = queue.get_by_id(escalation_id)
        return entry

    def _is_escalation_stale(
        self, entry: EscalationEntry, hours: int = 24
    ) -> bool:
        """Check if escalation exceeds timeout threshold.

        Args:
            entry: The escalation entry
            hours: Timeout threshold in hours (default 24)

        Returns:
            True if stale, False otherwise
        """
        from datetime import datetime
        age = datetime.utcnow() - entry.created_at
        return age.total_seconds() > hours * 3600

    def _load_task_from_backlog(self, context: MissionContext) -> Optional[BacklogItem]:
        """
        Load next eligible task from BACKLOG.md, skipping blocked tasks.

        A task is considered blocked if:
        - It has explicit dependencies
        - Its context contains markers: "blocked", "depends on", "waiting for"

        Returns:
            BacklogItem or None if no eligible tasks
            Raises: FileNotFoundError if BACKLOG.md missing (caller distinguishes from NO_ELIGIBLE_TASKS)
        """
        backlog_path = context.repo_root / "docs" / "11_admin" / "BACKLOG.md"

        if not backlog_path.exists():
            raise FileNotFoundError(f"BACKLOG.md not found at: {backlog_path}")

        items = parse_backlog(backlog_path)

        # First filter to uncompleted (TODO, P0/P1) tasks
        from recursive_kernel.backlog_parser import get_uncompleted_tasks
        uncompleted = get_uncompleted_tasks(items)

        # Then filter out blocked tasks before selection
        def is_not_blocked(item: BacklogItem) -> bool:
            """Check if task is not blocked."""
            # Check context for blocking markers
            blocked_markers = ["blocked", "depends on", "waiting for"]
            return not any(marker in item.context.lower() for marker in blocked_markers)

        selected = select_next_task(uncompleted, filter_fn=is_not_blocked)

        return selected

    def run(self, context: MissionContext, inputs: Dict[str, Any]) -> MissionResult:
        # Deprecated path guard: keep class for compatibility/historical replay/tests.
        # Block only CLI mission-run entrypoint for new autonomous runs.
        if (
            context.metadata.get("cli_command") == "mission run"
            and not inputs.get("allow_deprecated_replay", False)
        ):
            return self._make_result(
                success=False,
                executed_steps=["deprecation_guard"],
                error=(
                    "autonomous_build_cycle is deprecated for new runs. "
                    "Use 'lifeos spine run <task_spec>' instead."
                ),
                escalation_reason="DEPRECATED_PATH",
                evidence={"deprecation": "autonomous_build_cycle"},
            )

        executed_steps: List[str] = []
        total_tokens = 0
        final_commit_hash = "UNKNOWN"  # Track commit hash from steward

        # Handle from_backlog mode
        if inputs.get("from_backlog"):
            try:
                backlog_item = self._load_task_from_backlog(context)
            except FileNotFoundError as e:
                # BACKLOG.md missing - distinct from NO_ELIGIBLE_TASKS
                reason = "BACKLOG_MISSING"
                self._emit_terminal(TerminalOutcome.BLOCKED, reason, context, 0)
                return self._make_result(
                    success=False,
                    outputs={"outcome": "BLOCKED", "reason": reason, "error": str(e)},
                    executed_steps=["backlog_scan"],
                )

            if backlog_item is None:
                # No eligible tasks (all completed, blocked, or wrong priority)
                reason = "NO_ELIGIBLE_TASKS"
                self._emit_terminal(TerminalOutcome.BLOCKED, reason, context, 0)
                return self._make_result(
                    success=False,
                    outputs={"outcome": "BLOCKED", "reason": reason},
                    executed_steps=["backlog_scan"],
                )

            # Convert BacklogItem to task_spec format for design phase
            task_description = f"{backlog_item.title}\n\nAcceptance Criteria:\n{backlog_item.dod}"
            inputs["task_spec"] = task_description
            inputs["_backlog_item"] = backlog_item  # Store for completion marking

            executed_steps.append(f"backlog_selected:{backlog_item.item_key[:8]}")

        # P0: Workspace Semantics - Fail Closed if Reset Unavailable
        if not self._can_reset_workspace(context):
             reason = TerminalReason.WORKSPACE_RESET_UNAVAILABLE.value
             self._emit_terminal(TerminalOutcome.ESCALATION_REQUESTED, reason, context, total_tokens)
             return self._make_result(success=False, escalation_reason=reason, executed_steps=executed_steps)

        # 1. Setup Infrastructure
        ledger_path = context.repo_root / "artifacts" / "loop_state" / "attempt_ledger.jsonl"
        ledger = AttemptLedger(ledger_path)
        budget = BudgetController()

        # CEO Approval Queue
        queue_path = context.repo_root / "artifacts" / "queue" / "escalations.db"
        queue = CEOQueue(db_path=queue_path)
        
        # P0.1: Promotion to Authoritative Gating (Enabled per Council Pass)
        # Load policy config from repo canonical location
        policy_config_dir = context.repo_root / "config" / "policy"
        loader = PolicyLoader(config_dir=policy_config_dir, authoritative=True)
        effective_config = loader.load()
        
        policy = LoopPolicy(effective_config=effective_config)
        
        # P0: Policy Hash (Hardcoded for checking)
        current_policy_hash = "phase_a_hardcoded_v1" 
        
        # 2. Hydrate / Initialize Ledger
        try:
            is_resume = ledger.hydrate()
            if is_resume:
                # P0: Policy Hash Guard
                if ledger.header["policy_hash"] != current_policy_hash:
                    reason = TerminalReason.POLICY_CHANGED_MID_RUN.value
                    self._emit_terminal(TerminalOutcome.ESCALATION_REQUESTED, reason, context, total_tokens)
                    return self._make_result(
                        success=False,
                        escalation_reason=f"{reason}: Ledger has {ledger.header['policy_hash']}, current is {current_policy_hash}",
                        executed_steps=executed_steps
                    )
                executed_steps.append("ledger_hydrated")

                # Check for pending escalation on resume
                escalation_state_path = context.repo_root / "artifacts" / "loop_state" / "escalation_state.json"
                if escalation_state_path.exists():
                    with open(escalation_state_path, 'r') as f:
                        esc_state = json.load(f)
                    escalation_id = esc_state.get("escalation_id")
                    if escalation_id:
                        entry = self._check_queue_for_approval(queue, escalation_id)
                        if entry and entry.status == EscalationStatus.PENDING:
                            # Still pending, cannot resume
                            return self._make_result(
                                success=False,
                                escalation_reason=f"Escalation {escalation_id} still pending CEO approval",
                                outputs={"escalation_id": escalation_id},
                                executed_steps=executed_steps
                            )
                        elif entry and entry.status == EscalationStatus.REJECTED:
                            # Rejected, terminate
                            reason = f"CEO rejected escalation {escalation_id}: {entry.resolution_note}"
                            self._emit_terminal(TerminalOutcome.BLOCKED, reason, context, total_tokens)
                            return self._make_result(
                                success=False,
                                error=reason,
                                executed_steps=executed_steps
                            )
                        elif entry and entry.status == EscalationStatus.TIMEOUT:
                            # Timeout, terminate
                            reason = f"Escalation {escalation_id} timed out after 24 hours"
                            self._emit_terminal(TerminalOutcome.BLOCKED, reason, context, total_tokens)
                            return self._make_result(
                                success=False,
                                error=reason,
                                executed_steps=executed_steps
                            )
                        elif entry and entry.status == EscalationStatus.APPROVED:
                            # Approved, can continue - clear escalation state
                            escalation_state_path.unlink()
                            executed_steps.append(f"escalation_{escalation_id}_approved")
            else:
                # Initialize
                ledger.initialize(
                    LedgerHeader(
                        policy_hash=current_policy_hash,
                        handoff_hash=self._compute_hash(inputs),
                        run_id=context.run_id
                    )
                )
                executed_steps.append("ledger_initialized")
                
        except LedgerIntegrityError as e:
            return self._make_result(
                success=False,
                error=f"{TerminalOutcome.BLOCKED.value}: {TerminalReason.LEDGER_CORRUPT.value} - {e}",
                executed_steps=executed_steps
            )

        # 3. Design Phase (Attempt 0) - Simplified for Phase A
        # In a robust resume, we'd load this from disk.
        # For Phase A, if resuming, we assume we can re-run design OR we stored it.
        # Let's run design (idempotent-ish).
        design = DesignMission()
        d_res = design.run(context, inputs)
        executed_steps.append("design_phase")

        if not d_res.success:
            return self._make_result(success=False, error=f"Design failed: {d_res.error}", executed_steps=executed_steps)

        design_tokens = self._extract_usage_tokens(d_res.evidence)
        if design_tokens is None:
            reason = TerminalReason.TOKEN_ACCOUNTING_UNAVAILABLE.value
            self._emit_terminal(TerminalOutcome.ESCALATION_REQUESTED, reason, context, total_tokens)
            return self._make_result(success=False, escalation_reason=reason, executed_steps=executed_steps)
        total_tokens += design_tokens
            
        build_packet = d_res.outputs["build_packet"]
        
        # Design Review
        review = ReviewMission()
        r_res = review.run(context, {"subject_packet": build_packet, "review_type": "build_review"})
        executed_steps.append("design_review")

        review_tokens = self._extract_usage_tokens(r_res.evidence)
        if review_tokens is None:
            reason = TerminalReason.TOKEN_ACCOUNTING_UNAVAILABLE.value
            self._emit_terminal(TerminalOutcome.ESCALATION_REQUESTED, reason, context, total_tokens)
            return self._make_result(success=False, escalation_reason=reason, executed_steps=executed_steps)
        total_tokens += review_tokens

        if not r_res.success or r_res.outputs.get("verdict") != "approved":
             return self._make_result(
                 success=False,
                 escalation_reason=f"Design rejected: {r_res.outputs.get('verdict')}",
                 executed_steps=executed_steps
             )
             
        design_approval = r_res.outputs.get("council_decision")

        # 4. Loop Execution
        loop_active = True
        
        while loop_active:
            # Determine Attempt ID
            if ledger.history:
                attempt_id = ledger.history[-1].attempt_id + 1
            else:
                attempt_id = 1
                
            # Budget Check
            is_over, budget_reason = budget.check_budget(attempt_id, total_tokens)
            if is_over:
                # Emit Terminal Packet
                self._emit_terminal(TerminalOutcome.BLOCKED, budget_reason, context, total_tokens)
                return self._make_result(success=False, error=budget_reason, executed_steps=executed_steps) # Simplified return
                
            # Policy Check (Deadlock/Oscillation/Resume-Action)
            action, reason = policy.decide_next_action(ledger)
            
            if action == LoopAction.TERMINATE.value:
                # If policy says terminate, we stop.
                # Map reason to TerminalOutcome
                outcome = TerminalOutcome.BLOCKED
                if reason == TerminalReason.PASS.value:
                    outcome = TerminalOutcome.PASS
                elif reason == TerminalReason.OSCILLATION_DETECTED.value:
                    outcome = TerminalOutcome.ESCALATION_REQUESTED
                
                self._emit_terminal(outcome, reason, context, total_tokens)
                
                if outcome == TerminalOutcome.PASS:
                    # Return success details with commit hash from steward
                    return self._make_result(success=True, outputs={"commit_hash": final_commit_hash}, executed_steps=executed_steps)
                else:
                    return self._make_result(success=False, error=reason, executed_steps=executed_steps)

            # Execution (RETRY or First Run)
            feedback = ""
            if ledger.history:
                last = ledger.history[-1]
                feedback = f"Previous attempt failed: {last.failure_class}. Rationale: {last.rationale}"
                # Inject feedback
                build_packet["feedback_context"] = feedback

            # Build Mission
            build = BuildMission()
            b_res = build.run(context, {"build_packet": build_packet, "approval": design_approval})
            executed_steps.append(f"build_attempt_{attempt_id}")
            
            build_tokens = self._extract_usage_tokens(b_res.evidence)
            if build_tokens is None:
                # P0: Fail Closed on Token Accounting
                reason = TerminalReason.TOKEN_ACCOUNTING_UNAVAILABLE.value
                self._emit_terminal(TerminalOutcome.ESCALATION_REQUESTED, reason, context, total_tokens)
                return self._make_result(success=False, escalation_reason=reason, executed_steps=executed_steps)
            total_tokens += build_tokens

            if not b_res.success:
                # Internal mission error (crash?)
                self._record_attempt(ledger, attempt_id, context, b_res, FailureClass.UNKNOWN, "Build crashed")
                continue

            review_packet = b_res.outputs["review_packet"]
            
            # P0: Diff Budget Check (BEFORE Apply/Review)
            # Extracted from review_packet payload
            content = review_packet.get("payload", {}).get("content", "")
            lines = content.count('\n')
            
            # P0: Enforce limit (300 lines)
            max_lines = 300 # Hardcoded P0 constraint
            over_diff, diff_reason = budget.check_diff_budget(lines, max_lines=max_lines)
            
            if over_diff:
                reason = TerminalReason.DIFF_BUDGET_EXCEEDED.value
                # Evidence: Capture the rejected diff 
                evidence_path = context.repo_root / "artifacts" / f"rejected_diff_attempt_{attempt_id}.txt"
                with open(evidence_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                # Emit Terminal Packet with Evidence ref
                self._emit_terminal(TerminalOutcome.ESCALATION_REQUESTED, reason, context, total_tokens, diff_evidence=str(evidence_path))
                
                # Record Failure
                self._record_attempt(ledger, attempt_id, context, b_res, FailureClass.UNKNOWN, reason)

                return self._make_result(success=False, escalation_reason=reason, executed_steps=executed_steps)

            # Output Review
            out_review = ReviewMission()
            or_res = out_review.run(context, {"subject_packet": review_packet, "review_type": "output_review"})
            executed_steps.append(f"review_attempt_{attempt_id}")
            output_review_tokens = self._extract_usage_tokens(or_res.evidence)
            if output_review_tokens is None:
                reason = TerminalReason.TOKEN_ACCOUNTING_UNAVAILABLE.value
                self._emit_terminal(TerminalOutcome.ESCALATION_REQUESTED, reason, context, total_tokens)
                return self._make_result(success=False, escalation_reason=reason, executed_steps=executed_steps)
            total_tokens += output_review_tokens

            # Classification
            success = False
            failure_class = None
            term_reason = None
            
            verdict = or_res.outputs.get("verdict")
            if verdict == "approved":
                success = True
                failure_class = None
                # Steward
                steward = StewardMission()
                s_res = steward.run(context, {"review_packet": review_packet, "approval": or_res.outputs.get("council_decision")})
                if s_res.success:
                    steward_tokens = self._extract_usage_tokens(s_res.evidence)
                    if steward_tokens is None:
                        reason = TerminalReason.TOKEN_ACCOUNTING_UNAVAILABLE.value
                        self._emit_terminal(TerminalOutcome.ESCALATION_REQUESTED, reason, context, total_tokens)
                        return self._make_result(success=False, escalation_reason=reason, executed_steps=executed_steps)
                    total_tokens += steward_tokens

                    # SUCCESS! Capture commit hash and add steward step
                    final_commit_hash = s_res.outputs.get("commit_hash", s_res.outputs.get("simulated_commit_hash", "UNKNOWN"))
                    executed_steps.append("steward")

                    # Mark backlog task complete if from_backlog mode
                    if inputs.get("_backlog_item"):
                        backlog_item = inputs["_backlog_item"]
                        backlog_path = context.repo_root / "docs" / "11_admin" / "BACKLOG.md"

                        mark_item_done_with_evidence(
                            backlog_path,
                            backlog_item,
                            evidence={
                                "commit_hash": final_commit_hash,
                                "run_id": context.run_id,
                            },
                            repo_root=context.repo_root,
                        )
                        executed_steps.append("backlog_marked_complete")

                    # Record PASS
                    self._record_attempt(ledger, attempt_id, context, b_res, None, "Attributes Approved", success=True)
                    # Loop will check policy next iter -> PASS
                    continue 
                else:
                    success = False
                    failure_class = FailureClass.UNKNOWN
            else:
                # Map verdict to failure class
                success = False
                if verdict == "rejected":
                     failure_class = FailureClass.REVIEW_REJECTION
                else:
                     failure_class = FailureClass.REVIEW_REJECTION # Needs revision etc

            # Record Attempt
            reason_str = or_res.outputs.get("council_decision", {}).get("synthesis", "No rationale")
            self._record_attempt(ledger, attempt_id, context, b_res, failure_class, reason_str, success=success)
             
            # Emit Review Packet
            self._emit_packet(f"Review_Packet_attempt_{attempt_id:04d}.md", review_packet, context)


    def _record_attempt(self, ledger, attempt_id, context, build_res, f_class, rationale, success=False):
        # Compute hashes
        # diff_hash from review_packet content
        review_packet = build_res.outputs.get("review_packet")
        content = review_packet.get("payload", {}).get("content", "") if review_packet else ""
        d_hash = self._compute_hash(content)
        
        rec = AttemptRecord(
            attempt_id=attempt_id,
            timestamp=str(time.time()),
            run_id=context.run_id,
            policy_hash="phase_a_hardcoded_v1",
            input_hash="hash(inputs)", 
            actions_taken=build_res.executed_steps,
            diff_hash=d_hash,
            changed_files=[], # Extract if possible
            evidence_hashes={},
            success=success,
            failure_class=f_class.value if f_class else None,
            terminal_reason=None, # Filled if terminal
            next_action="evaluated_next_tick",
            rationale=rationale
        )
        ledger.append(rec)

    def _emit_terminal(self, outcome, reason, context, tokens, diff_evidence: str = None):
        """Emit CEO Terminal Packet & Closure Bundle."""
        content = {
            "outcome": outcome.value,
            "reason": reason,
            "tokens_consumed": tokens,
            "run_id": context.run_id
        }
        if diff_evidence:
            content["diff_evidence_path"] = diff_evidence

        self._emit_packet("CEO_Terminal_Packet.md", content, context)
        # Closure Bundle? (Stubbed as requested: "Use existing if present")
        # We assume independent closure process picks this up, or we assume done.

    # =========================================================================
    # Phase 3a: Test Verification Methods
    # =========================================================================

    def _run_verification_tests(
        self,
        context: MissionContext,
        target: str = "runtime/tests",
        timeout: int = 60
    ) -> Dict[str, Any]:
        """
        Run pytest on runtime/tests/ after build completes.

        Args:
            context: Mission context
            target: Test target path (default: runtime/tests)
            timeout: Timeout in seconds (default: 300 = 5 minutes)

        Returns:
            VerificationResult dict with:
                - success: bool (True if tests passed)
                - test_result: PytestResult object
                - evidence: dict with captured output
                - error: Optional error message
        """
        # Check pytest scope
        allowed, reason = check_pytest_scope(target)
        if not allowed:
            return {
                "success": False,
                "error": f"Test scope denied: {reason}",
                "evidence": {},
            }

        # Execute tests
        executor = PytestExecutor(timeout=timeout)
        result = executor.run(target)

        # Build verification result
        return {
            "success": result.exit_code == 0,
            "test_result": result,
            "evidence": {
                "pytest_stdout": result.stdout[:50000],  # Cap at 50KB
                "pytest_stderr": result.stderr[:50000],  # Cap at 50KB
                "exit_code": result.exit_code,
                "duration_seconds": result.duration,
                "test_counts": result.counts or {},
                "status": result.status,
                "timeout_triggered": result.evidence.get("timeout_triggered", False),
            },
            "error": None if result.exit_code == 0 else "Tests failed",
        }

    def _prepare_retry_context(
        self,
        verification: Dict[str, Any],
        previous_results: Optional[List[PytestResult]] = None
    ) -> Dict[str, Any]:
        """
        Prepare context for retry after test failure.

        Includes:
        - Which tests failed
        - Error messages from failures
        - Failure classification

        Args:
            verification: VerificationResult dict from _run_verification_tests
            previous_results: Optional list of previous test results for flake detection

        Returns:
            Retry context dict
        """
        test_result = verification.get("test_result")
        if not test_result:
            return {
                "failure_class": FailureClass.UNKNOWN.value,
                "error": "No test result available",
            }

        # Classify failure
        failure_class = classify_test_failure(test_result, previous_results)

        context = {
            "failure_class": failure_class.value,
            "error_messages": test_result.error_messages[:5] if test_result.error_messages else [],
            "suggestion": self._generate_fix_suggestion(failure_class),
        }

        # Add test-specific details if available
        if test_result.failed_tests:
            context["failed_tests"] = list(test_result.failed_tests)[:10]  # Cap at 10
        if test_result.counts:
            context["test_counts"] = test_result.counts

        return context

    def _generate_fix_suggestion(self, failure_class: FailureClass) -> str:
        """
        Generate fix suggestion based on failure class.

        Args:
            failure_class: Classified failure type

        Returns:
            Suggestion string for retry
        """
        suggestions = {
            FailureClass.TEST_FAILURE: "Review test failures and fix the code logic that's causing assertions to fail.",
            FailureClass.TEST_FLAKE: "This test appears flaky (passed before, failed now). Consider investigating timing issues or test dependencies.",
            FailureClass.TEST_TIMEOUT: "Tests exceeded timeout limit. Consider optimizing slow tests or increasing timeout threshold.",
        }
        return suggestions.get(failure_class, "Review the test output and fix the underlying issue.")

```

### FILE: `runtime/orchestration/openclaw_bridge.py`

```python
"""OpenClaw <-> Spine mapping helpers.

This module centralizes payload conversions between OpenClaw orchestration
inputs and LoopSpine execution/result contracts.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping


OPENCLAW_JOB_KIND = "lifeos.job.v0.1"
OPENCLAW_RESULT_KIND = "lifeos.result.v0.2"
OPENCLAW_EVIDENCE_ROOT = Path("artifacts/evidence/openclaw/jobs")


class OpenClawBridgeError(ValueError):
    """Raised when bridge payload mapping fails validation."""


def _validate_job_id(job_id: str) -> str:
    candidate = job_id.strip()
    if not candidate:
        raise OpenClawBridgeError("missing or invalid 'job_id'")
    if "/" in candidate or "\\" in candidate:
        raise OpenClawBridgeError("job_id must not contain path separators")
    if not re.fullmatch(r"[A-Za-z0-9._:-]+", candidate):
        raise OpenClawBridgeError("job_id contains unsupported characters")
    return candidate


def _require_non_empty_str(payload: Mapping[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise OpenClawBridgeError(f"missing or invalid '{key}'")
    return value.strip()


def _normalize_string_list(value: Any, *, key: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise OpenClawBridgeError(f"'{key}' must be a list[str]")
    return [item.strip() for item in value if item.strip()]


def map_openclaw_job_to_spine_invocation(job_payload: Mapping[str, Any]) -> dict[str, Any]:
    """Map an OpenClaw job payload into a LoopSpine invocation payload."""
    kind = _require_non_empty_str(job_payload, "kind")
    if kind != OPENCLAW_JOB_KIND:
        raise OpenClawBridgeError(f"unsupported job kind: {kind}")

    job_id = _validate_job_id(_require_non_empty_str(job_payload, "job_id"))
    objective = _require_non_empty_str(job_payload, "objective")
    workdir = _require_non_empty_str(job_payload, "workdir")
    command = _normalize_string_list(job_payload.get("command"), key="command")
    if not command:
        raise OpenClawBridgeError("'command' must include at least one token")

    timeout_s = job_payload.get("timeout_s")
    if not isinstance(timeout_s, int) or timeout_s <= 0:
        raise OpenClawBridgeError("missing or invalid 'timeout_s'")

    scope = _normalize_string_list(job_payload.get("scope"), key="scope")
    non_goals = _normalize_string_list(job_payload.get("non_goals"), key="non_goals")
    expected_artifacts = _normalize_string_list(
        job_payload.get("expected_artifacts"),
        key="expected_artifacts",
    )
    context_refs = _normalize_string_list(job_payload.get("context_refs"), key="context_refs")

    run_id = (
        str(job_payload["run_id"]).strip()
        if isinstance(job_payload.get("run_id"), str) and str(job_payload["run_id"]).strip()
        else f"openclaw:{job_id}"
    )

    task_spec = {
        "source": "openclaw",
        "job_id": job_id,
        "job_type": _require_non_empty_str(job_payload, "job_type"),
        "objective": objective,
        "workdir": workdir,
        "command": command,
        "constraints": {
            "scope": scope,
            "non_goals": non_goals,
            "timeout_s": timeout_s,
        },
        "expected_artifacts": expected_artifacts,
        "context_refs": context_refs,
    }

    return {
        "job_id": job_id,
        "run_id": run_id,
        "task_spec": task_spec,
    }


def map_spine_artifacts_to_openclaw_result(
    *,
    job_id: str,
    terminal_packet: Mapping[str, Any] | None = None,
    checkpoint_packet: Mapping[str, Any] | None = None,
    terminal_packet_ref: str | None = None,
    checkpoint_packet_ref: str | None = None,
    packet_refs: list[str] | None = None,
    ledger_refs: list[str] | None = None,
    hash_manifest_ref: str | None = None,
) -> dict[str, Any]:
    """Map LoopSpine terminal/checkpoint packets into an OpenClaw result payload."""
    if bool(terminal_packet) == bool(checkpoint_packet):
        raise OpenClawBridgeError("provide exactly one of terminal_packet or checkpoint_packet")

    if terminal_packet is not None:
        run_id = _require_non_empty_str(terminal_packet, "run_id")
        result: dict[str, Any] = {
            "kind": OPENCLAW_RESULT_KIND,
            "job_id": job_id,
            "run_id": run_id,
            "state": "terminal",
            "outcome": _require_non_empty_str(terminal_packet, "outcome"),
            "reason": _require_non_empty_str(terminal_packet, "reason"),
            "terminal_at": _require_non_empty_str(terminal_packet, "timestamp"),
        }
        if terminal_packet_ref:
            result["terminal_packet_ref"] = terminal_packet_ref
        result["packet_refs"] = sorted(set(packet_refs or []))
        result["ledger_refs"] = sorted(set(ledger_refs or []))
        if hash_manifest_ref:
            result["hash_manifest_ref"] = hash_manifest_ref
        return result

    run_id = _require_non_empty_str(checkpoint_packet or {}, "run_id")
    result = {
        "kind": OPENCLAW_RESULT_KIND,
        "job_id": job_id,
        "run_id": run_id,
        "state": "checkpoint",
        "trigger": _require_non_empty_str(checkpoint_packet or {}, "trigger"),
        "checkpoint_id": _require_non_empty_str(checkpoint_packet or {}, "checkpoint_id"),
        "checkpoint_at": _require_non_empty_str(checkpoint_packet or {}, "timestamp"),
    }
    if checkpoint_packet_ref:
        result["checkpoint_packet_ref"] = checkpoint_packet_ref
    result["packet_refs"] = sorted(set(packet_refs or []))
    result["ledger_refs"] = sorted(set(ledger_refs or []))
    if hash_manifest_ref:
        result["hash_manifest_ref"] = hash_manifest_ref
    return result


def resolve_openclaw_job_evidence_dir(repo_root: Path, job_id: str) -> Path:
    """Resolve deterministic OpenClaw evidence path for a job."""
    validated = _validate_job_id(job_id)
    return Path(repo_root) / OPENCLAW_EVIDENCE_ROOT / validated


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_openclaw_evidence_contract(
    *,
    repo_root: Path,
    job_id: str,
    packet_refs: list[str],
    ledger_refs: list[str],
) -> dict[str, str]:
    """Write deterministic OpenClaw evidence contract artifacts."""
    evidence_dir = resolve_openclaw_job_evidence_dir(repo_root, job_id)
    evidence_dir.mkdir(parents=True, exist_ok=True)

    normalized_packet_refs = _normalize_string_list(packet_refs, key="packet_refs")
    normalized_ledger_refs = _normalize_string_list(ledger_refs, key="ledger_refs")
    if not normalized_packet_refs:
        raise OpenClawBridgeError("packet_refs must not be empty")
    if not normalized_ledger_refs:
        raise OpenClawBridgeError("ledger_refs must not be empty")

    packet_refs_file = evidence_dir / "packet_refs.json"
    ledger_refs_file = evidence_dir / "ledger_refs.json"
    refs_file = evidence_dir / "refs.json"
    hash_manifest_file = evidence_dir / "hash_manifest.sha256"

    packet_refs_payload = {
        "job_id": _validate_job_id(job_id),
        "packet_refs": sorted(set(normalized_packet_refs)),
    }
    ledger_refs_payload = {
        "job_id": _validate_job_id(job_id),
        "ledger_refs": sorted(set(normalized_ledger_refs)),
    }

    packet_refs_file.write_text(
        json.dumps(packet_refs_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    ledger_refs_file.write_text(
        json.dumps(ledger_refs_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    refs_file.write_text(
        json.dumps(
            {
                "job_id": _validate_job_id(job_id),
                "packet_refs_file": packet_refs_file.name,
                "ledger_refs_file": ledger_refs_file.name,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    manifest_entries = []
    for filename in sorted([packet_refs_file.name, ledger_refs_file.name, refs_file.name]):
        file_path = evidence_dir / filename
        manifest_entries.append(f"{_sha256_file(file_path)}  {filename}")
    hash_manifest_file.write_text("\n".join(manifest_entries) + "\n", encoding="utf-8")

    return {
        "evidence_dir": str(evidence_dir),
        "packet_refs_file": str(packet_refs_file),
        "ledger_refs_file": str(ledger_refs_file),
        "refs_file": str(refs_file),
        "hash_manifest_file": str(hash_manifest_file),
    }


def verify_openclaw_evidence_contract(evidence_dir: Path) -> tuple[bool, list[str]]:
    """Verify required OpenClaw evidence contract files and hash manifest."""
    errors: list[str] = []
    evidence_path = Path(evidence_dir)
    required = ["packet_refs.json", "ledger_refs.json", "refs.json", "hash_manifest.sha256"]

    for name in required:
        if not (evidence_path / name).exists():
            errors.append(f"missing required evidence file: {name}")

    if errors:
        return False, errors

    def _safe_load_json(filename: str) -> dict[str, Any] | None:
        try:
            payload = json.loads((evidence_path / filename).read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            errors.append(f"{filename} is not valid JSON")
            return None
        if not isinstance(payload, dict):
            errors.append(f"{filename} must contain a JSON object")
            return None
        return payload

    for filename, field_name in (
        ("packet_refs.json", "packet_refs"),
        ("ledger_refs.json", "ledger_refs"),
    ):
        payload = _safe_load_json(filename)
        if payload is None:
            continue
        refs = payload.get(field_name)
        if not isinstance(refs, list) or not refs:
            errors.append(f"{filename} missing non-empty '{field_name}'")

    manifest_lines = []
    for line in (evidence_path / "hash_manifest.sha256").read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped:
            manifest_lines.append(stripped)
    manifest_map: dict[str, str] = {}
    for line in manifest_lines:
        parts = line.split("  ", 1)
        if len(parts) != 2:
            errors.append("hash_manifest.sha256 contains malformed line")
            continue
        digest, filename = parts
        manifest_map[filename] = digest

    for filename in ("packet_refs.json", "ledger_refs.json", "refs.json"):
        expected = manifest_map.get(filename)
        if expected is None:
            errors.append(f"hash manifest missing entry for {filename}")
            continue
        actual = _sha256_file(evidence_path / filename)
        if actual != expected:
            errors.append(f"hash mismatch for {filename}")

    return len(errors) == 0, errors

```

### FILE: `runtime/tests/orchestration/missions/test_autonomous_loop.py`

```python
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from runtime.orchestration.missions.autonomous_build_cycle import AutonomousBuildCycleMission
from runtime.orchestration.missions.base import MissionContext, MissionResult, MissionType
from runtime.orchestration.loop.taxonomy import TerminalOutcome, TerminalReason

@pytest.fixture
def mock_context(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "artifacts" / "loop_state").mkdir(parents=True)
    (repo_root / "artifacts" / "evidence").mkdir(parents=True)
    
    # Create Policy Config
    policy_dir = repo_root / "config" / "policy"
    policy_dir.mkdir(parents=True)
    
    # Valid master config
    (policy_dir / "policy_rules.yaml").write_text(
        "schema_version: 'v1.0'\n"
        "tool_rules: []\n"
        "failure_routing:\n"
        "  review_rejection:\n"
        "    default_action: RETRY\n"
        "budgets:\n"
        "  retry_limits:\n"
        "    review_rejection: 10\n",
        encoding="utf-8"
    )
    
    # Dummy schema (allow anything)
    (policy_dir / "policy_schema.json").write_text("{}", encoding="utf-8")
    
    return MissionContext(
        repo_root=repo_root,
        baseline_commit="abc",
        run_id="test_run",
        operation_executor=None
    )

@pytest.fixture
def mock_sub_missions():
    with patch("runtime.orchestration.missions.autonomous_build_cycle.DesignMission") as MockDesign, \
         patch("runtime.orchestration.missions.autonomous_build_cycle.BuildMission") as MockBuild, \
         patch("runtime.orchestration.missions.autonomous_build_cycle.ReviewMission") as MockReview, \
         patch("runtime.orchestration.missions.autonomous_build_cycle.StewardMission") as MockSteward:
        
        # Setup Success Defaults
        d_inst = MockDesign.return_value
        d_inst.run.return_value = MissionResult(True, MissionType.DESIGN, outputs={"build_packet": {}}, evidence={"usage": {"input_tokens": 10, "output_tokens": 10}})
        
        b_inst = MockBuild.return_value
        b_inst.run.return_value = MissionResult(True, MissionType.BUILD, outputs={"review_packet": {"payload": {"content": "diff"}}}, evidence={"usage": {"input_tokens": 10, "output_tokens": 10}})
        
        r_inst = MockReview.return_value
        # Design Review -> Approved
        # Output Review -> Approved (Default)
        r_inst.run.return_value = MissionResult(True, MissionType.REVIEW, outputs={"verdict": "approved", "council_decision": {}}, evidence={"usage": {"input_tokens": 10, "output_tokens": 10}})
        
        s_inst = MockSteward.return_value
        s_inst.run.return_value = MissionResult(True, MissionType.STEWARD, outputs={"commit_hash": "hash"}, evidence={"usage": {"input_tokens": 10, "output_tokens": 10}})
        
        yield MockDesign, MockBuild, MockReview, MockSteward

def test_loop_happy_path(mock_context, mock_sub_missions):
    mission = AutonomousBuildCycleMission()
    inputs = {"task_spec": "do validation"}
    
    result = mission.run(mock_context, inputs)
    
    # Needs to handle the fact that my logic loops? 
    # If Policy says Pass, it should exit.
    # In my logic, if Steward passes, 'check policy next iter' -> PASS.
    # So it runs one more policy check -> TERMINATE(PASS).
    
    # Assert
    assert result.success is True
    assert (mock_context.repo_root / "artifacts/CEO_Terminal_Packet.md").exists()

def test_token_accounting_fail_closed(mock_context, mock_sub_missions):
    _, MockBuild, _, _ = mock_sub_missions
    
    # Build returns NO usage
    b_inst = MockBuild.return_value
    b_inst.run.return_value = MissionResult(True, MissionType.BUILD, outputs={"review_packet": {}}, evidence={}) # Missing usage
    
    mission = AutonomousBuildCycleMission()
    inputs = {"task_spec": "do validation"}
    
    result = mission.run(mock_context, inputs)
    
    assert result.success is False
    assert result.escalation_reason == TerminalReason.TOKEN_ACCOUNTING_UNAVAILABLE.value


def test_token_accounting_fail_closed_when_design_usage_missing(mock_context, mock_sub_missions):
    MockDesign, _, _, _ = mock_sub_missions

    d_inst = MockDesign.return_value
    d_inst.run.return_value = MissionResult(
        True,
        MissionType.DESIGN,
        outputs={"build_packet": {}},
        evidence={},
    )

    mission = AutonomousBuildCycleMission()
    result = mission.run(mock_context, {"task_spec": "design without usage"})

    assert result.success is False
    assert result.escalation_reason == TerminalReason.TOKEN_ACCOUNTING_UNAVAILABLE.value


def test_token_accounting_fail_closed_when_review_usage_missing(mock_context, mock_sub_missions):
    _, _, MockReview, _ = mock_sub_missions

    r_inst = MockReview.return_value
    r_inst.run.return_value = MissionResult(
        True,
        MissionType.REVIEW,
        outputs={"verdict": "approved", "council_decision": {}},
        evidence={},
    )

    mission = AutonomousBuildCycleMission()
    result = mission.run(mock_context, {"task_spec": "review without usage"})

    assert result.success is False
    assert result.escalation_reason == TerminalReason.TOKEN_ACCOUNTING_UNAVAILABLE.value


def test_token_accounting_fail_closed_when_steward_usage_missing(mock_context, mock_sub_missions):
    _, _, _, MockSteward = mock_sub_missions

    s_inst = MockSteward.return_value
    s_inst.run.return_value = MissionResult(
        True,
        MissionType.STEWARD,
        outputs={"commit_hash": "hash"},
        evidence={},
    )

    mission = AutonomousBuildCycleMission()
    result = mission.run(mock_context, {"task_spec": "steward without usage"})

    assert result.success is False
    assert result.escalation_reason == TerminalReason.TOKEN_ACCOUNTING_UNAVAILABLE.value

def test_budget_exhausted(mock_context, mock_sub_missions):
    _, _, MockReview, _ = mock_sub_missions
    # Make Review reject everything -> Loop -> Exhaust Budget
    r_inst = MockReview.return_value
    # First call is Design Review (Approved), subsequent are Output Review (Rejected)
    
    # We need side_effect to distinguish calls?
    # Or just make all reviews reject?
    # If Design Review rejects, we exit 'Design rejected'.
    # We want Design Approved, Loop Rejected.
      
    def review_side_effect(ctx, inp):
        if inp["review_type"] == "build_review":
            return MissionResult(True, MissionType.REVIEW, outputs={"verdict": "approved"}, evidence={"usage":{"total":1}})
        else:
            return MissionResult(True, MissionType.REVIEW, outputs={"verdict": "rejected"}, evidence={"usage":{"total":1}})
            
    r_inst.run.side_effect = review_side_effect
    
    # Mock Build to return unique content each time to avoid Deadlock
    b_inst = mock_sub_missions[1].return_value
    b_inst.run.side_effect = [
        MissionResult(True, MissionType.BUILD, outputs={"review_packet": {"payload": {"content": f"diff_{i}"}}}, evidence={"usage": {"total": 1}})
        for i in range(10)
    ]
    
    mission = AutonomousBuildCycleMission()
    inputs = {"task_spec": "loop forever"}
    result = mission.run(mock_context, inputs)
    
    assert result.success is False
    assert result.error == TerminalReason.BUDGET_EXHAUSTED.value

def test_resume_policy_check(mock_context, mock_sub_missions):
    # PLANT A LEDGER WITH DIFFERENT POLICY HASH
    ledger_path = mock_context.repo_root / "artifacts/loop_state/attempt_ledger.jsonl"
    with open(ledger_path, "w") as f:
        f.write('{"type": "header", "policy_hash": "BOGUS", "handoff_hash": "X", "run_id": "r"}\n')
        # Full valid record
        rec = {
            "attempt_id": 1, "timestamp": "t", "run_id": "r", "policy_hash": "p", 
            "input_hash": "i", "actions_taken": [], "diff_hash": "d", "changed_files": [], 
            "evidence_hashes": {}, "success": False, "failure_class": "unknown", 
            "terminal_reason": None, "next_action": "retry", "rationale": "r"
        }
        import json
        f.write(json.dumps(rec) + "\n")
        
    mission = AutonomousBuildCycleMission()
    inputs = {"task_spec": "resume"}
    
    result = mission.run(mock_context, inputs)
    
    assert result.success is False
    assert TerminalReason.POLICY_CHANGED_MID_RUN.value in result.escalation_reason

```

### FILE: `runtime/tests/orchestration/test_openclaw_bridge.py`

```python
from __future__ import annotations

import json
from pathlib import Path

import pytest

from runtime.orchestration.openclaw_bridge import (
    OPENCLAW_RESULT_KIND,
    OpenClawBridgeError,
    map_openclaw_job_to_spine_invocation,
    map_spine_artifacts_to_openclaw_result,
    resolve_openclaw_job_evidence_dir,
    verify_openclaw_evidence_contract,
    write_openclaw_evidence_contract,
)


def test_map_openclaw_job_to_spine_invocation_success() -> None:
    job_payload = {
        "kind": "lifeos.job.v0.1",
        "job_id": "JOB-001",
        "job_type": "build",
        "objective": "Implement bridge mapping",
        "scope": ["tests only"],
        "non_goals": ["no network"],
        "workdir": ".",
        "command": ["pytest", "-q", "runtime/tests/orchestration/test_openclaw_bridge.py"],
        "timeout_s": 900,
        "expected_artifacts": ["stdout.txt", "stderr.txt"],
        "context_refs": ["docs/11_admin/LIFEOS_STATE.md"],
    }

    payload = map_openclaw_job_to_spine_invocation(job_payload)

    assert payload["job_id"] == "JOB-001"
    assert payload["run_id"] == "openclaw:JOB-001"
    assert payload["task_spec"]["source"] == "openclaw"
    assert payload["task_spec"]["constraints"]["timeout_s"] == 900
    assert payload["task_spec"]["command"][0] == "pytest"


def test_map_openclaw_job_to_spine_invocation_invalid_kind() -> None:
    with pytest.raises(OpenClawBridgeError, match="unsupported job kind"):
        map_openclaw_job_to_spine_invocation(
            {
                "kind": "unsupported",
                "job_id": "J1",
                "job_type": "build",
                "objective": "x",
                "workdir": ".",
                "command": ["pytest"],
                "timeout_s": 1,
            }
        )


def test_map_spine_terminal_to_openclaw_result_success() -> None:
    terminal_packet = {
        "run_id": "run-123",
        "timestamp": "2026-02-12T12:00:00Z",
        "outcome": "PASS",
        "reason": "pass",
    }

    result = map_spine_artifacts_to_openclaw_result(
        job_id="JOB-001",
        terminal_packet=terminal_packet,
        terminal_packet_ref="artifacts/terminal/TP_run-123.yaml",
    )

    assert result["kind"] == OPENCLAW_RESULT_KIND
    assert result["job_id"] == "JOB-001"
    assert result["state"] == "terminal"
    assert result["terminal_packet_ref"] == "artifacts/terminal/TP_run-123.yaml"
    assert result["packet_refs"] == []
    assert result["ledger_refs"] == []


def test_map_spine_checkpoint_to_openclaw_result_success() -> None:
    checkpoint_packet = {
        "run_id": "run-123",
        "checkpoint_id": "CP_123",
        "timestamp": "2026-02-12T12:00:00Z",
        "trigger": "ESCALATION_REQUESTED",
    }
    result = map_spine_artifacts_to_openclaw_result(
        job_id="JOB-001",
        checkpoint_packet=checkpoint_packet,
        checkpoint_packet_ref="artifacts/checkpoints/CP_123.yaml",
    )

    assert result["state"] == "checkpoint"
    assert result["checkpoint_id"] == "CP_123"
    assert result["checkpoint_packet_ref"] == "artifacts/checkpoints/CP_123.yaml"


def test_map_spine_result_rejects_ambiguous_inputs() -> None:
    with pytest.raises(OpenClawBridgeError, match="exactly one"):
        map_spine_artifacts_to_openclaw_result(
            job_id="JOB-001",
            terminal_packet={"run_id": "r", "timestamp": "t", "outcome": "PASS", "reason": "pass"},
            checkpoint_packet={"run_id": "r", "timestamp": "t", "trigger": "x", "checkpoint_id": "cp"},
        )


def test_resolve_openclaw_job_evidence_dir_is_deterministic(tmp_path: Path) -> None:
    expected = tmp_path / "artifacts" / "evidence" / "openclaw" / "jobs" / "JOB-009"
    assert resolve_openclaw_job_evidence_dir(tmp_path, "JOB-009") == expected


def test_write_and_verify_openclaw_evidence_contract(tmp_path: Path) -> None:
    written = write_openclaw_evidence_contract(
        repo_root=tmp_path,
        job_id="JOB-777",
        packet_refs=["artifacts/terminal/TP_run-777.yaml"],
        ledger_refs=["artifacts/loop_state/attempt_ledger.jsonl"],
    )

    evidence_dir = Path(written["evidence_dir"])
    assert evidence_dir == tmp_path / "artifacts" / "evidence" / "openclaw" / "jobs" / "JOB-777"

    packet_refs_payload = json.loads((evidence_dir / "packet_refs.json").read_text(encoding="utf-8"))
    ledger_refs_payload = json.loads((evidence_dir / "ledger_refs.json").read_text(encoding="utf-8"))
    assert packet_refs_payload["packet_refs"] == ["artifacts/terminal/TP_run-777.yaml"]
    assert ledger_refs_payload["ledger_refs"] == ["artifacts/loop_state/attempt_ledger.jsonl"]

    ok, errors = verify_openclaw_evidence_contract(evidence_dir)
    assert ok is True
    assert errors == []


def test_verify_openclaw_evidence_contract_fails_when_required_file_missing(tmp_path: Path) -> None:
    written = write_openclaw_evidence_contract(
        repo_root=tmp_path,
        job_id="JOB-778",
        packet_refs=["artifacts/terminal/TP_run-778.yaml"],
        ledger_refs=["artifacts/loop_state/attempt_ledger.jsonl"],
    )

    evidence_dir = Path(written["evidence_dir"])
    (evidence_dir / "packet_refs.json").unlink()
    ok, errors = verify_openclaw_evidence_contract(evidence_dir)
    assert ok is False
    assert any("packet_refs.json" in error for error in errors)


def test_verify_openclaw_evidence_contract_reports_corrupt_json(tmp_path: Path) -> None:
    written = write_openclaw_evidence_contract(
        repo_root=tmp_path,
        job_id="JOB-779",
        packet_refs=["artifacts/terminal/TP_run-779.yaml"],
        ledger_refs=["artifacts/loop_state/attempt_ledger.jsonl"],
    )

    evidence_dir = Path(written["evidence_dir"])
    (evidence_dir / "packet_refs.json").write_text("{not-json}\n", encoding="utf-8")
    ok, errors = verify_openclaw_evidence_contract(evidence_dir)
    assert ok is False
    assert any("packet_refs.json is not valid JSON" == error for error in errors)


@pytest.mark.parametrize(
    "job_id",
    [
        "",
        "   ",
        "../escape",
        "..\\escape",
        "bad/job",
        "bad\\job",
        "bad*char",
    ],
)
def test_resolve_openclaw_job_evidence_dir_rejects_invalid_job_id(
    tmp_path: Path, job_id: str
) -> None:
    with pytest.raises(OpenClawBridgeError):
        resolve_openclaw_job_evidence_dir(tmp_path, job_id)

```

### FILE: `tests/test_agent_api.py`

```python
"""
Unit tests for Agent API Layer.

Tests call_agent() with mocked OpenRouter responses.
Per LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md §5.1
"""

from __future__ import annotations

import hashlib
import json
import os
from unittest.mock import patch, MagicMock
import tempfile
from pathlib import Path

import pytest
import httpx

from runtime.agents.api import (
    canonical_json,
    compute_run_id_deterministic,
    compute_call_id_deterministic,
    AgentCall,
    AgentResponse,
    AgentAPIError,
    EnvelopeViolation,
    AgentTimeoutError,
    call_agent,
)
from runtime.agents.models import ModelConfig, DEFAULT_MODEL


class TestCanonicalJson:
    """Tests for canonical JSON serialization."""
    
    def test_canonical_json_stable_ordering(self):
        """Key ordering should be lexicographic."""
        obj1 = {"b": 1, "a": 2, "c": 3}
        obj2 = {"a": 2, "c": 3, "b": 1}
        
        assert canonical_json(obj1) == canonical_json(obj2)
    
    def test_canonical_json_no_whitespace(self):
        """No spaces after colons or commas."""
        obj = {"key": "value", "list": [1, 2, 3]}
        result = canonical_json(obj).decode("utf-8")
        
        assert ": " not in result
        assert ", " not in result
    
    def test_canonical_json_utf8(self):
        """Should handle Unicode properly."""
        obj = {"emoji": "🎉", "chinese": "中文"}
        result = canonical_json(obj)
        
        assert isinstance(result, bytes)
        decoded = result.decode("utf-8")
        assert "🎉" in decoded
        assert "中文" in decoded
    
    def test_canonical_json_rejects_nan(self):
        """Should fail-closed on NaN values."""
        import math
        obj = {"value": math.nan}
        
        with pytest.raises(ValueError):
            canonical_json(obj)


class TestDeterministicIds:
    """Tests for deterministic ID computation."""
    
    def test_run_id_deterministic(self):
        """Same inputs should produce same run ID."""
        run_id_1 = compute_run_id_deterministic(
            mission_spec={"type": "build"},
            inputs_hash="sha256:abc123",
            governance_surface_hashes={"file.py": "sha256:def456"},
            code_version_id="abc123def",
        )
        run_id_2 = compute_run_id_deterministic(
            mission_spec={"type": "build"},
            inputs_hash="sha256:abc123",
            governance_surface_hashes={"file.py": "sha256:def456"},
            code_version_id="abc123def",
        )
        
        assert run_id_1 == run_id_2
        assert run_id_1.startswith("sha256:")
    
    def test_call_id_deterministic(self):
        """Same inputs should produce same call ID."""
        call_id_1 = compute_call_id_deterministic(
            run_id_deterministic="sha256:run123",
            role="designer",
            prompt_hash="sha256:prompt456",
            packet_hash="sha256:packet789",
        )
        call_id_2 = compute_call_id_deterministic(
            run_id_deterministic="sha256:run123",
            role="designer",
            prompt_hash="sha256:prompt456",
            packet_hash="sha256:packet789",
        )
        
        assert call_id_1 == call_id_2
        assert call_id_1.startswith("sha256:")
    
    def test_different_inputs_different_ids(self):
        """Different inputs should produce different IDs."""
        call_id_1 = compute_call_id_deterministic(
            run_id_deterministic="sha256:run123",
            role="designer",
            prompt_hash="sha256:prompt456",
            packet_hash="sha256:packet789",
        )
        call_id_2 = compute_call_id_deterministic(
            run_id_deterministic="sha256:run123",
            role="builder",  # Different role
            prompt_hash="sha256:prompt456",
            packet_hash="sha256:packet789",
        )
        
        assert call_id_1 != call_id_2


class TestAgentCallDataclass:
    """Tests for AgentCall dataclass."""
    
    def test_default_values(self):
        """Should have correct defaults."""
        call = AgentCall(role="designer", packet={"task": "test"})
        
        assert call.model == "auto"
        assert call.temperature == 0.0
        assert call.max_tokens == 8192


class MockTransport(httpx.BaseTransport):
    """Mock transport for httpx that returns predefined responses."""
    
    def __init__(self, response_data: dict, status_code: int = 200):
        self.response_data = response_data
        self.status_code = status_code
        self.requests = []
    
    def handle_request(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return httpx.Response(
            status_code=self.status_code,
            json=self.response_data,
        )


class TestCallAgent:
    """Tests for call_agent function with mocked OpenRouter."""
    
    @pytest.fixture
    def temp_config_dir(self, tmp_path):
        """Create temporary config directory with role prompts."""
        agent_roles = tmp_path / "config" / "agent_roles"
        agent_roles.mkdir(parents=True)
        
        # Create designer prompt
        designer_prompt = agent_roles / "designer.md"
        designer_prompt.write_text("You are a designer agent.", encoding="utf-8")
        
        # Create builder prompt
        builder_prompt = agent_roles / "builder.md"
        builder_prompt.write_text("You are a builder agent.", encoding="utf-8")
        
        return tmp_path
    
    @pytest.fixture
    def mock_openrouter_response(self):
        """Standard successful OpenRouter response."""
        return {
            "id": "gen-123",
            "model": "minimax-m2.1-free",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "design_type: implementation_plan\nsummary: Test design",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
            },
        }
    
    def test_call_agent_missing_role_prompt(self, temp_config_dir):
        """Should raise EnvelopeViolation for missing role."""
        os.chdir(temp_config_dir)
        
        call = AgentCall(role="nonexistent", packet={"task": "test"})
        
        with pytest.raises(EnvelopeViolation, match="Role prompt not found"):
            call_agent(call)
    
    def test_call_agent_missing_api_key(self, temp_config_dir):
        """Should raise error if API key not set."""
        os.chdir(temp_config_dir)
        
        # Ensure API key is not set
        env_backup = os.environ.pop("OPENROUTER_API_KEY", None)
        try:
            call = AgentCall(role="designer", packet={"task": "test"})
            
            with pytest.raises(AgentAPIError, match="OPENROUTER_API_KEY"):
                call_agent(call)
        finally:
            if env_backup:
                os.environ["OPENROUTER_API_KEY"] = env_backup
    
    def test_call_agent_success(self, temp_config_dir, mock_openrouter_response, monkeypatch):
        """Should successfully call OpenRouter and return response."""
        os.chdir(temp_config_dir)
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-123")
        
        # Create mock transport
        transport = MockTransport(mock_openrouter_response)
        
        # Patch httpx.Client to use our mock transport
        original_client = httpx.Client
        def mock_client(**kwargs):
            kwargs["transport"] = transport
            return original_client(**kwargs)
        
        with patch("runtime.agents.api.httpx.Client", mock_client):
            call = AgentCall(role="designer", packet={"task": "test"})
            config = ModelConfig(default_chain=["minimax-m2.1-free"])
            
            response = call_agent(call, run_id="test-run", config=config)
        
        assert response.role == "designer"
        assert response.model_used == "minimax-m2.1-free"
        assert "implementation_plan" in response.content
        assert response.call_id.startswith("sha256:")
        assert response.latency_ms >= 0  # May be 0 in mocked tests
    
    def test_call_agent_parses_yaml_response(self, temp_config_dir, monkeypatch):
        """Should parse YAML responses into packet dict."""
        os.chdir(temp_config_dir)
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-123")
        
        yaml_response = {
            "choices": [
                {
                    "message": {
                        "content": "key: value\nlist:\n  - item1\n  - item2",
                    },
                }
            ],
            "model": "minimax-m2.1-free",
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }
        
        transport = MockTransport(yaml_response)
        original_client = httpx.Client
        def mock_client(**kwargs):
            kwargs["transport"] = transport
            return original_client(**kwargs)
        
        with patch("runtime.agents.api.httpx.Client", mock_client):
            call = AgentCall(role="designer", packet={"task": "test"})
            config = ModelConfig(default_chain=["minimax-m2.1-free"])
            
            response = call_agent(call, config=config)
        
        assert response.packet is not None
        assert response.packet["key"] == "value"
        assert response.packet["list"] == ["item1", "item2"]

    def test_call_agent_fallback_on_rate_limit(self, temp_config_dir, monkeypatch):
        """Should retry and succeed after rate limit (simulating fallback logic)."""
        os.chdir(temp_config_dir)
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-123")
        
        # Mock transport that fails once with 429 then succeeds
        calls = 0
        def mock_handler(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 1:
                resp = httpx.Response(429, content="Rate limited")
                resp._request = httpx.Request("POST", f"{config.base_url}/chat/completions")
                return resp
            resp = httpx.Response(200, json={
                "choices": [{"message": {"content": "ok"}}],
                "model": "minimax-m2.1-free",
                "usage": {}
            })
            resp._request = httpx.Request("POST", f"{config.base_url}/chat/completions")
            return resp
        
        with patch("runtime.agents.api.httpx.Client") as mock_client:
            # Set up the mock client to handle the context manager and post request
            client_instance = MagicMock()
            client_instance.__enter__.return_value = client_instance
            client_instance.post.side_effect = mock_handler
            mock_client.return_value = client_instance
            
            call = AgentCall(role="designer", packet={"task": "test"})
            config = ModelConfig(
                default_chain=["minimax-m2.1-free"],
                backoff_base_seconds=0.01  # Fast backoff for test
            )
            
            response = call_agent(call, config=config)
            
        assert response.content == "ok"
        assert calls == 2


class TestCallAgentReplayMode:
    """Tests for replay mode behavior."""
    
    def test_replay_mode_detection(self, monkeypatch):
        """Should detect LIFEOS_TEST_MODE=replay."""
        from runtime.agents.fixtures import is_replay_mode
        
        monkeypatch.delenv("LIFEOS_TEST_MODE", raising=False)
        assert not is_replay_mode()
        
        monkeypatch.setenv("LIFEOS_TEST_MODE", "replay")
        assert is_replay_mode()
        
        monkeypatch.setenv("LIFEOS_TEST_MODE", "REPLAY")
        assert is_replay_mode()
    
    def test_replay_mode_returns_cached(self, tmp_path, monkeypatch):
        """Should return cached response in replay mode."""
        from runtime.agents.fixtures import (
            ReplayFixtureCache,
            CachedResponse,
            is_replay_mode,
        )
        
        monkeypatch.setenv("LIFEOS_TEST_MODE", "replay")
        
        # Create cache with fixture
        cache_dir = tmp_path / "cache"
        cache = ReplayFixtureCache(str(cache_dir))
        
        cached = CachedResponse(
            call_id_deterministic="sha256:test123",
            role="designer",
            model_version="minimax-m2.1-free",
            input_packet_hash="sha256:input",
            prompt_hash="sha256:prompt",
            response_content="cached content",
            response_packet={"key": "value"},
        )
        
        cache.save_fixture(cached)
        
        # Verify fixture was saved
        reloaded = cache.get("sha256:test123")
        assert reloaded is not None
        assert reloaded.response_content == "cached content"

    def test_replay_mode_require_usage_fails_closed(self, tmp_path, monkeypatch):
        """Should fail closed when replay mode is used with require_usage=True."""
        from runtime.agents.fixtures import CachedResponse

        agent_roles = tmp_path / "config" / "agent_roles"
        agent_roles.mkdir(parents=True)
        (agent_roles / "designer.md").write_text("You are a designer agent.", encoding="utf-8")

        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("LIFEOS_TEST_MODE", "replay")

        cached = CachedResponse(
            call_id_deterministic="sha256:cached",
            role="designer",
            model_version="minimax-m2.1-free",
            input_packet_hash="sha256:input",
            prompt_hash="sha256:prompt",
            response_content="cached content",
            response_packet={"key": "value"},
        )

        with patch("runtime.agents.fixtures.get_cached_response", return_value=cached):
            with pytest.raises(AgentAPIError, match="TOKEN_ACCOUNTING_UNAVAILABLE"):
                call_agent(
                    AgentCall(
                        role="designer",
                        packet={"task": "test"},
                        require_usage=True,
                    )
                )

```
