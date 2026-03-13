"""Read-only execution truth surface for COO context building."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from runtime.orchestration.dispatch.manifest import MANIFEST_RELATIVE_PATH


_TERMINAL_DIR = Path("artifacts/terminal")
_DISPATCH_ROOT = Path("artifacts/dispatch")
_RUN_LOCK_PATHS = (
    Path("artifacts/locks/run.lock"),
    Path(".lifeos_run_lock"),
)
_RECENT_RUN_LIMIT = 5


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ordered_ids(path: Path) -> list[str]:
    if not path.exists():
        return []
    return sorted(
        item.stem
        for item in path.glob("*.yaml")
        if item.is_file() and item.name != ".gitkeep"
    )


def _safe_load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} did not decode to a mapping")
    return payload


def _read_manifest(path: Path, errors: list[str]) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    entries: list[dict[str, Any]] = []
    try:
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            raw = line.strip()
            if not raw:
                continue
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError as exc:
                errors.append(f"{path}:{line_no}: invalid json ({exc})")
                continue
            if not isinstance(payload, dict):
                errors.append(f"{path}:{line_no}: manifest entry must be an object")
                continue
            entries.append(payload)
    except OSError as exc:
        errors.append(f"{path}: {type(exc).__name__}: {exc}")
    return entries


def _read_terminal_packets(path: Path, errors: list[str]) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    packets: list[dict[str, Any]] = []
    for packet_path in sorted(path.glob("TP_*.yaml")):
        try:
            payload = _safe_load_yaml(packet_path)
        except (OSError, ValueError, yaml.YAMLError) as exc:
            errors.append(f"{packet_path}: {type(exc).__name__}: {exc}")
            continue

        packets.append(
            {
                "path": str(packet_path.relative_to(path.parent.parent)),
                "run_id": str(payload.get("run_id", "")).strip(),
                "timestamp": str(payload.get("timestamp", "")).strip(),
                "outcome": str(payload.get("outcome", "")).strip(),
                "reason": str(payload.get("reason", "")).strip(),
                "status": str(payload.get("status", "")).strip(),
                "task_ref": str(payload.get("task_ref", "")).strip(),
            }
        )
    return packets


def _read_lock(repo_root: Path, errors: list[str]) -> dict[str, Any]:
    for relative_path in _RUN_LOCK_PATHS:
        lock_path = repo_root / relative_path
        if not lock_path.exists():
            continue

        lock_info: dict[str, Any] = {
            "path": str(relative_path),
            "present": True,
            "content": "",
        }
        try:
            lock_info["content"] = lock_path.read_text(encoding="utf-8").strip()
        except OSError as exc:
            errors.append(f"{lock_path}: {type(exc).__name__}: {exc}")
        return lock_info

    return {"path": "", "present": False, "content": ""}


def _blocking_reason(payload: dict[str, Any]) -> str:
    reason = str(payload.get("reason", "")).strip()
    if reason:
        return reason
    outcome = str(payload.get("outcome", "")).strip()
    status = str(payload.get("status", "")).strip()
    return outcome or status


def _extract_blockers(
    terminal_packets: list[dict[str, Any]],
    manifest_entries: list[dict[str, Any]],
) -> list[dict[str, str]]:
    blockers: list[dict[str, str]] = []

    for payload in terminal_packets:
        outcome = str(payload.get("outcome", "")).upper()
        status = str(payload.get("status", "")).upper()
        if outcome in {"BLOCKED", "ESCALATION_REQUESTED", "WAIVER_REQUESTED"} or status == "CLEAN_FAIL":
            blockers.append(
                {
                    "run_id": str(payload.get("run_id", "")).strip(),
                    "reason": _blocking_reason(payload),
                    "source": str(payload.get("path", "")).strip(),
                }
            )

    for payload in manifest_entries:
        outcome = str(payload.get("outcome", "")).upper()
        reason = str(payload.get("reason", "")).strip()
        if outcome in {"BLOCKED", "ESCALATION_REQUESTED", "WAIVER_REQUESTED", "CLEAN_FAIL"}:
            blockers.append(
                {
                    "run_id": str(payload.get("run_id", "")).strip(),
                    "reason": reason or outcome,
                    "source": str(MANIFEST_RELATIVE_PATH),
                }
            )

    deduped: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for blocker in blockers:
        key = (blocker["run_id"], blocker["reason"], blocker["source"])
        if key not in seen:
            deduped.append(blocker)
            seen.add(key)
    return sorted(deduped, key=lambda item: (item["run_id"], item["source"], item["reason"]))


def _summarize_runs(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    recent = entries[-_RECENT_RUN_LIMIT:]
    recent = sorted(
        recent,
        key=lambda item: (
            str(item.get("recorded_at", "")),
            str(item.get("run_id", "")),
        ),
        reverse=True,
    )
    return [
        {
            "recorded_at": str(item.get("recorded_at", "")).strip(),
            "run_id": str(item.get("run_id", "")).strip(),
            "order_id": str(item.get("order_id", "")).strip(),
            "outcome": str(item.get("outcome", "")).strip(),
            "reason": str(item.get("reason", "")).strip(),
        }
        for item in recent
    ]


def _terminal_conflicts(
    recent_packets: list[dict[str, Any]],
    lock_info: dict[str, Any],
    active_ids: list[str],
) -> list[str]:
    conflicts: list[str] = []
    if lock_info.get("present") and recent_packets:
        latest = recent_packets[0]
        if str(latest.get("outcome", "")).upper() == "PASS" and not active_ids:
            conflicts.append("lock_present_but_latest_terminal_passed")
    return conflicts


def build_execution_truth(repo_root: Path) -> dict[str, Any]:
    """Aggregate lightweight execution truth from repo artifacts only."""
    repo_root = Path(repo_root)
    errors: list[str] = []

    manifest_entries = _read_manifest(repo_root / MANIFEST_RELATIVE_PATH, errors)
    terminal_packets = _read_terminal_packets(repo_root / _TERMINAL_DIR, errors)
    lock_info = _read_lock(repo_root, errors)

    inbox_ids = _ordered_ids(repo_root / _DISPATCH_ROOT / "inbox")
    active_ids = _ordered_ids(repo_root / _DISPATCH_ROOT / "active")
    completed_ids = _ordered_ids(repo_root / _DISPATCH_ROOT / "completed")

    recent_packets = sorted(
        terminal_packets,
        key=lambda item: (item["timestamp"], item["run_id"], item["path"]),
        reverse=True,
    )[:_RECENT_RUN_LIMIT]
    recent_runs = _summarize_runs(manifest_entries)
    blockers = _extract_blockers(terminal_packets, manifest_entries)
    conflicts = _terminal_conflicts(recent_packets, lock_info, active_ids)

    latest_run = recent_runs[0] if recent_runs else {}
    truth_data_present = any(
        [
            manifest_entries,
            terminal_packets,
            inbox_ids,
            active_ids,
            completed_ids,
            lock_info.get("present", False),
        ]
    )

    return {
        "truth_reader_ok": not errors,
        "truth_data_present": truth_data_present,
        "truth_generated_at": _now_iso(),
        "truth_read_errors": sorted(errors),
        "run_in_flight": bool(active_ids or lock_info.get("present", False)),
        "dispatch_queue": {
            "pending": len(inbox_ids),
            "active": len(active_ids),
            "completed": len(completed_ids),
            "pending_ids": inbox_ids,
            "active_ids": active_ids,
        },
        "recent_runs": recent_runs,
        "recent_terminal_packets": recent_packets,
        "blockers": blockers,
        "conflicts": conflicts,
        "authoritative_status_summary": {
            "last_run_id": str(latest_run.get("run_id", "")).strip(),
            "last_outcome": str(latest_run.get("outcome", "")).strip(),
            "blocked_count": len(blockers),
            "active_count": len(active_ids),
            "pending_count": len(inbox_ids),
        },
    }
