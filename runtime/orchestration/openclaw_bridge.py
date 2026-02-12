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
