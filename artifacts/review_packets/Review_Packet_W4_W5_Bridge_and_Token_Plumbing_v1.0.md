# Review Packet: W4/W5 Bridge and Token Plumbing v1.0

## Mission Scope
- W4-T01: OpenClaw mapping bridge module and unit tests.
- W4-T02: Deterministic OpenClaw evidence routing contract with verification checks.
- W5-T04 (scaffold): Token usage plumbing checks and fail-closed path for missing usage.

## Commits
- `e7d7ab8` W4-T01: add OpenClaw-Spine bridge mapping module with unit tests
- `f4e9c72` W4-T02: add deterministic OpenClaw evidence routing contract
- `fae33c5` W5-T04: enforce token usage plumbing checks and fail closed when missing

## Targeted Test Evidence
- `pytest -q runtime/tests/orchestration/test_openclaw_bridge.py`
  - PASS: 8 passed
- `pytest -q runtime/tests/orchestration/missions/test_autonomous_loop.py runtime/tests/test_agent_api_usage_plumbing.py`
  - PASS: 8 passed
- `pytest -q runtime/tests/orchestration/test_openclaw_bridge.py runtime/tests/orchestration/missions/test_autonomous_loop.py runtime/tests/test_agent_api_usage_plumbing.py`
  - PASS: 16 passed

