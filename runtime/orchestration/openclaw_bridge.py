"""OpenClaw <-> Spine mapping helpers.

This module centralizes payload conversions between OpenClaw orchestration
inputs and LoopSpine execution/result contracts.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import yaml

OPENCLAW_JOB_KIND = "lifeos.job.v0.1"
OPENCLAW_RESULT_KIND = "lifeos.result.v0.2"
OPENCLAW_EVIDENCE_ROOT = Path("artifacts/evidence/openclaw/jobs")


class OpenClawBridgeError(ValueError):
    """Raised when bridge payload mapping fails validation."""


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def _safe_result_id(value: Any, *, fallback: str) -> str:
    if isinstance(value, str) and value.strip():
        candidate = value.strip()
        if re.fullmatch(r"[A-Za-z0-9._:-]+", candidate):
            return candidate
    return fallback


def _blocked_result(
    *,
    job_id: str,
    run_id: str,
    reason: str,
    packet_refs: list[str] | None = None,
    ledger_refs: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "kind": OPENCLAW_RESULT_KIND,
        "job_id": job_id,
        "run_id": run_id,
        "state": "terminal",
        "outcome": "BLOCKED",
        "reason": reason,
        "terminal_at": _utc_now_iso(),
        "packet_refs": sorted(set(packet_refs or [])),
        "ledger_refs": sorted(set(ledger_refs or [])),
    }


def _repo_relative_path(*, repo_root: Path, path: Path) -> str:
    root = Path(repo_root).resolve()
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(root).as_posix()
    except ValueError as exc:
        raise OpenClawBridgeError(f"artifact path escapes repo root: {path}") from exc


def _load_yaml_packet(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise OpenClawBridgeError(f"artifact packet not found: {path}")
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise OpenClawBridgeError(f"invalid YAML packet: {path}") from exc
    if not isinstance(payload, dict):
        raise OpenClawBridgeError(f"packet must decode to an object: {path}")
    return payload


def _discover_ledger_refs(repo_root: Path) -> list[str]:
    ledger_path = Path(repo_root) / "artifacts" / "loop_state" / "attempt_ledger.jsonl"
    if ledger_path.exists():
        return [_repo_relative_path(repo_root=repo_root, path=ledger_path)]
    return []


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
        "use_worktree": True,
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


def execute_openclaw_job(
    *,
    repo_root: Path,
    job_payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Execute OpenClaw job via LoopSpine and return OpenClaw result payload."""
    fallback_job_id = _safe_result_id(job_payload.get("job_id"), fallback="unknown_job")
    fallback_run_id = _safe_result_id(job_payload.get("run_id"), fallback=f"openclaw:{fallback_job_id}")
    resolved_repo_root = Path(repo_root).resolve()

    try:
        invocation = map_openclaw_job_to_spine_invocation(job_payload)
        job_id = invocation["job_id"]
        run_id = invocation["run_id"]

        from runtime.orchestration.loop.spine import LoopSpine

        spine = LoopSpine(
            repo_root=resolved_repo_root,
            use_worktree=bool(invocation.get("use_worktree", False)),
        )
        spine_result = spine.run(task_spec=invocation["task_spec"], resume_from=None)

        run_id = _safe_result_id(spine_result.get("run_id"), fallback=run_id)
        packet_refs: list[str] = []
        checkpoint_packet: dict[str, Any] | None = None
        checkpoint_packet_ref: str | None = None
        terminal_packet: dict[str, Any] | None = None
        terminal_packet_ref: str | None = None

        if spine_result.get("state") == "CHECKPOINT":
            checkpoint_id = spine_result.get("checkpoint_id")
            if not isinstance(checkpoint_id, str) or not checkpoint_id.strip():
                raise OpenClawBridgeError("checkpoint state missing checkpoint_id")
            checkpoint_path = resolved_repo_root / "artifacts" / "checkpoints" / f"{checkpoint_id}.yaml"
            checkpoint_packet = _load_yaml_packet(checkpoint_path)
            checkpoint_packet_ref = _repo_relative_path(repo_root=resolved_repo_root, path=checkpoint_path)
            packet_refs.append(checkpoint_packet_ref)
        else:
            terminal_path = resolved_repo_root / "artifacts" / "terminal" / f"TP_{run_id}.yaml"
            if terminal_path.exists():
                terminal_packet = _load_yaml_packet(terminal_path)
                terminal_packet_ref = _repo_relative_path(repo_root=resolved_repo_root, path=terminal_path)
                packet_refs.append(terminal_packet_ref)
            else:
                return _blocked_result(
                    job_id=job_id,
                    run_id=run_id,
                    reason=f"TERMINAL_PACKET_MISSING: TP_{run_id}.yaml",
                    ledger_refs=_discover_ledger_refs(resolved_repo_root),
                )

        ledger_refs = _discover_ledger_refs(resolved_repo_root)
        if not ledger_refs:
            return _blocked_result(
                job_id=job_id,
                run_id=run_id,
                reason="LEDGER_REF_MISSING: artifacts/loop_state/attempt_ledger.jsonl",
                packet_refs=packet_refs,
            )

        evidence_contract = write_openclaw_evidence_contract(
            repo_root=resolved_repo_root,
            job_id=job_id,
            packet_refs=packet_refs,
            ledger_refs=ledger_refs,
        )
        evidence_ok, evidence_errors = verify_openclaw_evidence_contract(
            Path(evidence_contract["evidence_dir"])
        )
        if not evidence_ok:
            failure_reason = evidence_errors[0] if evidence_errors else "unknown evidence validation failure"
            return _blocked_result(
                job_id=job_id,
                run_id=run_id,
                reason=f"EVIDENCE_CONTRACT_INVALID: {failure_reason}",
                packet_refs=packet_refs,
                ledger_refs=ledger_refs,
            )

        hash_manifest_ref = _repo_relative_path(
            repo_root=resolved_repo_root,
            path=Path(evidence_contract["hash_manifest_file"]),
        )

        return map_spine_artifacts_to_openclaw_result(
            job_id=job_id,
            terminal_packet=terminal_packet,
            checkpoint_packet=checkpoint_packet,
            terminal_packet_ref=terminal_packet_ref,
            checkpoint_packet_ref=checkpoint_packet_ref,
            packet_refs=packet_refs,
            ledger_refs=ledger_refs,
            hash_manifest_ref=hash_manifest_ref,
        )

    except OpenClawBridgeError as exc:
        return _blocked_result(
            job_id=fallback_job_id,
            run_id=fallback_run_id,
            reason=f"OPENCLAW_BRIDGE_ERROR: {exc}",
        )
    except Exception as exc:  # pragma: no cover - defensive fail-closed fallback
        return _blocked_result(
            job_id=fallback_job_id,
            run_id=fallback_run_id,
            reason=f"OPENCLAW_EXECUTION_ERROR: {type(exc).__name__}: {exc}",
        )
