"""Trusted RemoteOps helpers for non-blocking housekeeping actions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from typing import Any, Callable, Dict, Iterable, List, Literal, Optional

from runtime.validation.reporting import write_json_atomic


RemoteOpStatus = Literal["PENDING", "DEFERRED", "DONE", "TERMINAL"]

QUEUE_FILENAME = "remote_ops_queue.jsonl"
REPORT_FILENAME = "remote_ops_report.json"
RETENTION_DAYS_DEFAULT = 30

_DNS_ERROR_PATTERNS = (
    "could not resolve hostname",
    "name resolution",
)


@dataclass(frozen=True)
class RemoteOp:
    op_id: str
    op_type: str
    target: str
    created_at: str
    attempts: int
    next_attempt_at: Optional[str]
    last_error: Optional[str]
    status: RemoteOpStatus

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "RemoteOp":
        return cls(
            op_id=str(payload["op_id"]),
            op_type=str(payload["op_type"]),
            target=str(payload["target"]),
            created_at=str(payload["created_at"]),
            attempts=int(payload.get("attempts", 0)),
            next_attempt_at=str(payload["next_attempt_at"]) if payload.get("next_attempt_at") else None,
            last_error=str(payload["last_error"]) if payload.get("last_error") else None,
            status=payload.get("status", "PENDING"),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "op_id": self.op_id,
            "op_type": self.op_type,
            "target": self.target,
            "created_at": self.created_at,
            "attempts": self.attempts,
            "next_attempt_at": self.next_attempt_at,
            "last_error": self.last_error,
            "status": self.status,
        }


@dataclass(frozen=True)
class RemoteOpsResult:
    ok_non_blocking: bool
    status: RemoteOpStatus
    blocked_reason: Optional[str]
    report_path: Path
    needs_escalation: bool


def attempt_root_for_remote_ops(workspace_root: Path, run_id: str, attempt_id: str) -> Path:
    workspace_root = workspace_root.resolve()
    return workspace_root / "artifacts" / "validation_runs" / run_id / attempt_id


def queue_path_for_attempt(workspace_root: Path, run_id: str, attempt_id: str) -> Path:
    return attempt_root_for_remote_ops(workspace_root, run_id, attempt_id) / QUEUE_FILENAME


def report_path_for_attempt(workspace_root: Path, run_id: str, attempt_id: str) -> Path:
    return attempt_root_for_remote_ops(workspace_root, run_id, attempt_id) / REPORT_FILENAME


def _now_utc(now_fn: Optional[Callable[[], datetime]] = None) -> datetime:
    now = now_fn() if now_fn is not None else datetime.now(timezone.utc)
    if now.tzinfo is None:
        return now.replace(tzinfo=timezone.utc)
    return now.astimezone(timezone.utc)


def _backoff_delta_for_attempt(attempts: int) -> timedelta:
    if attempts <= 1:
        return timedelta(minutes=5)
    if attempts == 2:
        return timedelta(minutes=15)
    if attempts == 3:
        return timedelta(minutes=45)
    return timedelta(hours=24)


def _looks_like_dns_failure(error_text: str) -> bool:
    lowered = error_text.lower()
    return any(pattern in lowered for pattern in _DNS_ERROR_PATTERNS)


def _op_id_for(op_type: str, target: str) -> str:
    digest = hashlib.sha256(f"{op_type}:{target}".encode("utf-8")).hexdigest()
    return f"op-{digest[:16]}"


def load_queue(queue_path: Path) -> List[RemoteOp]:
    if not queue_path.exists():
        return []

    ops: List[RemoteOp] = []
    for line in queue_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        payload = json.loads(stripped)
        if isinstance(payload, dict):
            ops.append(RemoteOp.from_dict(payload))

    return sorted(ops, key=lambda op: op.op_id)


def _write_queue_atomic(queue_path: Path, ops: Iterable[RemoteOp]) -> None:
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    sorted_ops = sorted(ops, key=lambda op: op.op_id)

    fd, tmp_name = tempfile.mkstemp(prefix=f".{queue_path.name}.", suffix=".tmp", dir=str(queue_path.parent))
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            for op in sorted_ops:
                handle.write(json.dumps(op.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=True))
                handle.write("\n")
        os.replace(tmp_path, queue_path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


def _upsert_op(ops: List[RemoteOp], op: RemoteOp) -> List[RemoteOp]:
    next_ops = [existing for existing in ops if existing.op_id != op.op_id]
    next_ops.append(op)
    return sorted(next_ops, key=lambda item: item.op_id)


def write_remote_ops_report(
    *,
    workspace_root: Path,
    run_id: str,
    attempt_id: str,
    blocked_reason: Optional[str],
    attempted_op: RemoteOp,
    needs_escalation: bool,
    ops: List[RemoteOp],
    generated_at: datetime,
) -> Path:
    report_path = report_path_for_attempt(workspace_root, run_id, attempt_id)
    payload = {
        "schema_version": "remote_ops_report_v1",
        "run_id": run_id,
        "attempt_id": attempt_id,
        "generated_at": generated_at.isoformat(),
        "retention_days": RETENTION_DAYS_DEFAULT,
        "blocked_reason": blocked_reason,
        "needs_escalation": needs_escalation,
        "attempted_op": attempted_op.to_dict(),
        "ops": [op.to_dict() for op in sorted(ops, key=lambda item: item.op_id)],
    }
    write_json_atomic(report_path, payload)
    return report_path


def try_delete_remote_branch(
    branch: str,
    *,
    workspace_root: Path,
    run_id: str = "manual",
    attempt_id: str = "manual",
    timeout_seconds: int = 20,
    now_fn: Optional[Callable[[], datetime]] = None,
) -> RemoteOpsResult:
    now = _now_utc(now_fn)
    op_type = "DELETE_REMOTE_BRANCH"
    op_id = _op_id_for(op_type, branch)

    queue_path = queue_path_for_attempt(workspace_root, run_id, attempt_id)
    existing_ops = load_queue(queue_path)
    existing_by_id = {op.op_id: op for op in existing_ops}

    prior = existing_by_id.get(op_id)
    if prior is None:
        prior = RemoteOp(
            op_id=op_id,
            op_type=op_type,
            target=branch,
            created_at=now.isoformat(),
            attempts=0,
            next_attempt_at=now.isoformat(),
            last_error=None,
            status="PENDING",
        )

    attempts = prior.attempts + 1
    blocked_reason: Optional[str] = None
    needs_escalation = False

    try:
        completed = subprocess.run(
            ["git", "push", "origin", "--delete", branch],
            cwd=workspace_root,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_seconds,
        )
        return_code = completed.returncode
        stderr = completed.stderr.strip()
        stdout = completed.stdout.strip()
        error_text = stderr if stderr else stdout
    except subprocess.TimeoutExpired:
        return_code = 124
        error_text = f"git push origin --delete timed out after {timeout_seconds}s"

    if return_code == 0:
        updated = RemoteOp(
            op_id=prior.op_id,
            op_type=prior.op_type,
            target=prior.target,
            created_at=prior.created_at,
            attempts=attempts,
            next_attempt_at=None,
            last_error=None,
            status="DONE",
        )
    elif _looks_like_dns_failure(error_text):
        blocked_reason = "dns_or_name_resolution_failure"
        updated = RemoteOp(
            op_id=prior.op_id,
            op_type=prior.op_type,
            target=prior.target,
            created_at=prior.created_at,
            attempts=attempts,
            next_attempt_at=(now + _backoff_delta_for_attempt(attempts)).isoformat(),
            last_error=error_text,
            status="DEFERRED",
        )
    elif attempts >= 4:
        needs_escalation = True
        updated = RemoteOp(
            op_id=prior.op_id,
            op_type=prior.op_type,
            target=prior.target,
            created_at=prior.created_at,
            attempts=attempts,
            next_attempt_at=None,
            last_error=error_text,
            status="TERMINAL",
        )
    else:
        updated = RemoteOp(
            op_id=prior.op_id,
            op_type=prior.op_type,
            target=prior.target,
            created_at=prior.created_at,
            attempts=attempts,
            next_attempt_at=(now + _backoff_delta_for_attempt(attempts)).isoformat(),
            last_error=error_text,
            status="DEFERRED",
        )

    next_ops = _upsert_op(existing_ops, updated)
    _write_queue_atomic(queue_path, next_ops)
    report_path = write_remote_ops_report(
        workspace_root=workspace_root,
        run_id=run_id,
        attempt_id=attempt_id,
        blocked_reason=blocked_reason,
        attempted_op=updated,
        needs_escalation=needs_escalation,
        ops=next_ops,
        generated_at=now,
    )

    return RemoteOpsResult(
        ok_non_blocking=True,
        status=updated.status,
        blocked_reason=blocked_reason,
        report_path=report_path,
        needs_escalation=needs_escalation,
    )