## Appendix A: Flattened Code (Full, No Omissions)

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

    for filename, field_name in (
        ("packet_refs.json", "packet_refs"),
        ("ledger_refs.json", "ledger_refs"),
    ):
        payload = json.loads((evidence_path / filename).read_text(encoding="utf-8"))
        refs = payload.get(field_name)
        if not isinstance(refs, list) or not refs:
            errors.append(f"{filename} missing non-empty '{field_name}'")

    manifest_lines = [
        line.strip()
        for line in (evidence_path / "hash_manifest.sha256").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
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

```

### FILE: `runtime/agents/opencode_client.py`

```python
"""
OpenCode Client Module
======================

Reusable client for LLM calls via OpenCode HTTP REST API.
Wraps the ephemeral server lifecycle with context manager support.

================================================================================
HOW TO CHANGE MODELS / PROVIDERS (READ THIS FIRST)
================================================================================

If you need to switch to a different model or provider, follow these steps:

1.  **Edit `config/models.yaml`**:
    - Set the model ID in `default_chain` (e.g., `"claude-sonnet-4"`, `"gpt-4o"`).
    - Set the endpoint URL in the `zen.base_url` field.
    - The first model in `default_chain` is always used.

2.  **Set the API Key in `.env`**:
    - Add/update the key that matches your provider:
      - Zen/Anthropic: `ZEN_API_KEY=sk-...`
      - OpenRouter: `STEWARD_OPENROUTER_KEY=sk-or-...`
      - OpenAI: `OPENAI_API_KEY=sk-...`
    - This client prioritizes: ZEN_API_KEY > STEWARD_OPENROUTER_KEY > OPENROUTER_API_KEY.

3.  **IMPORTANT: Zen Endpoint Specifics**:
    - The Zen endpoint (`https://opencode.ai/zen/v1/messages`) uses the Anthropic protocol.
    - The `opencode` CLI may **reject model IDs it doesn't recognize**. If you see
      "ProviderModelNotFoundError", this client has a direct REST fallback for
      Zen + Minimax. For other models, you may need to use a recognized alias
      or extend the fallback logic below (search for "SPECIAL CASE: Zen").

4.  **Verification**:
    - Run `python scripts/verify_opencode_connectivity.py` to test.
    - Check `logs/agent_calls/` for the `model_used` field in the JSON logs.

================================================================================
"""

import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# Use requests if available, otherwise provide helpful error
try:
    import requests
except ImportError:
    requests = None  # Will raise on actual use

# Import config-driven defaults from single source of truth
try:
    from runtime.agents.models import (
        get_default_endpoint,
        get_api_key_fallback_chain,
        get_api_key,
        load_model_config,
    )
    _HAS_MODELS_MODULE = True
except ImportError:
    _HAS_MODELS_MODULE = False

    def get_default_endpoint() -> str:
        return "https://opencode.ai/zen/v1/messages"

    def get_api_key_fallback_chain() -> list:
        return ["ZEN_STEWARD_KEY", "ZEN_API_KEY", "OPENROUTER_API_KEY"]

    def get_api_key() -> Optional[str]:
        for k in get_api_key_fallback_chain():
            v = os.environ.get(k)
            if v:
                return v
        return None

    def load_model_config():
        return None


def _get_openrouter_base_url() -> str:
    """Get OpenRouter base URL from config or fallback."""
    if _HAS_MODELS_MODULE:
        try:
            config = load_model_config()
            # Check for openrouter config in the raw yaml
            import yaml
            from pathlib import Path
            config_path = Path("config/models.yaml")
            if config_path.exists():
                with open(config_path, "r") as f:
                    data = yaml.safe_load(f)
                    openrouter = data.get("openrouter", {})
                    base_url = openrouter.get("base_url", "")
                    if base_url:
                        # Ensure it ends with /chat/completions for API calls
                        if not base_url.endswith("/chat/completions"):
                            return base_url.rstrip("/") + "/chat/completions"
                        return base_url
        except Exception:
            pass
    return "https://openrouter.ai/api/v1/chat/completions"


# ============================================================================
# EXCEPTIONS
# ============================================================================

class OpenCodeError(Exception):
    """Base exception for OpenCode client errors."""
    pass


class OpenCodeServerError(OpenCodeError):
    """Server failed to start or respond."""
    pass


class OpenCodeTimeoutError(OpenCodeError):
    """Request timed out."""
    pass


class OpenCodeSessionError(OpenCodeError):
    """Failed to create session or send message."""
    pass


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class LLMCall:
    """
    Request for an LLM call.

    Attributes:
        prompt: The user prompt to send.
        model: Model identifier (OpenRouter format).
        system_prompt: Optional system prompt (currently unused by OpenCode).
        role: Agent role making the call (for usage tracking).
    """
    prompt: str
    model: Optional[str] = "auto"  # "auto" triggers config-driven resolution
    system_prompt: Optional[str] = None
    role: str = "unknown"


@dataclass
class LLMResponse:
    """
    Response from an LLM call.

    Attributes:
        call_id: Unique identifier for this call (UUID).
        content: The response text from the model.
        model_used: The model that was actually used.
        latency_ms: Time taken for the call in milliseconds.
        timestamp: ISO timestamp of when the call completed.
    """
    call_id: str
    content: str
    model_used: str
    latency_ms: int
    timestamp: str
    usage: Dict[str, int] = field(default_factory=dict)


# ============================================================================
# CLIENT
# ============================================================================

class OpenCodeClient:
    """
    Client for interacting with OpenCode HTTP REST API.

    Manages an ephemeral OpenCode server lifecycle and provides
    a clean interface for LLM calls with logging.

    Usage:
        with OpenCodeClient(port=62586) as client:
            response = client.call(LLMCall(prompt="Hello"))
            print(response.content)

    Or manual lifecycle:
        client = OpenCodeClient()
        client.start_server(model="openrouter/anthropic/claude-sonnet-4")
        response = client.call(LLMCall(prompt="Hello"))
        client.stop_server()
    """

    # Default paths
    LOG_DIR = "logs/agent_calls"

    def __init__(
        self,
        port: int = 62586,
        timeout: int = 120,
        api_key: Optional[str] = None,
        upstream_base_url: Optional[str] = None,
        log_calls: bool = True,
        role: str = "unknown",
    ):
        """
        Initialize the OpenCode client.

        Args:
            port: HTTP port for the ephemeral server.
            timeout: Request timeout in seconds.
            api_key: OpenRouter API key (falls back to role-based key).
            upstream_base_url: Custom base URL for the LLM endpoint.
            log_calls: Whether to log calls to disk.
            role: Agent role for per-agent key selection.
        """
        if requests is None:
            raise OpenCodeError("requests library required: pip install requests")

        self.port = port
        self.timeout = timeout
        self.log_calls = log_calls
        self.role = role
        self.api_key = api_key or self._load_api_key_for_role(role)
        self.upstream_base_url = upstream_base_url or get_default_endpoint()

        # Server state
        self._server_process: Optional[subprocess.Popen] = None
        self._config_dir: Optional[str] = None
        self._current_model: Optional[str] = None
        self._session_id: Optional[str] = None

        # Ensure log directory exists
        if self.log_calls:
            os.makedirs(self.LOG_DIR, exist_ok=True)

    @property
    def base_url(self) -> str:
        """Base URL for the OpenCode server."""
        return f"http://127.0.0.1:{self.port}"

    @property
    def is_running(self) -> bool:
        """Check if the server is running."""
        return self._server_process is not None and self._server_process.poll() is None

    # ========================================================================
    # API KEY LOADING
    # ========================================================================

    def _get_key_from_env_file(self, var_name: str) -> Optional[str]:
        """
        Robustly parse .env file for a variable.
        Handles:
        - Comments (#)
        - Quoted values ("value", 'value')
        - Whitespace around =
        """
        env_path = os.path.join(os.getcwd(), ".env")
        if not os.path.exists(env_path):
            return None
            
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"): continue
                    
                    if "=" in line:
                        k, v = line.split("=", 1)
                        if k.strip() == var_name:
                            v = v.strip()
                            # Handle quotes
                            if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
                                v = v[1:-1]
                            return v
        except Exception:
            pass
        return None

    def _load_api_key_for_role(self, role: str, provider: str = "openrouter") -> Optional[str]:
        """
        Load the API key for a specific role and provider.
        
        Priority:
        1. os.environ[SPECIFIC_VAR]
        2. .env file [SPECIFIC_VAR]
        3. os.environ[GENERIC_VAR]
        4. .env file [GENERIC_VAR]
        """
        # 1. Determine Var Name from Config
        env_var_name = None
        try:
            from runtime.agents.models import get_agent_config
            agent_config = get_agent_config(role)
            if agent_config:
                if provider == "zen":
                    # For Zen, we trust the primary key env unless explicitly overridden
                    env_var_name = agent_config.api_key_env
                elif agent_config.fallback:
                    for fb in agent_config.fallback:
                        if fb.get("provider") == provider:
                            env_var_name = fb.get("api_key_env")
                            break
        except ImportError:
            pass

        if not env_var_name:
            if provider == "zen":
                 env_var_name = f"ZEN_{role.upper()}_KEY"
            else:
                 env_var_name = f"OPENROUTER_{role.upper()}_KEY"
        
        # 2. Try Specific Key
        key = self._get_key_from_source(env_var_name)
        if key: return key

        # 3. Fallback to Generic
        if provider == "zen":
             return self._get_key_from_source("ZEN_API_KEY")
        else:
             return self._get_key_from_source("OPENROUTER_API_KEY")

    def _get_key_from_source(self, env_var_name: str) -> Optional[str]:
        """Try os.environ then .env."""
        if not env_var_name: return None
        val = os.environ.get(env_var_name)
        if val and val.strip(): return val.strip()
        return self._get_key_from_env_file(env_var_name)

    def _load_api_key(self) -> Optional[str]:
        """Legacy method - calls _load_api_key_for_role with 'unknown'."""
        return self._load_api_key_for_role("unknown")


    # ========================================================================
    # SERVER LIFECYCLE
    # ========================================================================

    def _create_isolated_config(self, model: str) -> str:
        """Create isolated config directory for ephemeral server."""
        temp_dir = tempfile.mkdtemp(prefix="opencode_client_")

        # Config subdirectory
        config_subdir = os.path.join(temp_dir, "opencode")
        os.makedirs(config_subdir, exist_ok=True)

        # Data subdirectory for auth
        data_subdir = os.path.join(temp_dir, ".local", "share", "opencode")
        os.makedirs(data_subdir, exist_ok=True)

        # Write auth.json
        if self.api_key:
            auth_data = {
                "zen": {"type": "api", "key": self.api_key},
                "openrouter": {"type": "api", "key": self.api_key}
            }
            with open(os.path.join(data_subdir, "auth.json"), "w") as f:
                json.dump(auth_data, f, indent=2)

        # Write config
        config_data = {"model": model, "$schema": "https://opencode.ai/config.json"}
        with open(os.path.join(config_subdir, "opencode.json"), "w") as f:
            json.dump(config_data, f, indent=2)

        return temp_dir

    def _cleanup_config(self) -> None:
        """Clean up isolated config directory."""
        if self._config_dir and os.path.exists(self._config_dir):
            try:
                shutil.rmtree(self._config_dir)
            except Exception:
                pass
            self._config_dir = None

    def start_server(self, model: Optional[str] = None) -> None:
        """
        Start the ephemeral OpenCode server.

        Args:
            model: Model identifier to use (defaults to self.default_model or grok).
        """
        if self.is_running:
            raise OpenCodeServerError("Server already running")

        # Check API key first (more fundamental than model)
        if not self.api_key:
            raise OpenCodeServerError("No API key configured (STEWARD_OPENROUTER_KEY or OPENROUTER_API_KEY required)")

        # Determine model
        model = model or os.environ.get("STEWARD_MODEL")
        if not model:
            raise OpenCodeServerError("No model specified for server.")

        self._current_model = model
        self._config_dir = self._create_isolated_config(model)

        # Build environment
        env = os.environ.copy()
        env["APPDATA"] = self._config_dir
        env["XDG_CONFIG_HOME"] = self._config_dir
        env["USERPROFILE"] = self._config_dir
        env["HOME"] = self._config_dir
        env["OPENROUTER_API_KEY"] = self.api_key
        if self.upstream_base_url:
            # Only set base URL for server if it's NOT the Zen special case
            # (Zen special case is handled in call() via direct REST or env override)
            # Actually, server might need it for session creation if using REST?
            # But we only use 'opencode run' now. 'serve' + REST is legacy/flaky.
            # We'll set it anyway, but call() override is what matters.
            env["OPENROUTER_BASE_URL"] = self.upstream_base_url
            env["BASE_URL"] = self.upstream_base_url
        
        # Block fallback to other providers
        env["OPENAI_API_KEY"] = ""
        env["ANTHROPIC_API_KEY"] = ""

        try:
            self._server_process = subprocess.Popen(
                ["opencode", "serve", "--port", str(self.port)],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                shell=(os.name == "nt"),
            )
        except Exception as e:
            self._cleanup_config()
            raise OpenCodeServerError(f"Failed to start server: {e}")

        # Wait for server to be ready
        if not self._wait_for_health():
            self.stop_server()
            raise OpenCodeServerError("Server failed to become healthy")

    def stop_server(self) -> None:
        """Stop the ephemeral OpenCode server."""
        if self._server_process:
            self._server_process.terminate()
            try:
                self._server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._server_process.kill()
            self._server_process = None

        self._cleanup_config()
        self._session_id = None

    def _wait_for_health(self, timeout: int = 30) -> bool:
        """Wait for server health check to pass."""
        start = time.time()
        while time.time() - start < timeout:
            try:
                resp = requests.get(f"{self.base_url}/global/health", timeout=1)
                if resp.status_code == 200:
                    return True
            except Exception:
                pass
            time.sleep(0.5)
        return False

    # ========================================================================
    # SESSION MANAGEMENT
    # ========================================================================

    def _create_session(self) -> str:
        """Create a new session and return session ID."""
        try:
            resp = requests.post(
                f"{self.base_url}/session",
                json={"title": "LLM Call", "model": self._current_model},
                timeout=10,
            )
            if resp.status_code != 200:
                raise OpenCodeSessionError(f"Session creation failed: {resp.status_code} - {resp.text}")
            return resp.json()["id"]
        except requests.RequestException as e:
            raise OpenCodeSessionError(f"Session creation failed: {e}")

    def _send_message(self, session_id: str, prompt: str) -> str:
        """Send a message and return response content."""
        try:
            resp = requests.post(
                f"{self.base_url}/session/{session_id}/message",
                json={"parts": [{"type": "text", "text": prompt}]},
                timeout=self.timeout,
            )
            if resp.status_code != 200:
                raise OpenCodeSessionError(f"Message send failed: {resp.status_code} - {resp.text}")

            # Parse response
            try:
                data = resp.json()
            except json.JSONDecodeError:
                raise OpenCodeSessionError(f"Message send failed: Invalid JSON response from server. Body: {resp.text[:500]}")
            parts = data.get("parts", [])
            content = ""
            for part in parts:
                if part.get("type") == "text":
                    content += part.get("text", "")
            return content

        except requests.Timeout:
            raise OpenCodeTimeoutError(f"Request timed out after {self.timeout}s")
        except requests.RequestException as e:
            raise OpenCodeSessionError(f"Message send failed: {e}")

    # ========================================================================
    # CALL INTERFACE
    # ========================================================================

    def call(self, request: LLMCall) -> LLMResponse:
        """
        Make an LLM call with automatic fallback support.
        """
        # 1. Determine Primary Model
        primary_model = request.model
        if not primary_model:
            primary_model = self._current_model or os.environ.get("STEWARD_MODEL")
            if not primary_model:
                raise ValueError("Model must be specified in request or configuration.")

        # 2. Build Attempt Chain
        # Start with primary (load provider from config)
        primary_provider = None
        try:
            from runtime.agents.models import get_agent_config
            agent_config = get_agent_config(self.role)
            if agent_config:
                primary_provider = agent_config.provider
        except (ImportError, Exception):
            pass

        attempts = [{"model": primary_model, "provider": primary_provider}]

        # Add fallbacks from config
        try:
            from runtime.agents.models import get_agent_config
            agent_config = get_agent_config(self.role)
            if agent_config and agent_config.fallback:
                for fb in agent_config.fallback:
                    attempts.append({
                        "model": fb.get("model"),
                        "provider": fb.get("provider")
                    })
        except ImportError:
            # If models module issue, allow pass
            pass
        except Exception:
            # If config load fails, proceed with primary only
            pass

        # 3. Execute Chain
        last_error = None
        for i, attempt in enumerate(attempts):
            model = attempt["model"]
            is_fallback = (i > 0)
            
            # Trace log
            if "repro" in sys.argv[0] or "verify" in sys.argv[0]:
                print(f"  [TRACE] Attempt {i+1}/{len(attempts)}: {model} {'(Fallback)' if is_fallback else '(Primary)'}")

            try:
                return self._execute_attempt(model, request, provider=attempt.get("provider"))
            except Exception as e:
                # Log warning but continue
                print(f"  [WARNING] Call to {model} failed: {e}")
                last_error = e
                continue
        
        # If all failed
        raise last_error or OpenCodeError("All execution attempts failed")

    def _execute_attempt(self, model: str, request: LLMCall, provider: Optional[str] = None) -> LLMResponse:
        """Execute a single LLM attempt with specific model and dynamic key swapping."""
        call_id = str(uuid.uuid4())
        start_time = time.time()

        def _normalize_usage(usage: Any) -> Dict[str, int]:
            if not isinstance(usage, dict):
                return {}
            out: Dict[str, int] = {}
            field_map = {
                "prompt_tokens": ("prompt_tokens", "input_tokens", "promptTokenCount", "inputTokenCount"),
                "completion_tokens": ("completion_tokens", "output_tokens", "candidatesTokenCount", "outputTokenCount"),
                "total_tokens": ("total_tokens", "totalTokenCount"),
            }
            for canonical_key, aliases in field_map.items():
                for alias in aliases:
                    value = usage.get(alias)
                    if isinstance(value, int) and value >= 0:
                        out[canonical_key] = value
                        break
            return out
        
        # Build environment for this attempt
        env = os.environ.copy()
        
        # Base Key Injection
        if self.api_key:
            env["OPENROUTER_API_KEY"] = self.api_key
            env["ZEN_API_KEY"] = self.api_key
            env["ANTHROPIC_API_KEY"] = self.api_key
            
        # SWAP LOGIC: Determine correct key & provider for THIS model
        # Expanded for new OpenCode/Gemini models
        # P1: Option C - If provider is explicitly 'opencode-openai', treat as plugin (skip Zen REST)
        is_plugin = provider and "opencode-openai" in provider
        is_zen_model = not is_plugin and any(k in model.lower() for k in ["minimax", "zen", "opencode", "gemini"])
        key_status = "Using Primary Key"
        
        if not is_zen_model:
            # Targeted swap to OpenRouter key if needed
            or_key = self._load_api_key_for_role(self.role, provider="openrouter")
            if or_key:
                if or_key != self.api_key:
                    env["OPENROUTER_API_KEY"] = or_key
                    key_status = f"SWAPPED to OpenRouter Key ({or_key[:10]}...)"
                else:
                     key_status = "Primary is already OpenRouter Key"
            else:
                key_status = "FAILED TO SWAP (No OpenRouter key found)"
        
        # Verbose Trace
        if "repro" in sys.argv[0] or "verify" in sys.argv[0]:
            print(f"  [TRACE] Role: {self.role} | Model: {model} | {key_status}")
            if "SWAP" in key_status and "FAILED" not in key_status:
                 print(f"  [TRACE] Injecting OPENROUTER_API_KEY into subprocess environment")

        # 1. SPECIAL CASE: OpenRouter Direct REST (Standard OpenAI)
        # We use this because `opencode run` CLI ignores injected environment variables
        # if a local .env exists, which breaks multi-key support.
        is_openrouter_model = model.startswith("openrouter/") or "openrouter" in self.upstream_base_url.lower()
        
        if is_openrouter_model:
            # Always attempt to load the specific key for this role first
            or_key = self._load_api_key_for_role(self.role, provider="openrouter")
            
            # If not found or empty, check if we have a generic one in env
            # (But only if we didn't find a specific one)
            if not or_key and "OPENROUTER_API_KEY" in env:
                or_key = env["OPENROUTER_API_KEY"]
                
            if or_key:
                or_key = or_key.strip()
                headers = {
                    "Authorization": f"Bearer {or_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://opencode.ai", # Required by OpenRouter for ranking
                    "X-Title": "LifeOS OpenCode Client"
                }
                
                # Get OpenRouter endpoint from config (single source of truth)
                or_url = _get_openrouter_base_url()
                # Override if custom base URL provided
                if self.upstream_base_url and "openrouter" in self.upstream_base_url:
                    or_url = self.upstream_base_url
                    if not or_url.endswith("/chat/completions"):
                        or_url = or_url.rstrip("/") + "/chat/completions"
                
                # Strip internal 'openrouter/' prefix for the raw API call
                api_model = model
                if api_model.startswith("openrouter/"):
                    api_model = api_model.replace("openrouter/", "", 1)

                messages = []
                if request.system_prompt:
                    messages.append({"role": "system", "content": request.system_prompt})
                messages.append({"role": "user", "content": request.prompt})

                payload = {
                    "model": api_model, 
                    "messages": messages,
                }
                
                try:
                    import requests
                    response = requests.post(or_url, headers=headers, json=payload, timeout=self.timeout)
                    
                    if response.status_code == 200:
                        data = response.json()
                        text = ""
                        for choice in data.get("choices", []):
                            delta = choice.get("message", {}).get("content", "")
                            if delta:
                                text += delta
                                
                        llm_response = LLMResponse(
                            call_id=call_id,
                            content=text,
                            model_used=f"OR:{data.get('model', model)}",
                            latency_ms=int((time.time() - start_time) * 1000),
                            timestamp=datetime.now().isoformat(),
                            usage=_normalize_usage(data.get("usage")),
                        )
                        
                        # Log the call
                        if self.log_calls:
                            self._log_call(request, llm_response)
                        
                        return llm_response
                    else:
                         logger.debug(f"OpenRouter REST Failed: Status {response.status_code}, Body: {response.text}")
                except Exception as e:
                    logger.debug(f"OpenRouter REST Exception: {e}")
                    pass

        # 2. SPECIAL CASE: Zen Direct REST (Minimax)
        # Using self.upstream_base_url logic from verified blocks
        is_zen_config_url = self.upstream_base_url and "opencode.ai/zen" in self.upstream_base_url.lower()
        
        if is_zen_model and is_zen_config_url:
             # Load Zen API Key specific
             zen_key = self._load_api_key_for_role(self.role, provider="zen")
             if zen_key:
                 zen_key = zen_key.strip()
                 headers = {
                    "x-api-key": zen_key,
                    "Content-Type": "application/json",
                    "anthropic-version": "2023-06-01"
                 }
                 # SPECIAL CASE: Gemini on Zen (Google Style)
                 if "gemini" in model.lower():
                     # Use Google Generative Language API format
                     # Zen endpoint likely mirrors Google's requirement for key in query param or x-goog-api-key
                     # Try removing :generateContent in case Zen appends it
                     zen_url = f"https://opencode.ai/zen/v1/models/gemini-3-flash:generateContent?key={zen_key}"
                     
                     # Google payload format
                     # user -> user, system -> (not robustly supported in v1beta/v1 for all models, passing as system_instruction if needed or prepending)
                     # For Flash, system_instruction is supported but simplified here to prepending for robustness via Zen?
                     # Let's try standard contents.
                     
                     contents = []
                     if request.system_prompt:
                         contents.append({"role": "user", "parts": [{"text": f"System: {request.system_prompt}"}]})
                         contents.append({"role": "model", "parts": [{"text": "Understood."}]})
                     
                     contents.append({"role": "user", "parts": [{"text": request.prompt}]})
                     
                     payload = {
                         "contents": contents,
                         "generationConfig": {
                             "temperature": 0.7,
                             "maxOutputTokens": 4096
                         }
                     }
                     
                     # Headers: Send all variants to be safe
                     headers = {
                        "x-api-key": zen_key,
                        "x-goog-api-key": zen_key,
                        "Authorization": f"Bearer {zen_key}",
                        "Content-Type": "application/json"
                     }

                     try:
                         import requests
                         response = requests.post(zen_url, headers=headers, json=payload, timeout=self.timeout)
                         
                         if response.status_code == 200:
                             data = response.json()
                             # Parse Google response
                             # candidates[0].content.parts[0].text
                             text = ""
                             candidates = data.get("candidates", [])
                             if candidates:
                                 parts = candidates[0].get("content", {}).get("parts", [])
                                 for part in parts:
                                     text += part.get("text", "")
                             
                             llm_response = LLMResponse(
                                 call_id=call_id,
                                 content=text,
                                 model_used=f"ZEN:{model}",
                                 latency_ms=int((time.time() - start_time) * 1000),
                                 timestamp=datetime.now().isoformat(),
                                 usage=_normalize_usage(data.get("usageMetadata")),
                             )
                             if self.log_calls:
                                 self._log_call(request, llm_response)
                             return llm_response
                         else:
                             logger.debug(f"Zen/Gemini REST Failed: Status {response.status_code}, Body: {response.text}")
                     except Exception as e:
                         logger.debug(f"Zen/Gemini REST Exception: {e}")
                         pass

                 else:
                     # Standard Anthropic Style (Minimax/Claude)
                     zen_model = model.replace("minimax/", "").replace("zen/", "").replace("opencode/", "")
                     
                     payload = {
                        "model": zen_model, 
                        "messages": [{"role": "user", "content": request.prompt}],
                        "max_tokens": 4096,
                        "temperature": 0.7
                     }
                     if request.system_prompt:
                         payload["system"] = request.system_prompt
                     
                     try:
                         import requests
                         # Ensure URL is correct.
                         zen_url = self.upstream_base_url
                         if "/messages" not in zen_url and "/models/" not in zen_url:
                             zen_url = zen_url.rstrip("/") + "/messages"
                         
                         response = requests.post(zen_url, headers=headers, json=payload, timeout=self.timeout)
                         
                         if response.status_code == 200:
                             data = response.json()
                             text = ""
                             for content_part in data.get("content", []):
                                 if content_part.get("type") == "text":
                                     text += content_part.get("text")
                             
                             llm_response = LLMResponse(
                                 call_id=call_id,
                                 content=text,
                                 model_used=f"ZEN:{data.get('model', model)}",
                                 latency_ms=int((time.time() - start_time) * 1000),
                                 timestamp=datetime.now().isoformat(),
                                 usage=_normalize_usage(data.get("usage")),
                             )
                             
                             # Log the call
                             if self.log_calls:
                                 self._log_call(request, llm_response)
                             
                             return llm_response
                         else:
                             logger.debug(f"Zen REST Failed: Status {response.status_code}, Body: {response.text}")
                     except Exception as e:
                         logger.debug(f"Zen REST Exception: {e}")
                         pass
        
        # 2. Standard CLI Execution
        cmd = ["opencode", "run", "-m", model, request.prompt]
        
        # Smart Base URL logic for CLI
        if self.upstream_base_url:
            is_zen_url = "opencode.ai/zen" in self.upstream_base_url.lower()
            if is_zen_url:
                if is_zen_model:
                     env["OPENROUTER_BASE_URL"] = self.upstream_base_url
                     env["BASE_URL"] = self.upstream_base_url
                     env["ANTHROPIC_BASE_URL"] = self.upstream_base_url
                else:
                    # Fallback clearing of Zen URL to avoid routing Grok to Zen
                    pass
            else:
                # Custom non-Zen URL
                env["OPENROUTER_BASE_URL"] = self.upstream_base_url
                env["BASE_URL"] = self.upstream_base_url
                env["ANTHROPIC_BASE_URL"] = self.upstream_base_url

        # Execute
        try:
            # Simulate 'y' inputs for tool confirmation prompts (send multiple just in case)
            result = subprocess.run(
                cmd, 
                env=env, 
                capture_output=True, 
                text=True, 
                input="y\ny\ny\ny\ny\n", # Auto-approve tool calls
                timeout=self.timeout,
                shell=(os.name == "nt"),
            )
            
            if result.returncode != 0:
                error_output = result.stderr or result.stdout
                raise OpenCodeError(f"opencode run failed with exit code {result.returncode}: {error_output}")

            content = result.stdout.strip()
            if not content:
                 # Debugging info
                err_msg = result.stderr.strip() if result.stderr else "No stderr output"
                # Check for known "UndefinedProviderError" signature in stderr just in case
                if "UndefinedProviderError" in err_msg:
                     raise OpenCodeError(f"CLI Provider Error: {err_msg}")
                raise OpenCodeError(f"CLI returned empty content (Silent Failure). Stderr: {err_msg}")

            # Calculate latency
            latency_ms = int((time.time() - start_time) * 1000)
            timestamp = datetime.utcnow().isoformat() + "Z"

            response = LLMResponse(
                call_id=call_id,
                content=content,
                model_used=model,
                latency_ms=latency_ms,
                timestamp=timestamp,
                usage={},
            )

            # Log the call
            if self.log_calls:
                self._log_call(request, response)

            return response
        except subprocess.TimeoutExpired:
            raise OpenCodeTimeoutError(f"opencode run timed out after {self.timeout}s")
        except Exception as e:
            if isinstance(e, OpenCodeError):
                raise
            raise OpenCodeError(f"Failed to execute opencode run: {e}")

    # ========================================================================
    # LOGGING
    # ========================================================================

    def _log_call(self, request: LLMCall, response: LLMResponse) -> None:
        """Log call to disk as JSON."""
        log_entry = {
            "call_id": response.call_id,
            "timestamp": response.timestamp,
            "role": request.role,
            "request": {
                "prompt": request.prompt,
                "model": request.model,
                "system_prompt": request.system_prompt,
            },
            "response": {
                "content": response.content,
                "model_used": response.model_used,
                "latency_ms": response.latency_ms,
            },
        }

        # Use timestamp-based filename for chronological ordering
        filename = f"{response.timestamp.replace(':', '-').replace('.', '-')}_{response.call_id[:8]}.json"
        filepath = os.path.join(self.LOG_DIR, filename)

        try:
            with open(filepath, "w") as f:
                json.dump(log_entry, f, indent=2, sort_keys=True)
        except Exception as e:
            # Don't fail on logging errors
            logger.debug(f"Failed to write call log to {filepath}: {e}")

    # ========================================================================
    # CONTEXT MANAGER
    # ========================================================================

    def __enter__(self) -> "OpenCodeClient":
        """Start server on context entry."""
        self.start_server()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Stop server on context exit."""
        self.stop_server()

```

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
    
    return AgentResponse(
        call_id=call_id,
        call_id_audit=call_id_audit,
        role=call.role,
        model_used=model_version,
        model_version=model_version,
        content=content,
        packet=packet,
        usage={},
        latency_ms=latency_ms,
        timestamp=timestamp,
    )

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
        s_inst.run.return_value = MissionResult(True, MissionType.STEWARD, outputs={"commit_hash": "hash"}, evidence={"usage": {}})
        
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

### FILE: `runtime/tests/test_agent_api_usage_plumbing.py`

```python
from __future__ import annotations

from runtime.agents.api import _normalize_usage


def test_normalize_usage_maps_openrouter_fields() -> None:
    usage = _normalize_usage(
        {
            "prompt_tokens": 11,
            "completion_tokens": 7,
            "total_tokens": 18,
        }
    )
    assert usage == {"input_tokens": 11, "output_tokens": 7, "total_tokens": 18}


def test_normalize_usage_returns_empty_when_unavailable() -> None:
    assert _normalize_usage({}) == {}
    assert _normalize_usage(None) == {}

```
